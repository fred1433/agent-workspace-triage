#!/usr/bin/env python3
"""decision_split.py: a PreToolUse hook that keeps three decisions apart.

  1. Authorization. A forbidden write stays forbidden.
  2. Operational limit. An input too large for the advisory check degrades that
     check and says so. It emits no decision, which lets the normal permission
     flow continue. Emitting no decision is not "allow".
  3. Controller error. Anything that goes wrong inside the control is visible
     to the person running the session, and it never turns into a permission.

Written against the Claude Code hooks reference at
https://code.claude.com/docs/en/hooks, consulted on 18 September 2026. What
that page says, and what this script does with it:

  - the call arrives as JSON on standard input, with tool_name, tool_input and
    tool_use_id among its fields;
  - "Stderr from a hook that exits 0 goes to the debug log only, never the
    transcript, and Claude never sees it." So anything a person needs to read
    is returned as systemMessage, which the page describes as the way "to
    surface a message to the user on any platform";
  - exit code 2 blocks the call; any other exit code does not block by itself,
    and when stdout carries a valid decision object "Claude Code ignores the
    exit code and the JSON alone decides the outcome";
  - permissionDecision is deny, allow or abstain, where abstain means "No
    decision, continue to normal permission flow";
  - a command hook that reaches its timeout is cancelled and "doesn't block the
    tool call", so a control that hangs is not a gate.

Consequences this script is built on. The input is decoded and validated before
anything is compared, because a path can arrive JSON escaped and a field can
arrive after any number of bytes. A control that cannot validate its input, or
that is misconfigured, refuses: it is the only outcome that does not quietly
become permission. And because a timeout is not a refusal either, the work here
stays small.

Nothing is claimed for any other engine, and nothing here was exercised inside
a running engine: the tests drive this script, not Claude Code. See HOOK.md.

Configuration, all optional:
  HOOK_PROTECTED_PATTERN  extended regex of paths that may not be written
  HOOK_ADVISORY_MAX_BYTES size above which the advisory check degrades
  HOOK_LOG                where to append one JSON record per call
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

DEFAULT_PROTECTED = r"(^|/)(\.env|\.git/|secrets/|infra/production/)"
WRITING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
TARGET_FIELDS = ("file_path", "notebook_path", "path")
CONTRACT = "every call this control examined is recorded here"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(decision: str, reason: str, notes: list[str]) -> None:
    """One object on stdout, exit 0. That is the documented decision channel."""
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    if notes:
        payload["systemMessage"] = " ".join(notes)
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    raise SystemExit(0)


class Log:
    """Append only, best effort, and never silent about its own failure."""

    def __init__(self, path: str, notes: list[str]):
        self.path = path
        self.notes = notes
        if not path:
            notes.append("decision_split: no log is configured (HOOK_LOG is unset), "
                         "so no rejection rate can be computed from this run.")

    def write(self, record: dict) -> None:
        if not self.path:
            return
        try:
            fresh = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
            with open(self.path, "a", encoding="utf-8") as handle:
                if fresh:
                    handle.write(json.dumps({
                        "record": "contract", "complete": True, "scope": CONTRACT,
                        "control": "decision_split", "version": 1, "opened": now(),
                    }) + "\n")
                handle.write(json.dumps(record) + "\n")
        except OSError:
            self.notes.append(f"decision_split: the log at {self.path} could not be written. "
                              "The decision below was taken anyway, and no rate can be computed "
                              "from an incomplete log.")


def main() -> None:
    raw = sys.stdin.read()
    size = len(raw.encode("utf-8", errors="replace"))
    notes: list[str] = []
    log = Log(os.environ.get("HOOK_LOG", ""), notes)
    attempt = ""

    def record(outcome: str, reason: str, advisory: str) -> None:
        entry = {"record": "event", "ts": now(), "outcome": outcome, "reason": reason,
                 "bytes": size, "advisory": advisory, "attempt": attempt or f"pid-{os.getpid()}-{now()}"}
        log.write(entry)

    # A control that cannot read its input does not get to guess what the input
    # said. It refuses, visibly.
    try:
        call = json.loads(raw)
        if not isinstance(call, dict):
            raise ValueError("the call is not an object")
    except (json.JSONDecodeError, ValueError):
        notes.append("decision_split: the call could not be read as JSON, so nothing about it could be "
                     "checked. A control that cannot validate its input refuses rather than let it through.")
        record("rejected", "input-unreadable", "not-run")
        emit("deny", "this call could not be decoded, so it could not be checked", notes)

    attempt = str(call.get("tool_use_id") or "")
    limit_text = os.environ.get("HOOK_ADVISORY_MAX_BYTES", "65536")
    pattern_text = os.environ.get("HOOK_PROTECTED_PATTERN", DEFAULT_PROTECTED)
    try:
        protected = re.compile(pattern_text)
        limit = int(limit_text)
    except (re.error, ValueError):
        notes.append("decision_split: the configuration could not be used "
                     f"(HOOK_PROTECTED_PATTERN or HOOK_ADVISORY_MAX_BYTES). A control that cannot run "
                     "refuses rather than let the call through.")
        record("rejected", "configuration-invalid", "not-run")
        emit("deny", "the control is misconfigured, so this call could not be checked", notes)

    tool = call.get("tool_name")
    arguments = call.get("tool_input")
    if tool is not None and not isinstance(tool, str):
        notes.append("decision_split: the name of the tool is not a string, so the call could not be checked.")
        record("rejected", "tool-name-unreadable", "not-run")
        emit("deny", "the name of the tool could not be read, so this call could not be checked", notes)

    # 1. Authorization, on the decoded call.
    if tool in WRITING_TOOLS:
        if not isinstance(arguments, dict):
            notes.append("decision_split: the input of a writing tool could not be read as an object.")
            record("rejected", "target-unreadable", "not-run")
            emit("deny", "the target of this write could not be read, so it cannot be authorized", notes)
        target = next((arguments[field] for field in TARGET_FIELDS
                       if isinstance(arguments.get(field), str)), None)
        if target is None:
            record("rejected", "target-unreadable", "not-run")
            emit("deny", "the target path of this write could not be read, so it cannot be authorized", notes)
        if protected.search(target):
            record("rejected", "protected-path", "not-run")
            emit("deny", "this path is protected by policy, and that does not change with the size of the call",
                 notes)

    # 2. Operational limit. Above the threshold the advisory check degrades. No
    # decision is emitted, so the normal permission flow continues. This is not
    # an authorization, and it grants nothing.
    if size > limit:
        notes.append(f"decision_split: the advisory check was skipped, the call is {size} bytes, above the "
                     f"advisory limit of {limit}. No permission decision was emitted; the normal permission "
                     f"flow applies.")
        record("observed", "advisory-degraded-oversize", "degraded")
        emit("abstain", "the advisory check degraded on size; no permission is granted or refused here", notes)

    # 3. The advisory check itself. There is none in this example: it is the
    # place where a real one would go, and it is logged as not implemented
    # rather than as a check that ran and passed.
    record("observed", "advisory-not-implemented", "not-implemented")
    emit("abstain", "nothing to report on this call", notes)


if __name__ == "__main__":
    main()
