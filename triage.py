#!/usr/bin/env python3
"""agent-workspace-triage: a read only collector that turns a sprawling agent
workspace into decisions you can check.

What it does
    Walks the roots you name, finds the directories that look like working
    trees, asks git what each one actually is, and writes one decision per
    directory with the evidence behind it and the check that is still missing.

What it never does
    It writes nothing under the roots it inspects, it calls no external
    service, it sends no report, and it prints no cleanup command for you to
    paste. The report goes where you ask for it, and nowhere else. Statuses are
    proposals with their evidence, not instructions.

Python 3.11 or newer. Standard library only. No configuration file.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.1"

# Every external command this program is allowed to start. The read only test
# asserts that nothing outside this set is ever executed.
ALLOWED_EXECUTABLES = {"git", "ps", "lsof"}

# Flags that keep git from writing anything while it answers a question.
# --no-optional-locks stops git from refreshing the index on a read command,
# which is the writing that a "read only" tool usually does without noticing.
GIT_READONLY_FLAGS = [
    "--no-optional-locks",
    "-c", "gc.auto=0",
    "-c", "maintenance.auto=false",
    "-c", "core.fsmonitor=false",
]

# Directories the walk never enters.
SKIP_DIR_NAMES = {
    "node_modules", ".git", ".venv", "venv", "__pycache__", ".next", ".nuxt",
    ".turbo", ".cache", ".pytest_cache", ".mypy_cache", "dist", "build",
    "target", ".terraform", ".gradle", "Pods", ".svn", ".hg",
}

# A directory holding one of these is treated as a candidate working tree even
# when it carries no git link at all.
PROJECT_MARKERS = (
    ".git", "package.json", "pyproject.toml", "requirements.txt", "go.mod",
    "Cargo.toml", "Gemfile", "pom.xml", "composer.json", "node_modules",
)

# Ignored entries this collector ASSUMES a build writes again. The assumption is
# never verified: nothing here inspects a build. Anything ignored and outside
# this list is treated as possibly the only copy of something, which is a reason
# to preserve the directory and to name what is left to confirm.
# *.log is deliberately absent: an ignored log can hold the only trace of an
# incident, and a name is not evidence that a build would write it again.
ASSUMED_REBUILDABLE = {
    "node_modules", "dist", "build", ".next", ".nuxt", ".turbo", ".cache",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "coverage",
    ".coverage", "target", ".parcel-cache", ".svelte-kit", ".angular",
    ".gradle", ".DS_Store", "*.pyc",
}

KEEP = "keep"
CANDIDATE = "removal candidate, to confirm"
UNDETERMINED = "undetermined"

# Every external command actually executed, with the directory it ran in, in
# order. Exposed for the tests, which check both the allow list and the scope.
COMMAND_TRACE: list[dict] = []


class CommandError(Exception):
    """An external command failed, timed out, or was refused.

    Its message is a category, never the text a command printed: that text can
    carry a path or a file content, and it ends up in the report.
    """


def run_command(argv: list[str], cwd: str | None = None, timeout: float = 20.0,
                allow_exit: tuple[int, ...] = (0,)) -> str:
    """Run one allowed external command and return its stdout.

    No shell, no network, no writing. The executable is checked against the
    allow list before anything starts, and the directory it runs in is recorded
    so that the scope of the run can be checked afterwards.
    """
    if argv[0] not in ALLOWED_EXECUTABLES:
        raise CommandError(f"executable not allowed: {argv[0]}")
    COMMAND_TRACE.append({"argv": list(argv), "cwd": cwd})
    env = dict(os.environ)
    # Belt and braces next to --no-optional-locks.
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_PAGER"] = "cat"
    env["LC_ALL"] = "C"
    try:
        done = subprocess.run(
            argv, cwd=cwd, env=env, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandError(f"timed out after {timeout:g}s") from exc
    except OSError:
        raise CommandError("the command could not be started") from None
    if done.returncode not in allow_exit:
        raise CommandError(f"exit status {done.returncode}")
    return done.stdout


# The only failure descriptions that may reach a report. Anything else a
# command said about itself stays out: its text can carry a path, a branch name
# or a file content, and a report is meant to carry names, not contents.
SAFE_ERROR_CATEGORIES = (
    "timed out after", "exit status", "the command could not be started",
    "executable not allowed",
)


def error_category(exc: Exception) -> str:
    text = str(exc)
    return text if text.startswith(SAFE_ERROR_CATEGORIES) else "the command failed"


def git(cwd: str, args: list[str], timeout: float = 20.0,
        allow_exit: tuple[int, ...] = (0,)) -> str:
    return run_command(["git", *GIT_READONLY_FLAGS, *args], cwd=cwd,
                       timeout=timeout, allow_exit=allow_exit)


@dataclass
class Coverage:
    """What the walk of one root actually saw, and what it left unopened.

    Three states, because two were not enough. `partial` is a stop that was not
    intended: a budget that ran out, a directory that could not be read.
    `bounded` is a walk that finished inside its declared limits while leaving
    subtrees unopened: the depth limit, the excluded names, a symlink, or a
    candidate directory the walk stops at. Only a walk that left nothing
    unopened is `complete`.
    """
    root: str
    max_depth: int = 0
    failed: bool = False
    failure_reason: str = ""
    directories_examined: int = 0
    directories_skipped: int = 0
    symlinks_not_followed: int = 0
    depth_limit_reached: int = 0
    candidates_not_descended: int = 0
    errors: list[str] = field(default_factory=list)
    seconds: float = 0.0

    def bounds(self) -> list[str]:
        out = []
        if self.depth_limit_reached:
            out.append(f"{self.depth_limit_reached} left unopened at the depth limit of {self.max_depth}")
        if self.directories_skipped:
            out.append(f"{self.directories_skipped} skipped by name or by an exclusion you gave")
        if self.candidates_not_descended:
            out.append(f"{self.candidates_not_descended} candidate directories not descended into")
        if self.symlinks_not_followed:
            out.append(f"{self.symlinks_not_followed} symlinks counted and not followed")
        return out

    @property
    def status(self) -> str:
        if self.failed:
            return "partial"
        return "bounded" if self.bounds() else "complete"

    @property
    def not_opened(self) -> int:
        return self.depth_limit_reached + self.directories_skipped + self.candidates_not_descended

    def reason(self) -> str:
        if self.failed:
            return self.failure_reason
        return "; ".join(self.bounds())

    def as_dict(self) -> dict:
        return {
            "root": os.path.basename(self.root.rstrip(os.sep)) or self.root,
            "coverage": self.status,
            "reason": self.reason(),
            "depth_limit": self.max_depth,
            "directories_examined": self.directories_examined,
            "directories_skipped": self.directories_skipped,
            "symlinks_not_followed": self.symlinks_not_followed,
            "depth_limit_reached": self.depth_limit_reached,
            "candidates_not_descended": self.candidates_not_descended,
            "not_opened": self.not_opened,
            "errors": self.errors,
        }


@dataclass
class Candidate:
    """One directory, what git says about it, and the decision it earns."""
    path: str                      # displayed path, relative to its root
    absolute: str
    root: str
    kind: str = ""
    owner: str = ""
    branch: str = ""
    last_activity: str = ""
    observation: str = ""
    evidence: list[str] = field(default_factory=list)
    preservation: list[str] = field(default_factory=list)
    decision: str = UNDETERMINED
    sentence: str = ""
    remaining: str = ""
    inspection: str = "complete"
    node_modules: int = 0
    node_modules_bytes: int | None = None

    def as_dict(self) -> dict:
        out = {
            "path": self.path,
            "kind": self.kind,
            "owner": self.owner,
            "branch": self.branch,
            "last_activity": self.last_activity,
            "observation": self.observation,
            "evidence": list(self.evidence),
            "preserved_because": list(self.preservation),
            "decision": self.decision,
            "decision_sentence": self.sentence,
            "remaining_condition": self.remaining,
            "inspection": self.inspection,
            "node_modules_trees": self.node_modules,
            "provenance": "measured on the scanned filesystem",
        }
        if self.node_modules_bytes is not None:
            out["node_modules_bytes"] = self.node_modules_bytes
        return out


# --------------------------------------------------------------------------
# Walking, with a budget
# --------------------------------------------------------------------------

def is_candidate_dir(entry_path: str) -> bool:
    for marker in PROJECT_MARKERS:
        if os.path.exists(os.path.join(entry_path, marker)):
            return True
    return False


def walk_root(root: str, budget: float, max_depth: int, excludes: list[str]) -> tuple[list[str], Coverage]:
    """Find candidate directories under one root without walking the world.

    The walk stops at max_depth, refuses to enter the noisy directory names,
    never follows symlinks, stops at a candidate rather than descending into
    it, and gives up when the time budget for this root is spent. Everything it
    left unopened is counted, and the coverage of the root says so. An
    interrupted walk is reported as partial, never as a clean result.
    """
    started = time.monotonic()
    cov = Coverage(root=root, max_depth=max_depth)
    found: list[str] = []
    stack: list[tuple[str, int]] = [(root, 0)]

    while stack:
        current, depth = stack.pop()
        if time.monotonic() - started > budget:
            cov.failed = True
            cov.failure_reason = f"the time budget of {budget:g}s for this root was reached"
            break
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except PermissionError:
            cov.failed = True
            cov.failure_reason = "at least one directory could not be read"
            cov.errors.append(f"permission denied: {tail(current, 2)}")
            continue
        except OSError as exc:
            cov.failed = True
            cov.failure_reason = "at least one directory could not be read"
            cov.errors.append(f"{exc.strerror or 'could not be read'}: {tail(current, 2)}")
            continue

        for entry in entries:
            try:
                if entry.is_symlink():
                    cov.symlinks_not_followed += 1
                    continue
                if not entry.is_dir():
                    continue
            except OSError:
                cov.errors.append(f"could not stat: {tail(entry.path, 2)}")
                cov.failed = True
                cov.failure_reason = cov.failure_reason or "at least one directory could not be read"
                continue
            if entry.name in SKIP_DIR_NAMES:
                cov.directories_skipped += 1
                continue
            if any(fnmatch.fnmatch(entry.name, pattern) for pattern in excludes):
                cov.directories_skipped += 1
                continue
            cov.directories_examined += 1
            if is_candidate_dir(entry.path):
                found.append(entry.path)
                cov.candidates_not_descended += 1
                continue
            if depth + 1 >= max_depth:
                cov.depth_limit_reached += 1
                continue
            stack.append((entry.path, depth + 1))

    cov.seconds = time.monotonic() - started
    return sorted(found), cov


def count_node_modules(directory: str, budget: float, with_sizes: bool) -> tuple[int, int | None, bool]:
    """Count node_modules trees inside a candidate. Sizes only on request.

    Returns (count, bytes_or_None, complete). Size is the sum of the logical
    file sizes, which is stable across filesystems, unlike disk usage.
    """
    started = time.monotonic()
    count = 0
    total = 0 if with_sizes else None
    complete = True
    stack = [(directory, 0)]
    while stack:
        current, depth = stack.pop()
        if time.monotonic() - started > budget:
            complete = False
            break
        try:
            entries = list(os.scandir(current))
        except OSError:
            complete = False
            continue
        for entry in entries:
            try:
                if entry.is_symlink() or not entry.is_dir():
                    continue
            except OSError:
                complete = False
                continue
            if entry.name == "node_modules":
                count += 1
                if with_sizes:
                    size, ok = directory_bytes(entry.path, budget - (time.monotonic() - started))
                    total += size
                    complete = complete and ok
                continue
            if entry.name in SKIP_DIR_NAMES or entry.name.startswith("."):
                continue
            if depth + 1 < 3:
                stack.append((entry.path, depth + 1))
    return count, total, complete


def directory_bytes(directory: str, budget: float) -> tuple[int, bool]:
    started = time.monotonic()
    total = 0
    complete = True
    for current, dirs, files in os.walk(directory, followlinks=False):
        if time.monotonic() - started > budget:
            return total, False
        for name in files:
            try:
                stat = os.lstat(os.path.join(current, name))
            except OSError:
                complete = False
                continue
            total += stat.st_size
    return total, complete


# --------------------------------------------------------------------------
# What git says
# --------------------------------------------------------------------------

def read_git_link(directory: str) -> tuple[str, str]:
    """Return (kind, gitdir) where kind is 'dir', 'file' or 'none'."""
    dot_git = os.path.join(directory, ".git")
    if os.path.isdir(dot_git):
        return "dir", dot_git
    if os.path.isfile(dot_git):
        try:
            with open(dot_git, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read().strip()
        except OSError:
            return "file", ""
        match = re.match(r"^gitdir:\s*(.+)$", text)
        if not match:
            return "file", ""
        target = match.group(1).strip()
        if not os.path.isabs(target):
            target = os.path.normpath(os.path.join(directory, target))
        return "file", target
    return "none", ""


def owner_of_gitdir(gitdir: str) -> str:
    """A linked worktree keeps its metadata in <owner>/.git/worktrees/<name>."""
    parent = os.path.dirname(os.path.normpath(gitdir))          # .../.git/worktrees
    if os.path.basename(parent) != "worktrees":
        return ""
    git_dir = os.path.dirname(parent)                            # .../.git
    if os.path.basename(git_dir) != ".git":
        return ""
    return os.path.realpath(os.path.dirname(git_dir))


def parse_worktree_list(text: str) -> list[dict]:
    """Parse `git worktree list --porcelain` into records.

    The free text git attaches to `locked` and `prunable` is deliberately not
    kept: a lock reason is written by a person and can say anything.
    """
    records: list[dict] = []
    current: dict = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                records.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            if current:
                records.append(current)
            current = {"worktree": line[len("worktree "):]}
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):]
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("locked"):
            current["locked"] = True
        elif line.startswith("prunable"):
            current["prunable"] = True
        elif line.strip() == "bare":
            current["bare"] = True
        elif line.strip() == "detached":
            current["detached"] = True
    if current:
        records.append(current)
    return records


def short_branch(ref: str) -> str:
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


def content_filters(directory: str, git_timeout: float) -> list[str]:
    """The content filters that could actually run in this working tree.

    A git filter is a command, and git starts it while answering an ordinary
    question about a file. A collector that calls itself read only cannot run
    somebody else's conversion command, so it looks first and stops.

    Two things have to be true before a filter can run: a driver is configured
    with a clean or process command, and an attribute assigns that driver to a
    path. Configuration alone is not enough, and treating it as enough makes the
    collector useless on any machine where git-lfs is installed, which is most of
    them.
    """
    text = git(directory, ["config", "--get-regexp", r"^filter\.[^.]+\.(clean|process)$"],
               git_timeout, allow_exit=(0, 1))
    configured = set()
    for line in text.splitlines():
        parts = line.split(" ", 1)[0].split(".")
        if len(parts) >= 3:
            configured.add(parts[1])
    if not configured:
        return []

    assigned = set()
    for source in attribute_sources(directory, git_timeout):
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for token in stripped.split():
                if token.startswith("filter="):
                    assigned.add(token[len("filter="):])
    return sorted(configured & assigned)


def attribute_sources(directory: str, git_timeout: float) -> list[str]:
    """The attribute files that apply to this working tree, read as plain text.

    Reading a file is not converting it: nothing here makes git touch content.
    The in tree files are listed by git, plus the one at the root whether or not
    it is tracked, plus the per repository and per user files.
    """
    texts: list[str] = []
    paths: list[str] = [os.path.join(directory, ".gitattributes")]

    listing = git(directory, ["ls-files", "-z", "--", "*.gitattributes"], git_timeout, allow_exit=(0, 1))
    names = [name for name in listing.split("\0") if name]
    if len(names) > 200:
        # Too many to read inside a bounded inspection. The conservative answer
        # is to behave as if a filter were assigned.
        return ["* filter=unread"]
    paths += [os.path.join(directory, name) for name in names]

    for key in ("core.attributesFile",):
        value = git(directory, ["config", "--get", key], git_timeout, allow_exit=(0, 1)).strip()
        if value:
            paths.append(os.path.expanduser(value))
    for name in ("info/attributes",):
        for base in (git(directory, ["rev-parse", "--absolute-git-dir"], git_timeout, allow_exit=(0, 1)).strip(),
                     git(directory, ["rev-parse", "--path-format=absolute", "--git-common-dir"],
                         git_timeout, allow_exit=(0, 1)).strip()):
            if base:
                paths.append(os.path.join(base, name))

    for path in dict.fromkeys(paths):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                texts.append(handle.read(200000))
        except OSError:
            continue
    return texts


def established_reference(owner: str, git_timeout: float, override: str = "") -> str:
    """The reference a worktree is compared against, or nothing.

    It has to be established, not guessed. `refs/remotes/origin/HEAD` is written
    by a clone or by `git remote set-head`, so it says what the default branch
    of this repository is. The branch the owner happens to have checked out
    says what somebody was working on this morning, which is a different fact,
    and comparing against it produces removal candidates that mean nothing.
    """
    if override:
        return override
    value = git(owner, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
                git_timeout, allow_exit=(0, 1)).strip()
    return value


# --------------------------------------------------------------------------
# Evidence and decision
# --------------------------------------------------------------------------

def classify_ignored(entries: list[str]) -> list[str]:
    """Keep the ignored entries that are outside the assumed rebuildable list."""
    kept = []
    for raw in entries:
        name = raw.strip().rstrip("/")
        base = os.path.basename(name)
        if base in ASSUMED_REBUILDABLE:
            continue
        if any(fnmatch.fnmatch(base, pattern) for pattern in ASSUMED_REBUILDABLE if "*" in pattern):
            continue
        kept.append(name)
    return kept


def quantity(count: int, singular: str, plural: str) -> str:
    """Write a count the way a person would read it."""
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def preservation_reasons(facts: dict) -> list[tuple[str, str]]:
    """Positive reasons to preserve a directory, each with its own condition.

    Every reason returns the pair (what was read, what is left to confirm). The
    condition belongs to the reason: a lock is not confirmed the way untracked
    work is, and one sentence cannot stand for both. Nothing here establishes
    that the content of a directory exists nowhere else, so nothing here says
    so.

    This function is the preservation control the mutation test disables. When
    it returns nothing, a directory holding untracked work is no longer
    protected, and the expected decision for that directory must fail.
    """
    reasons: list[tuple[str, str]] = []
    if facts.get("locked"):
        reasons.append((
            "git reports this worktree locked, and the reason recorded in the lock was not read",
            "Check why this worktree was locked, and whether the storage it stands on is available, "
            "before reconsidering removal.",
        ))
    if facts.get("moved"):
        reasons.append((
            "the recorded path and the real path differ, which is what git worktree repair reconciles",
            "Reconcile the recorded path with the real path (git worktree repair) before deciding "
            "anything about this directory.",
        ))
    if facts.get("untracked"):
        sample = ", ".join(facts["untracked"][:3])
        count = quantity(len(facts["untracked"]), "untracked file", "untracked files")
        verb = "is" if len(facts["untracked"]) == 1 else "are"
        reasons.append((
            f"{count} here and in no commit ({sample})",
            f"Confirm that this untracked work {verb} kept somewhere else before reconsidering removal.",
        ))
    if facts.get("modified"):
        sample = ", ".join(facts["modified"][:3])
        count = quantity(len(facts["modified"]), "tracked file", "tracked files")
        reasons.append((
            f"{count} modified and not committed ({sample})",
            "Confirm that these uncommitted changes are kept somewhere else before reconsidering removal.",
        ))
    kept_ignored = facts.get("ignored_kept") or []
    if kept_ignored:
        names = ", ".join(kept_ignored[:3])
        if len(kept_ignored) == 1:
            reasons.append((
                f"Ignored {names} found. Its rebuildability and backup status were not checked.",
                "Confirm how this file can be restored before reconsidering removal.",
            ))
        else:
            reasons.append((
                f"Ignored {names} found. Their rebuildability and backup status were not checked.",
                "Confirm how these files can be restored before reconsidering removal.",
            ))
    if facts.get("commits_ahead"):
        count = quantity(facts["commits_ahead"], "commit", "commits")
        verb = "is" if facts["commits_ahead"] == 1 else "are"
        base = facts.get("base_label", "the reference branch")
        reasons.append((
            f"{count} on this branch {verb} not contained in {base}",
            f"Confirm that {'this commit exists' if facts['commits_ahead'] == 1 else 'these commits exist'} "
            f"on another reference before reconsidering removal.",
        ))
    if facts.get("recent_days") is not None and facts.get("recent_days") <= facts.get("stale_days", 30):
        reasons.append((
            f"last commit {quantity(facts['recent_days'], 'day', 'days')} before the reference time",
            "Confirm this worktree is no longer in use before reconsidering removal.",
        ))
    return reasons


def decide(facts: dict) -> tuple[str, str, list[str], str]:
    """Return (status, sentence, preservation reasons, remaining condition).

    Three statuses, and the scope of each one is explicit:
      keep                          a positive reason to preserve was found
      removal candidate, to confirm every check in scope passed, and the last
                                    confirmations are named
      undetermined                  something is missing, with the next check

    A missing piece of information or an inspection that did not finish can
    never produce a removal candidate. That is the whole point of the third
    status.
    """
    kind = facts.get("kind", "")
    undetermined = "Undetermined. Nothing here supports a removal."

    if facts.get("content_filters"):
        names = ", ".join(facts["content_filters"])
        return (
            UNDETERMINED,
            "Undetermined. The content inspection was not run in this repository.",
            [],
            f"This repository configures the content filter {names}, and git starts a filter as an external "
            f"command while reading a working tree. This collector does not run other people's commands, so it "
            f"did not look at the content here. Inspect this directory with the filter disabled, or by hand.",
        )

    if kind == "not registered by any repository":
        return (
            UNDETERMINED,
            undetermined,
            [],
            "No repository under the scanned roots claims this directory. Establish whether it is "
            "a copy, an export, or a working tree whose metadata was removed, and where its content lives now.",
        )

    if kind == "worktree metadata unavailable":
        return (
            UNDETERMINED,
            undetermined,
            [],
            f"The recorded metadata path does not exist ({facts.get('gitdir_display', 'unknown')}). Find the owner "
            f"repository, then decide with git worktree repair or by reading the directory content.",
        )

    if kind == "linked worktree, owner outside the scanned scope":
        return (
            UNDETERMINED,
            undetermined,
            [],
            f"The owner repository is outside the roots you named ({facts.get('owner_hint', 'unknown path')}). "
            f"Include that root, or check this attachment before touching the directory.",
        )

    if kind == "independent repository":
        return (
            KEEP,
            "Keep. This is a repository of its own, not a linked worktree.",
            ["this is a repository of its own, not a linked worktree"],
            "Out of scope for worktree triage: it holds its own history, so it is compared with its remote, "
            "not with a parent.",
        )

    reasons = preservation_reasons(facts)
    conditions = [condition for _reason, condition in reasons]

    # Information that is missing blocks a removal, and only a removal. A
    # directory holding uncommitted work is preserved for that reason whether
    # or not the rest of the inspection could run; the gap is then one more
    # open condition rather than a reason to say nothing at all.
    missing = ""
    if facts.get("reference_missing"):
        missing = ("No comparison reference is established for the owner repository. Set one with "
                   "git remote set-head, or name it with --compare-with, so that commits held only by this "
                   "branch can be counted.")
    elif facts.get("inspection_error"):
        missing = (f"Inspection incomplete ({facts['inspection_error']}). Rerun on this directory "
                   f"before concluding anything else about it.")

    if missing:
        if reasons:
            return (
                KEEP,
                "Keep pending confirmation.",
                [reason for reason, _condition in reasons],
                " ".join([*conditions, missing]),
            )
        return UNDETERMINED, undetermined, [], missing

    if reasons:
        return (
            KEEP,
            "Keep pending confirmation.",
            [reason for reason, _condition in reasons],
            " ".join(conditions),
        )

    branch = facts.get("branch") or "this branch"
    remaining = (
        f"Confirm that no running process has this path as its working directory, and that `{branch}` is not "
        f"the base of an open review. This run read the filesystem, not your processes and not your forges."
    )
    return (
        CANDIDATE,
        "Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.",
        [],
        remaining,
    )


# --------------------------------------------------------------------------
# Inspection of one candidate
# --------------------------------------------------------------------------

def inspect(directory: str, roots: list[str], now: datetime, stale_days: int,
            git_timeout: float, owner_reference: dict, compare_with: str = "") -> dict:
    """Read what git knows about one directory. Nothing is written."""
    facts: dict = {"stale_days": stale_days}
    link_kind, gitdir = read_git_link(directory)

    if link_kind == "none":
        facts["kind"] = "not registered by any repository"
        facts["observation"] = "a directory that looks like a working tree, with no link to any repository"
        facts["evidence"] = ["no .git entry", "project markers present on disk"]
        return facts

    if link_kind == "dir":
        facts["kind"] = "independent repository"
        facts["observation"] = "a repository with its own history, holding its main working tree"
        facts["evidence"] = [".git is a directory, so this is not a linked worktree"]
        try:
            listing = parse_worktree_list(git(directory, ["worktree", "list", "--porcelain"], git_timeout))
            # realpath on both sides: git answers with the resolved path, and on
            # macOS a temporary directory reaches us through a symlink, which made
            # this count differ by one between platforms.
            here = os.path.realpath(directory)
            linked = [r for r in listing
                      if r.get("worktree") and os.path.realpath(r["worktree"]) != here]
            facts["evidence"].append(
                quantity(len(linked), "linked worktree", "linked worktrees") + " registered by this repository"
            )
        except CommandError as exc:
            facts["inspection_error"] = error_category(exc)
        return facts

    # Linked worktree.
    if not gitdir:
        facts["kind"] = "worktree metadata unavailable"
        facts["observation"] = "a .git file that does not name a readable metadata directory"
        facts["evidence"] = [".git is a file, its content could not be read as a gitdir line"]
        facts["gitdir"] = "unreadable"
        return facts

    facts["gitdir"] = gitdir
    facts["gitdir_display"] = tail(gitdir, 4)
    if not os.path.exists(gitdir):
        facts["kind"] = "worktree metadata unavailable"
        facts["observation"] = "a worktree whose metadata directory is gone"
        facts["evidence"] = [f".git points at {tail(gitdir, 4)}", "that path does not exist"]
        return facts

    owner = owner_of_gitdir(gitdir)
    facts["owner_hint"] = tail(owner, 2) if owner else tail(gitdir, 4)
    inside = any(is_within(owner, root) for root in roots) if owner else False
    if not inside:
        facts["kind"] = "linked worktree, owner outside the scanned scope"
        facts["observation"] = "a valid worktree attached to a repository the scan was not asked to look at"
        facts["evidence"] = [f"metadata at {tail(gitdir, 4)}", "owner repository is outside the scanned roots"]
        facts["owner"] = owner
        return facts

    facts["kind"] = "linked worktree"
    facts["owner"] = owner
    facts["evidence"] = [f"attached to {os.path.basename(owner)}"]
    facts["observation"] = f"a linked worktree of {os.path.basename(owner)}"

    # Before any command that makes git read a working file: a repository that
    # configures a content filter would have git run that filter for us.
    try:
        filters = content_filters(directory, git_timeout)
    except CommandError as exc:
        facts["inspection_error"] = error_category(exc)
        return facts
    if filters:
        facts["content_filters"] = filters
        facts["evidence"].append(
            quantity(len(filters), "content filter", "content filters") + " configured in this repository"
        )
        facts["observation"] = (
            f"a linked worktree of {os.path.basename(owner)} in a repository that converts its content"
        )
        return facts

    # A moved worktree: the metadata still records the previous path.
    facts["path_consistent"] = True
    recorded = os.path.join(gitdir, "gitdir")
    if os.path.isfile(recorded):
        try:
            with open(recorded, "r", encoding="utf-8", errors="replace") as handle:
                stored = handle.read().strip()
            if os.path.realpath(stored) != os.path.realpath(os.path.join(directory, ".git")):
                facts["moved"] = True
                facts["path_consistent"] = False
                facts["evidence"].append("the metadata records another path for this worktree")
        except OSError:
            facts["path_consistent"] = False
            facts["inspection_error"] = "the recorded path of this worktree could not be read"
            return facts

    # The fact of the lock, never the text somebody wrote in it.
    facts["locked"] = os.path.exists(os.path.join(gitdir, "locked"))

    try:
        head = git(directory, ["rev-parse", "--abbrev-ref", "HEAD"], git_timeout).strip()
        facts["branch"] = head
        status = git(
            directory,
            ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--no-renames"],
            git_timeout,
        )
    except CommandError as exc:
        facts["inspection_error"] = error_category(exc)
        facts["observation"] = "a worktree git refused to describe"
        return facts

    untracked, modified, ignored = [], [], []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        code, name = line[:2], line[3:]
        if code == "??":
            untracked.append(name)
        elif code == "!!":
            ignored.append(name)
        else:
            modified.append(name)
    facts["untracked"] = sorted(untracked)
    facts["modified"] = sorted(modified)
    facts["ignored_kept"] = sorted(classify_ignored(ignored))

    try:
        last = git(directory, ["log", "-1", "--format=%cI"], git_timeout).strip()
        facts["last_commit"] = last[:10] if last else ""
        if last:
            when = datetime.fromisoformat(last)
            facts["recent_days"] = max(0, (now - when).days)
    except CommandError:
        facts["inspection_error"] = "the date of the last commit could not be read"
        facts["observation"] = f"a linked worktree of {os.path.basename(owner)} on branch {facts.get('branch', 'unknown')}"
        return facts

    base = compare_with or owner_reference.get(owner, "")
    if not base:
        facts["reference_missing"] = True
        facts["observation"] = f"a linked worktree of {os.path.basename(owner)} on branch {facts.get('branch', 'unknown')}"
        return facts

    facts["base_label"] = base
    try:
        ahead = git(directory, ["rev-list", "--count", f"{base}..HEAD"], git_timeout).strip()
        facts["commits_ahead"] = int(ahead or "0")
    except (CommandError, ValueError):
        facts["inspection_error"] = "the number of commits not contained in the reference branch could not be read"
        facts["observation"] = f"a linked worktree of {os.path.basename(owner)} on branch {facts.get('branch', 'unknown')}"
        return facts

    facts["observation"] = f"a linked worktree of {os.path.basename(owner)} on branch {facts.get('branch', 'unknown')}"
    facts["verified_negatives"] = verified_negatives(facts)
    return facts


def verified_negatives(facts: dict) -> list[str]:
    """The checks that were read and came back empty.

    A removal candidate is a directory where several things were looked for and
    not found. Naming only the branch comparison would turn the rest into a
    claim nobody can check.
    """
    lines = []
    if not facts.get("modified"):
        lines.append("no modified tracked file")
    if not facts.get("untracked"):
        lines.append("no untracked file")
    if not facts.get("ignored_kept"):
        lines.append("no ignored entry outside the assumed rebuildable list")
    if not facts.get("locked"):
        lines.append("not locked")
    if facts.get("path_consistent"):
        lines.append("the recorded path matches the real path")
    if facts.get("last_commit"):
        days = facts.get("recent_days")
        if days is None:
            lines.append(f"last commit {facts['last_commit']}")
        else:
            lines.append(f"last commit {facts['last_commit']}, "
                         f"{quantity(days, 'day', 'days')} before the reference time")
    return lines


def tail(path: str, parts: int = 3) -> str:
    """Show the tail of a path. A report is read next to the machine it
    describes, and an absolute temporary path helps nobody."""
    pieces = [p for p in os.path.normpath(path).split(os.sep) if p]
    return os.sep.join(pieces[-parts:]) if pieces else path


def is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)
    except (ValueError, OSError):
        return False


# --------------------------------------------------------------------------
# Optional inventories, each with its boundary written next to it
# --------------------------------------------------------------------------

def read_process_table() -> str:
    return run_command(["ps", "-Ao", "pid=,ppid=,etime=,tty=,comm="], timeout=15.0)


def read_cwd(pid: str) -> str:
    """The working directory of one process, from the system that knows it.

    On Linux the kernel publishes it as a symlink. Elsewhere lsof is asked for
    that one file descriptor. Either can refuse, and a refusal is reported as
    unavailable rather than filled in with a guess.
    """
    link = f"/proc/{pid}/cwd"
    try:
        if os.path.islink(link):
            return os.readlink(link)
    except OSError:
        return ""
    try:
        text = run_command(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                           timeout=10.0, allow_exit=(0, 1))
    except CommandError:
        return ""
    for line in text.splitlines():
        if line.startswith("n"):
            return line[1:].strip()
    return ""


def inventory_sessions(now: datetime, table: str | None = None,
                       cwd_lookup=None, names=("claude", "codex", "kiro")) -> dict:
    """List the agent processes that exist. It does not detect a hung session.

    A process name, an age, a working directory and a terminal describe a
    process. They do not describe the progress of the work it was given, so the
    progress column says so instead of guessing. Detecting a suspected block
    needs a progress event or a declared wait, a session identity and a
    documented threshold. None of those are filesystem facts.
    """
    if table is None:
        try:
            table = read_process_table()
        except CommandError as exc:
            return {"available": False, "reason": str(exc), "sessions": []}
    if cwd_lookup is None:
        cwd_lookup = read_cwd

    sessions = []
    for line in table.splitlines():
        fields = line.split()
        if len(fields) < 5:
            continue
        pid, _ppid, elapsed, tty, comm = fields[0], fields[1], fields[2], fields[3], " ".join(fields[4:])
        base = os.path.basename(comm)
        if base not in names:
            continue
        cwd = ""
        try:
            cwd = cwd_lookup(pid) or ""
        except Exception:
            cwd = ""
        sessions.append({
            "pid": pid,
            "process": base,
            "elapsed": elapsed,
            "terminal": tty if tty not in ("??", "-") else "none",
            "working_directory": cwd or "not available (the working directory of this process could not be read)",
            "progress": "unknown (no progress source)",
        })
    return {
        "available": True,
        "sessions": sorted(sessions, key=lambda s: (s["process"], s["pid"])),
        "note": (
            "processes only. An old session without a terminal can be perfectly normal, and this "
            "inventory never claims a session is hung."
        ),
    }


KNOWN_OUTCOMES = {"observed", "examined", "allowed", "passed", "rejected", "denied"}
REJECTIONS = {"rejected", "denied"}


def hook_rejection_rate(log_path: str) -> dict:
    """Compute a rejection rate only when the log can carry one.

    "About one call in four" is a ratio, so it needs a denominator that was not
    built out of the numerator. Three things have to be true of the log before
    any number is worth printing: it declares that every call the control
    examined is recorded, every line can be read, and every record carries a
    time and an identifier. Otherwise the honest output is a refusal.

    Two rates, because they answer different questions. The rate per attempt is
    what the log can always support. The rate per initial call needs the log to
    say which attempts belong to the same call, and most logs do not.
    """
    out: dict = {"log": os.path.basename(log_path)}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            lines = [line for line in handle if line.strip()]
    except OSError as exc:
        return {**out, "computable": False,
                "reason": f"log could not be read ({exc.strerror or 'no such file'})"}

    contract = None
    events = []
    unreadable = 0
    unrecognised = 0
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            unreadable += 1
            continue
        if not isinstance(record, dict):
            unreadable += 1
            continue
        kind = record.get("record")
        if kind == "contract":
            contract = record
        elif kind == "event":
            events.append(record)
        else:
            unrecognised += 1

    if unreadable:
        return {**out, "computable": False, "records": len(lines),
                "reason": f"rate: not computable from this log, {quantity(unreadable, 'line', 'lines')} "
                          f"could not be read as a record, so the log cannot claim to hold every call"}
    if unrecognised:
        return {**out, "computable": False, "records": len(lines),
                "reason": f"rate: not computable from this log, {quantity(unrecognised, 'record', 'records')} "
                          f"is of no known kind, so the log cannot claim to hold every call"}
    if contract is None or not contract.get("complete"):
        return {**out, "computable": False, "records": len(lines),
                "reason": "rate: not computable from this log, it does not declare that every call the control "
                          "examined is recorded here, and refusals cannot be their own denominator"}
    if not events:
        return {**out, "computable": False, "records": len(lines),
                "reason": "rate: not computable from this log, it declares a contract and holds no call"}

    missing = [event for event in events
               if not event.get("ts") or event.get("outcome") not in KNOWN_OUTCOMES or not event.get("attempt")]
    if missing:
        return {**out, "computable": False, "records": len(lines),
                "reason": f"rate: not computable from this log, {quantity(len(missing), 'record', 'records')} "
                          f"carry no time, no outcome or no attempt identifier"}

    stamps = sorted(str(event["ts"]) for event in events)
    rejected = [event for event in events if event["outcome"] in REJECTIONS]
    reasons: dict[str, int] = {}
    for event in rejected:
        key = str(event.get("reason", "unspecified"))
        reasons[key] = reasons.get(key, 0) + 1

    calls = {}
    for event in events:
        call = event.get("call")
        if not call:
            calls = {}
            break
        calls.setdefault(call, []).append(event)

    if calls:
        first_of_call = [sorted(group, key=lambda e: str(e["ts"]))[0] for group in calls.values()]
        rejected_calls = [event for event in first_of_call if event["outcome"] in REJECTIONS]
        initial = round(len(rejected_calls) / len(first_of_call), 4)
    else:
        initial = ("not identifiable from this log: its records carry no link between an attempt and the "
                   "call it belongs to")

    return {
        **out,
        "computable": True,
        "attempts_examined": len(events),
        "attempts_rejected": len(rejected),
        "attempt_rate": round(len(rejected) / len(events), 4),
        "initial_call_rate": initial,
        "period": f"{stamps[0]} to {stamps[-1]}",
        "reasons": dict(sorted(reasons.items())),
        "contract": str(contract.get("scope", "every call examined by this control is recorded here")),
        "note": ("the rate is per attempt. A call refused and tried again counts twice, which is the honest "
                 "reading unless the log says which attempts belong to the same call."),
    }


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def collect(roots: list[str], now: datetime, stale_days: int, budget: float,
            max_depth: int, excludes: list[str], git_timeout: float,
            with_sizes: bool, compare_with: str = "") -> dict:
    roots = [os.path.abspath(r) for r in roots]
    candidates: list[Candidate] = []
    coverages: list[Coverage] = []
    owner_reference: dict[str, str] = {}
    discovered: list[tuple[str, str]] = []

    for root in roots:
        found, cov = walk_root(root, budget, max_depth, excludes)
        coverages.append(cov)
        for path in found:
            discovered.append((root, path))

    # The comparison reference of every owner, read once, and only for owners
    # that are inside the roots we were given. The scope check comes first: a
    # repository outside the roots is not asked anything at all, not even the
    # name of its default branch.
    for _root, path in discovered:
        link_kind, gitdir = read_git_link(path)
        owner = os.path.realpath(path) if link_kind == "dir" else owner_of_gitdir(gitdir) if gitdir else ""
        if not owner or owner in owner_reference:
            continue
        if not any(is_within(owner, root) for root in roots):
            continue
        if not os.path.isdir(os.path.join(owner, ".git")):
            continue
        try:
            owner_reference[owner] = established_reference(owner, git_timeout, compare_with)
        except CommandError:
            owner_reference[owner] = ""

    moved_registrations: dict[tuple[str, str], str] = {}

    for root, path in discovered:
        facts = inspect(path, roots, now, stale_days, git_timeout, owner_reference, compare_with)
        decision, sentence, reasons, remaining = decide(facts)
        trees, size, complete = count_node_modules(path, budget, with_sizes)
        cand = Candidate(
            path=os.path.relpath(path, os.path.dirname(root)),
            absolute=path,
            root=os.path.basename(root),
            kind=facts.get("kind", ""),
            owner=os.path.basename(facts.get("owner", "")) if facts.get("owner") else "",
            branch=facts.get("branch", ""),
            last_activity=facts.get("last_commit", ""),
            observation=facts.get("observation", ""),
            evidence=list(facts.get("evidence", [])),
            preservation=reasons,
            decision=decision,
            sentence=sentence,
            remaining=remaining,
            inspection="complete" if not facts.get("inspection_error") else f"incomplete: {facts['inspection_error']}",
            node_modules=trees,
            node_modules_bytes=size,
        )
        if facts.get("moved") and facts.get("owner") and facts.get("branch"):
            moved_registrations[(facts["owner"], facts["branch"])] = cand.path
        if decision == CANDIDATE:
            cand.evidence.extend(facts.get("verified_negatives", []))
        if facts.get("untracked"):
            cand.evidence.append(quantity(len(facts["untracked"]), "untracked file", "untracked files"))
        if facts.get("modified"):
            cand.evidence.append(quantity(len(facts["modified"]), "modified tracked file", "modified tracked files"))
        if facts.get("ignored_kept"):
            cand.evidence.append(
                quantity(len(facts["ignored_kept"]), "ignored entry", "ignored entries")
                + " outside the assumed rebuildable list"
            )
        if facts.get("commits_ahead") is not None:
            base = facts.get("base_label", "the reference branch")
            if facts["commits_ahead"] == 0:
                cand.evidence.append(f"every commit on this branch is contained in {base}")
            else:
                cand.evidence.append(
                    quantity(facts["commits_ahead"], "commit", "commits") + f" not contained in {base}"
                )
        if not complete:
            cand.evidence.append("the node_modules count for this directory hit its budget and is a lower bound")
        candidates.append(cand)

    # Registered entries whose directory is absent: metadata, not directories.
    absent: list[dict] = []
    for owner in sorted(owner_reference):
        try:
            listing = parse_worktree_list(git(owner, ["worktree", "list", "--porcelain"], git_timeout))
        except CommandError:
            continue
        for record in listing:
            path = record.get("worktree", "")
            if not path or os.path.realpath(path) == os.path.realpath(owner):
                continue
            if os.path.exists(path):
                continue
            branch = short_branch(record.get("branch", ""))
            entry = {
                "owner": os.path.basename(owner),
                "recorded_path": os.path.basename(path),
                "branch": branch,
                "git_says": "the recorded directory is not on disk",
                "note": (
                    "this is a registration with no directory. Pruning removes the registration, "
                    "it does not remove any directory that is still on disk."
                ),
            }
            moved_to = moved_registrations.get((owner, branch))
            if moved_to:
                entry["explained_by"] = moved_to
                entry["note"] = (
                    f"this is the previous path of {moved_to}, which was moved on disk. Nothing is missing: "
                    f"git worktree repair reconciles the registration with the real path."
                )
            absent.append(entry)

    candidates.sort(key=lambda c: c.path)
    counts = {
        "roots_scanned": len(roots),
        "candidate_directories": len(candidates),
        "linked_worktrees_in_scope": sum(1 for c in candidates if c.kind == "linked worktree"),
        "linked_worktrees_owner_outside_scope": sum(1 for c in candidates if c.kind.startswith("linked worktree, owner")),
        "worktree_metadata_unavailable": sum(1 for c in candidates if c.kind == "worktree metadata unavailable"),
        "independent_repositories": sum(1 for c in candidates if c.kind == "independent repository"),
        "not_registered_by_any_repository": sum(1 for c in candidates if c.kind == "not registered by any repository"),
        "node_modules_trees": sum(c.node_modules for c in candidates),
        "registered_entries_without_directory": len(absent),
        "keep": sum(1 for c in candidates if c.decision == KEEP),
        "removal_candidates_to_confirm": sum(1 for c in candidates if c.decision == CANDIDATE),
        "undetermined": sum(1 for c in candidates if c.decision == UNDETERMINED),
    }

    return {
        "tool": "agent-workspace-triage",
        "version": VERSION,
        "reference_time": now.date().isoformat(),
        "stale_days": stale_days,
        "roots": [os.path.basename(r) for r in roots],
        "walk": {
            "max_depth": max_depth,
            "excluded_names": sorted(SKIP_DIR_NAMES) + sorted(excludes),
            "budget_seconds_per_root": budget,
            "git_timeout_seconds": git_timeout,
        },
        "coverage": [c.as_dict() for c in coverages],
        "counts": counts,
        "decisions": [c.as_dict() for c in candidates],
        "registered_entries_without_directory": absent,
        "boundaries": {
            "network": "no external service is called and no report is sent: the collector imports no network "
                       "client, and a control runs a whole collection with no network access at all",
            "writes": "nothing under the roots you name is written: no file, no index, no reference, no "
                      "configuration. Git is called with --no-optional-locks, and a repository that configures "
                      "a content filter is left uninspected rather than have git run that filter. The report is "
                      "written where you ask for it, and nowhere else",
            "commands": "no cleanup command is printed or executed; a status is a proposal with its evidence",
            "outside_scope": "nothing outside the roots you name is read, including the owner of a worktree "
                             "attached elsewhere, which is not asked anything at all",
        },
    }


def markdown(report: dict, sessions: dict | None, hook: dict | None, with_sizes: bool) -> str:
    lines: list[str] = []
    add = lines.append
    counts = report["counts"]
    walk = report.get("walk", {})

    add("# Workspace triage report")
    add("")
    add(f"Collector `agent-workspace-triage {report['version']}`, read only. "
        f"Reference time {report['reference_time']}. Roots scanned: {', '.join(report['roots'])}.")
    add("")
    if report.get("provenance_note"):
        add(report["provenance_note"])
        add("")
    add("Every line below is one directory: what was observed, the evidence behind it, the decision it earns, "
        "and the check that is still missing. Nothing here was deleted, and no cleanup command is printed.")
    add("")

    add("## Coverage")
    add("")
    add("| Root | Coverage | Examined | Not opened | Errors |")
    add("|---|---|---|---|---|")
    for cov in report["coverage"]:
        errors = "; ".join(cov["errors"]) if cov["errors"] else "none"
        note = cov["coverage"] + (f" ({cov['reason']})" if cov["reason"] else "")
        add(f"| {cov['root']} | {note} | {cov['directories_examined']} | {cov['not_opened']} | {errors} |")
    add("")
    add(f"Depth limit in force: {walk.get('max_depth', 'unset')} levels below each root. "
        f"The walk stops at a candidate directory instead of descending into it, so a working tree nested "
        f"inside another one is not discovered. Excluded names: "
        f"{', '.join(walk.get('excluded_names', [])[:8])} and the rest of the built in list.")
    add("")
    add("`complete` means nothing was left unopened. `bounded` means the walk finished inside the limits above "
        "and left the counted subtrees unopened. `partial` means it stopped for a reason it did not choose, and "
        "partial is never read as nothing found, and never as clean.")
    add("")
    add(f"The time budget of {walk.get('budget_seconds_per_root', 0):g}s bounds the discovery walk of one root. "
        f"It does not bound the whole run: every git inspection has its own timeout "
        f"({walk.get('git_timeout_seconds', 0):g}s), and the node_modules count of each candidate directory "
        f"receives that budget again.")
    add("")

    add("## Counts")
    add("")
    for key in ("candidate_directories", "linked_worktrees_in_scope", "linked_worktrees_owner_outside_scope",
                "worktree_metadata_unavailable", "independent_repositories", "not_registered_by_any_repository",
                "node_modules_trees", "registered_entries_without_directory"):
        add(f"- {key.replace('_', ' ')}: {counts[key]}")
    add("")
    add(f"- decisions: {counts['keep']} keep, {counts['removal_candidates_to_confirm']} removal candidate to confirm, "
        f"{counts['undetermined']} undetermined")
    add("")

    for status, title, blurb in (
        (KEEP, "Keep", "A positive reason to preserve was found, and each reason carries the confirmation it "
                       "still needs. These are the directories a count based cleanup would have taken."),
        (CANDIDATE, "Removal candidate, to confirm", "The checks in scope were read and came back empty; they "
                                                     "are listed as evidence. The confirmations that remain are "
                                                     "named, because the scan read the filesystem and nothing else."),
        (UNDETERMINED, "Undetermined", "Something is missing. The next check is named. An undetermined line is "
                                       "work, not a shrug."),
    ):
        rows = [d for d in report["decisions"] if d["decision"] == status]
        add(f"## {title} ({len(rows)})")
        add("")
        add(blurb)
        add("")
        for row in rows:
            add(f"### `{row['path']}`")
            add("")
            add(f"- Observation: {row['observation']}")
            add(f"- Evidence: {'; '.join(row['evidence']) if row['evidence'] else 'none recorded'}")
            if row.get("preserved_because"):
                add(f"- Reason to preserve: {'; '.join(row['preserved_because'])}")
            add(f"- Decision: {row.get('decision_sentence') or row['decision']}")
            add(f"- Still open: {row['remaining_condition']}")
            if row["inspection"] != "complete":
                add(f"- Inspection: {row['inspection']}")
            add("")

    absent = report["registered_entries_without_directory"]
    add(f"## Registrations without a directory ({len(absent)})")
    add("")
    if absent:
        add("These are entries in a repository that name a worktree directory which is not on disk. "
            "They are metadata. Pruning them removes the registration and removes no directory.")
        add("")
        for row in absent:
            add(f"- `{row['recorded_path']}` recorded by `{row['owner']}` on branch `{row['branch']}`: {row['note']}")
    else:
        add("None found.")
    add("")

    add("## Not measured in this run")
    add("")
    if sessions is None:
        add("- Agent sessions: not inventoried. The optional inventory lists processes with their age, terminal and "
            "working directory, and reports progress as unknown, because no progress source exists on the filesystem.")
    if hook is None:
        add("- Hook rejection rate: no hook log was given, so no rate is computed. A rate needs a log that says it "
            "records every call the control examined, over a period, with an identifier per attempt.")
    elif not hook.get("computable"):
        add(f"- Hook rejection rate: {hook.get('reason')}")
    else:
        add(f"- Hook rejection rate per attempt: {hook['attempts_rejected']} of {hook['attempts_examined']} "
            f"({hook['attempt_rate']:.0%}), period {hook['period']}. Rate per initial call: "
            f"{hook['initial_call_rate']}.")
    if not with_sizes:
        add("- node_modules sizes: counted, not weighed. Sizes are an option because weighing them walks every file, "
            "which is the walk that times out on a workspace this size.")
    add("")

    if sessions is not None:
        rows = sessions.get("sessions", [])
        add(f"## Agent sessions ({len(rows)})")
        add("")
        if not sessions.get("available"):
            add(f"The process table could not be read ({sessions.get('reason', 'unknown')}), so nothing is listed.")
        elif not rows:
            add("No process of the named kinds is running.")
        else:
            add("| Process | PID | Age | Terminal | Working directory | Progress |")
            add("|---|---|---|---|---|---|")
            for row in rows:
                add(f"| {row['process']} | {row['pid']} | {row['elapsed']} | {row['terminal']} | "
                    f"`{row['working_directory']}` | {row['progress']} |")
            add("")
            add(sessions.get("note", ""))
        add("")

    add("## Boundaries")
    add("")
    for value in report["boundaries"].values():
        add(f"- {value}")
    add("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="triage.py",
        description="Read only triage of a sprawling agent workspace: one decision per directory, with its evidence.",
    )
    parser.add_argument("--root", action="append", default=[], metavar="PATH",
                        help="a directory that contains working trees. Repeat it for each root.")
    parser.add_argument("--markdown", metavar="FILE", help="write the report as Markdown (default: standard output)")
    parser.add_argument("--json", metavar="FILE", help="write the report as JSON")
    parser.add_argument("--budget-seconds", type=float, default=20.0,
                        help="time budget for the discovery walk of ONE root (default 20). It does not bound the "
                             "whole run: each git call has --git-timeout, and each candidate directory receives "
                             "this budget again while its node_modules trees are counted.")
    parser.add_argument("--max-depth", type=int, default=3, help="how deep below a root to look (default 3)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="directory names to skip, in addition to the built in list")
    parser.add_argument("--stale-days", type=int, default=30,
                        help="a worktree whose last commit is newer than this is preserved (default 30)")
    parser.add_argument("--git-timeout", type=float, default=20.0, help="timeout for each git call (default 20)")
    parser.add_argument("--compare-with", metavar="REF", default="",
                        help="the reference a branch is compared against when a repository has no established "
                             "default branch. Without it, such a repository is reported as undetermined rather "
                             "than compared with whatever branch happens to be checked out.")
    parser.add_argument("--sizes", action="store_true", help="also weigh the node_modules trees (walks every file)")
    parser.add_argument("--sessions", action="store_true", help="also list the agent processes that exist")
    parser.add_argument("--hook-log", metavar="FILE", help="a hook log to compute a rejection rate from, if it can carry one")
    parser.add_argument("--now", metavar="ISO8601", help="reference time, for a reproducible report")
    parser.add_argument("--version", action="version", version=f"agent-workspace-triage {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root:
        print("give at least one --root", file=sys.stderr)
        return 2
    for root in args.root:
        if not os.path.isdir(root):
            print(f"not a directory: {root}", file=sys.stderr)
            return 2

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    report = collect(
        roots=args.root, now=now, stale_days=args.stale_days, budget=args.budget_seconds,
        max_depth=args.max_depth, excludes=args.exclude, git_timeout=args.git_timeout,
        with_sizes=args.sizes, compare_with=args.compare_with,
    )
    sessions = inventory_sessions(now) if args.sessions else None
    hook = hook_rejection_rate(args.hook_log) if args.hook_log else None
    if sessions is not None:
        report["sessions"] = sessions
    if hook is not None:
        report["hook_log"] = hook

    text = markdown(report, sessions, hook, args.sizes)
    if args.markdown:
        Path(args.markdown).write_text(text, encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.markdown and not args.json:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
