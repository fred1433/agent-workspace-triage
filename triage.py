#!/usr/bin/env python3
"""agent-workspace-triage: a read only collector that turns a sprawling agent
workspace into decisions you can check.

What it does
    Walks the roots you name, finds the directories that look like working
    trees, asks git what each one actually is, and writes one decision per
    directory with the evidence behind it and the check that is still missing.

What it never does
    It never writes to the repositories it inspects, it never calls an external
    service, it never sends a report anywhere, and it never prints a cleanup
    command for you to paste. Statuses are proposals with their evidence, not
    instructions.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "1.0"

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

# Ignored entries that a build regenerates. Anything else that is ignored is
# treated as work that only exists here, for example an environment file or a
# local database, and it becomes a reason to preserve the directory.
REGENERABLE_IGNORED = {
    "node_modules", "dist", "build", ".next", ".nuxt", ".turbo", ".cache",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "coverage",
    ".coverage", "target", ".parcel-cache", ".svelte-kit", ".angular",
    "vendor", ".gradle", ".DS_Store", "*.pyc", "*.log",
}

KEEP = "keep"
CANDIDATE = "removal candidate, to confirm"
UNDETERMINED = "undetermined"

# Every external command actually executed, in order. Exposed for the tests.
COMMAND_TRACE: list[list[str]] = []


class CommandError(Exception):
    """An external command failed, timed out, or was refused."""


def run_command(argv: list[str], cwd: str | None = None, timeout: float = 20.0) -> str:
    """Run one allowed external command and return its stdout.

    No shell, no network, no writing. The executable is checked against the
    allow list before anything starts.
    """
    if argv[0] not in ALLOWED_EXECUTABLES:
        raise CommandError(f"executable not allowed: {argv[0]}")
    COMMAND_TRACE.append(list(argv))
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
        raise CommandError(f"timed out after {timeout:g}s: {' '.join(argv[:4])}") from exc
    except OSError as exc:
        raise CommandError(str(exc)) from exc
    if done.returncode != 0:
        detail = (done.stderr or "").strip().splitlines()
        raise CommandError(detail[0] if detail else f"exit {done.returncode}")
    return done.stdout


def git(cwd: str, args: list[str], timeout: float = 20.0) -> str:
    return run_command(["git", *GIT_READONLY_FLAGS, *args], cwd=cwd, timeout=timeout)


@dataclass
class Coverage:
    """What the walk of one root actually saw."""
    root: str
    complete: bool = True
    reason: str = ""
    directories_examined: int = 0
    directories_skipped: int = 0
    symlinks_not_followed: int = 0
    depth_limit_reached: int = 0
    errors: list[str] = field(default_factory=list)
    seconds: float = 0.0

    def as_dict(self) -> dict:
        return {
            "root": os.path.basename(self.root.rstrip(os.sep)) or self.root,
            "coverage": "complete" if self.complete else "partial",
            "reason": self.reason,
            "directories_examined": self.directories_examined,
            "directories_skipped": self.directories_skipped,
            "symlinks_not_followed": self.symlinks_not_followed,
            "depth_limit_reached": self.depth_limit_reached,
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
    never follows symlinks, and gives up when the time budget for this root is
    spent. When it gives up, the coverage says so. An interrupted walk is
    reported as partial, never as a clean result.
    """
    started = time.monotonic()
    cov = Coverage(root=root)
    found: list[str] = []
    stack: list[tuple[str, int]] = [(root, 0)]

    while stack:
        current, depth = stack.pop()
        if time.monotonic() - started > budget:
            cov.complete = False
            cov.reason = f"time budget of {budget:g}s for this root was reached"
            break
        try:
            entries = sorted(os.scandir(current), key=lambda e: e.name)
        except PermissionError:
            cov.complete = False
            cov.reason = "at least one directory could not be read"
            cov.errors.append(f"permission denied: {tail(current, 2)}")
            continue
        except OSError as exc:
            cov.complete = False
            cov.reason = "at least one directory could not be read"
            cov.errors.append(f"{exc.strerror or exc}: {tail(current, 2)}")
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
                cov.complete = False
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
    """Parse `git worktree list --porcelain` into records."""
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
            current["locked"] = line[len("locked"):].strip() or "no reason recorded"
        elif line.startswith("prunable"):
            current["prunable"] = line[len("prunable"):].strip() or "reported by git"
        elif line.strip() == "bare":
            current["bare"] = True
        elif line.strip() == "detached":
            current["detached"] = True
    if current:
        records.append(current)
    return records


def short_branch(ref: str) -> str:
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


# --------------------------------------------------------------------------
# Evidence and decision
# --------------------------------------------------------------------------

def classify_ignored(entries: list[str]) -> list[str]:
    """Keep only the ignored entries a build would not regenerate."""
    kept = []
    for raw in entries:
        name = raw.strip().rstrip("/")
        base = os.path.basename(name)
        if base in REGENERABLE_IGNORED:
            continue
        if any(fnmatch.fnmatch(base, pattern) for pattern in REGENERABLE_IGNORED if "*" in pattern):
            continue
        kept.append(name)
    return kept


def quantity(count: int, singular: str, plural: str) -> str:
    """Write a count the way a person would read it."""
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def preservation_reasons(facts: dict) -> list[str]:
    """Positive reasons to preserve a directory, in the order they are read.

    This function is the preservation control the mutation test disables. When
    it returns nothing, a directory holding untracked work is no longer
    protected, and the expected decision for that directory must fail.
    """
    reasons: list[str] = []
    if facts.get("locked"):
        reasons.append(f"git reports this worktree locked ({facts['locked']})")
    if facts.get("moved"):
        reasons.append("the recorded path and the real path differ, git worktree repair applies here")
    if facts.get("untracked"):
        sample = ", ".join(facts["untracked"][:3])
        count = quantity(len(facts["untracked"]), "untracked file", "untracked files")
        verb = "lives" if len(facts["untracked"]) == 1 else "live"
        reasons.append(f"{count} {verb} only here ({sample})")
    if facts.get("modified"):
        sample = ", ".join(facts["modified"][:3])
        count = quantity(len(facts["modified"]), "tracked file", "tracked files")
        reasons.append(f"{count} modified and not committed ({sample})")
    kept_ignored = facts.get("ignored_kept") or []
    if kept_ignored:
        sample = ", ".join(kept_ignored[:3])
        count = quantity(len(kept_ignored), "ignored file", "ignored files")
        reasons.append(f"{count} a build does not regenerate ({sample})")
    if facts.get("commits_ahead"):
        count = quantity(facts["commits_ahead"], "commit", "commits")
        verb = "is" if facts["commits_ahead"] == 1 else "are"
        reasons.append(
            f"{count} on this branch {verb} not contained in {facts.get('base_label', 'the default branch')}"
        )
    if facts.get("recent_days") is not None and facts.get("recent_days") <= facts.get("stale_days", 30):
        reasons.append(f"last commit {quantity(facts['recent_days'], 'day', 'days')} before the reference time")
    return reasons


def decide(facts: dict) -> tuple[str, list[str], str]:
    """Return (decision, preservation reasons, remaining condition).

    Three statuses, and the scope of each one is explicit:
      keep                          a positive reason to preserve was found
      removal candidate, to confirm every check in scope passed, and the last
                                    confirmations are named
      undetermined                  something is missing, with the next check

    A missing piece of information or an incomplete inspection can never
    produce a removal candidate. That is the whole point of the third status.
    """
    kind = facts.get("kind", "")

    if facts.get("inspection_error"):
        return (
            UNDETERMINED,
            [],
            f"inspection incomplete ({facts['inspection_error']}): rerun on this directory "
            f"before concluding anything about it",
        )

    if kind == "not registered by any repository":
        return (
            UNDETERMINED,
            [],
            "no repository under the scanned roots claims this directory: establish whether it is "
            "a copy, an export, or a working tree whose metadata was removed, and where its content lives now",
        )

    if kind == "worktree metadata unavailable":
        return (
            UNDETERMINED,
            [],
            f"the recorded metadata path does not exist ({facts.get('gitdir_display', 'unknown')}): find the owner "
            f"repository, then decide with git worktree repair or by reading the directory content",
        )

    if kind == "linked worktree, owner outside the scanned scope":
        return (
            UNDETERMINED,
            [],
            f"owner repository is outside the roots you named ({facts.get('owner_hint', 'unknown path')}): "
            f"include that root, or check this attachment before touching the directory",
        )

    if kind == "independent repository":
        return (
            KEEP,
            ["this is a repository of its own, not a linked worktree"],
            "out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent",
        )

    reasons = preservation_reasons(facts)
    if reasons:
        return KEEP, reasons, "nothing for the removal question. What this directory holds exists nowhere else"

    branch = facts.get("branch") or "this branch"
    remaining = (
        f"confirm that no running process has this path as its working directory, and that `{branch}` is not "
        f"the base of an open review; this run read the filesystem, not your processes and not your forges"
    )
    return CANDIDATE, [], remaining


# --------------------------------------------------------------------------
# Inspection of one candidate
# --------------------------------------------------------------------------

def inspect(directory: str, roots: list[str], now: datetime, stale_days: int,
            git_timeout: float, owner_defaults: dict) -> dict:
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
            linked = [r for r in listing if r.get("worktree") and os.path.normpath(r["worktree"]) != os.path.normpath(directory)]
            facts["evidence"].append(
                quantity(len(linked), "linked worktree", "linked worktrees") + " registered by this repository"
            )
        except CommandError as exc:
            facts["inspection_error"] = str(exc)
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

    # A moved worktree: the metadata still records the previous path.
    recorded = os.path.join(gitdir, "gitdir")
    if os.path.isfile(recorded):
        try:
            with open(recorded, "r", encoding="utf-8", errors="replace") as handle:
                stored = handle.read().strip()
            if os.path.realpath(stored) != os.path.realpath(os.path.join(directory, ".git")):
                facts["moved"] = True
                facts["evidence"].append("the metadata records another path for this worktree")
        except OSError:
            pass

    if os.path.exists(os.path.join(gitdir, "locked")):
        try:
            with open(os.path.join(gitdir, "locked"), "r", encoding="utf-8", errors="replace") as handle:
                reason = handle.read().strip()
        except OSError:
            reason = ""
        facts["locked"] = reason or "no reason recorded"

    try:
        head = git(directory, ["rev-parse", "--abbrev-ref", "HEAD"], git_timeout).strip()
        facts["branch"] = head
        status = git(
            directory,
            ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--no-renames"],
            git_timeout,
        )
    except CommandError as exc:
        facts["inspection_error"] = str(exc)
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
    facts["ignored_regenerable"] = len(ignored) - len(facts["ignored_kept"])

    try:
        last = git(directory, ["log", "-1", "--format=%cI"], git_timeout).strip()
        facts["last_commit"] = last[:10] if last else ""
        if last:
            when = datetime.fromisoformat(last)
            facts["recent_days"] = max(0, (now - when).days)
    except CommandError:
        facts["last_commit"] = ""

    base = owner_defaults.get(owner, "")
    facts["base_label"] = base or "the default branch of the owner repository"
    if base:
        try:
            ahead = git(directory, ["rev-list", "--count", f"{base}..HEAD"], git_timeout).strip()
            facts["commits_ahead"] = int(ahead or "0")
        except (CommandError, ValueError):
            facts["inspection_error"] = "the number of commits not contained in the default branch could not be read"
    else:
        facts["inspection_error"] = "the default branch of the owner repository could not be read"

    facts["observation"] = f"a linked worktree of {os.path.basename(owner)} on branch {facts.get('branch', 'unknown')}"
    return facts


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


def default_branch_of(owner: str, git_timeout: float) -> str:
    """The branch a worktree is compared against, read from the owner itself."""
    for args in (
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
    ):
        try:
            value = git(owner, args, git_timeout).strip()
            if value:
                return value
        except CommandError:
            continue
    return ""


# --------------------------------------------------------------------------
# Optional inventories, each with its boundary written next to it
# --------------------------------------------------------------------------

def read_process_table() -> str:
    return run_command(["ps", "-Ao", "pid=,ppid=,etime=,tty=,comm="], timeout=15.0)


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
        if cwd_lookup is not None:
            cwd = cwd_lookup(pid)
        sessions.append({
            "pid": pid,
            "process": base,
            "elapsed": elapsed,
            "terminal": tty if tty not in ("??", "-") else "none",
            "working_directory": cwd or "not read in this run",
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


def hook_rejection_rate(log_path: str) -> dict:
    """Compute a rejection rate only when the log carries a denominator.

    One call in four means nothing without the number of calls examined over a
    period, the reasons kept apart, and retries counted as retries. A log that
    records only refusals cannot produce that number, and the honest output is
    to say so.
    """
    out: dict = {"log": os.path.basename(log_path)}
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            lines = [line for line in handle if line.strip()]
    except OSError as exc:
        return {**out, "computable": False, "reason": f"log could not be read ({exc.strerror or exc})"}

    examined = rejected = retries = malformed = 0
    reasons: dict[str, int] = {}
    first = last = ""
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        outcome = str(record.get("outcome", ""))
        stamp = str(record.get("ts", ""))
        if stamp:
            first = min(first, stamp) if first else stamp
            last = max(last, stamp) if last else stamp
        if record.get("retry_of"):
            retries += 1
        if outcome in ("observed", "examined", "allowed", "passed", "rejected", "denied"):
            examined += 1
        if outcome in ("rejected", "denied"):
            rejected += 1
            reasons[str(record.get("reason", "unspecified"))] = reasons.get(str(record.get("reason", "unspecified")), 0) + 1

    if examined == 0:
        return {
            **out,
            "computable": False,
            "reason": "rate: not computable from this log, it carries no record of the calls examined, only outcomes without a denominator",
            "records": len(lines),
            "malformed": malformed,
        }
    return {
        **out,
        "computable": True,
        "examined": examined,
        "rejected": rejected,
        "retries": retries,
        "malformed": malformed,
        "period": f"{first} to {last}" if first else "no timestamps in this log",
        "rate": round(rejected / examined, 4),
        "reasons": dict(sorted(reasons.items())),
        "note": "retries are counted separately; a retry of a rejected call is not a second independent rejection",
    }


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def collect(roots: list[str], now: datetime, stale_days: int, budget: float,
            max_depth: int, excludes: list[str], git_timeout: float,
            with_sizes: bool) -> dict:
    roots = [os.path.abspath(r) for r in roots]
    candidates: list[Candidate] = []
    coverages: list[Coverage] = []
    owner_defaults: dict[str, str] = {}
    discovered: list[tuple[str, str]] = []

    for root in roots:
        found, cov = walk_root(root, budget, max_depth, excludes)
        coverages.append(cov)
        for path in found:
            discovered.append((root, path))

    # Read the default branch of every owner once.
    for _root, path in discovered:
        link_kind, gitdir = read_git_link(path)
        owner = os.path.realpath(path) if link_kind == "dir" else owner_of_gitdir(gitdir) if gitdir else ""
        if owner and owner not in owner_defaults and os.path.isdir(os.path.join(owner, ".git")):
            owner_defaults[owner] = default_branch_of(owner, git_timeout)

    for root, path in discovered:
        facts = inspect(path, roots, now, stale_days, git_timeout, owner_defaults)
        decision, reasons, remaining = decide(facts)
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
            remaining=remaining,
            inspection="complete" if not facts.get("inspection_error") else f"incomplete: {facts['inspection_error']}",
            node_modules=trees,
            node_modules_bytes=size,
        )
        if facts.get("untracked"):
            cand.evidence.append(quantity(len(facts["untracked"]), "untracked file", "untracked files"))
        if facts.get("modified"):
            cand.evidence.append(quantity(len(facts["modified"]), "modified tracked file", "modified tracked files"))
        if facts.get("ignored_kept"):
            cand.evidence.append(
                quantity(len(facts["ignored_kept"]), "ignored file", "ignored files")
                + " a build does not regenerate"
            )
        if facts.get("commits_ahead") is not None:
            base = facts.get("base_label", "the default branch")
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
    for owner in sorted(owner_defaults):
        try:
            listing = parse_worktree_list(git(owner, ["worktree", "list", "--porcelain"], git_timeout))
        except CommandError:
            continue
        for record in listing:
            path = record.get("worktree", "")
            if not path or os.path.realpath(path) == os.path.realpath(owner):
                continue
            if not os.path.exists(path):
                absent.append({
                    "owner": os.path.basename(owner),
                    "recorded_path": os.path.basename(path),
                    "branch": short_branch(record.get("branch", "")),
                    "git_says": record.get("prunable", "the directory is absent"),
                    "note": (
                        "this is a registration with no directory. Pruning removes the registration, "
                        "it does not remove any directory that is still on disk."
                    ),
                })

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
        "coverage": [c.as_dict() for c in coverages],
        "counts": counts,
        "decisions": [c.as_dict() for c in candidates],
        "registered_entries_without_directory": absent,
        "boundaries": {
            "network": "the collector calls no external service and sends no report",
            "writes": "no file, index, reference or configuration of an inspected repository is written; git is called with --no-optional-locks",
            "commands": "no cleanup command is printed or executed; a status is a proposal with its evidence",
            "outside_scope": "nothing outside the roots you name is read, including the owner of a worktree attached elsewhere",
        },
    }


def markdown(report: dict, sessions: dict | None, hook: dict | None, with_sizes: bool) -> str:
    lines: list[str] = []
    add = lines.append
    counts = report["counts"]

    add(f"# Workspace triage report")
    add("")
    add(f"Collector `agent-workspace-triage {report['version']}`, read only. "
        f"Reference time {report['reference_time']}. Roots scanned: {', '.join(report['roots'])}.")
    add("")
    add("Every line below is one directory: what was observed, the evidence behind it, the decision it earns, "
        "and the check that is still missing. Nothing here was deleted, and no cleanup command is printed.")
    add("")

    add("## Coverage")
    add("")
    add("| Root | Coverage | Examined | Skipped | Symlinks not followed | Errors |")
    add("|---|---|---|---|---|---|")
    for cov in report["coverage"]:
        errors = "; ".join(cov["errors"]) if cov["errors"] else "none"
        note = cov["coverage"] + (f" ({cov['reason']})" if cov["reason"] else "")
        add(f"| {cov['root']} | {note} | {cov['directories_examined']} | {cov['directories_skipped']} | "
            f"{cov['symlinks_not_followed']} | {errors} |")
    add("")
    add("A walk that stops early is reported as partial. Partial is never read as nothing found, and never as clean.")
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
        (KEEP, "Keep", "A positive reason to preserve was found. These are the directories a count based cleanup would have taken."),
        (CANDIDATE, "Removal candidate, to confirm", "Every check in scope passed. The confirmations that remain are named, because the scan read the filesystem and nothing else."),
        (UNDETERMINED, "Undetermined", "Something is missing. The next check is named. An undetermined line is work, not a shrug."),
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
            add(f"- Decision: {row['decision']}")
            add(f"- Remaining condition: {row['remaining_condition']}")
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
            add(f"- `{row['recorded_path']}` recorded by `{row['owner']}` on branch `{row['branch']}`: {row['git_says']}")
    else:
        add("None found.")
    add("")

    add("## Not measured in this run")
    add("")
    if sessions is None:
        add("- Agent sessions: not inventoried. The optional inventory lists processes with their age, terminal and "
            "working directory, and reports progress as unknown, because no progress source exists on the filesystem.")
    else:
        add(f"- Agent sessions: {len(sessions.get('sessions', []))} process(es) listed, progress unknown for each. "
            "This inventory never claims a session is hung.")
    if hook is None:
        add("- Hook rejection rate: no hook log was given, so no rate is computed. A rate needs the calls examined over "
            "a period, the reasons kept apart, and retries counted as retries.")
    elif not hook.get("computable"):
        add(f"- Hook rejection rate: {hook.get('reason')}")
    else:
        add(f"- Hook rejection rate: {hook['rejected']} of {hook['examined']} calls examined ({hook['rate']:.0%}), "
            f"{hook['retries']} retries counted separately, period {hook['period']}.")
    if not with_sizes:
        add("- node_modules sizes: counted, not weighed. Sizes are an option because weighing them walks every file, "
            "which is the walk that times out on a workspace this size.")
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
                        help="time budget per root for the walk (default 20)")
    parser.add_argument("--max-depth", type=int, default=3, help="how deep below a root to look (default 3)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="directory names to skip, in addition to the built in list")
    parser.add_argument("--stale-days", type=int, default=30,
                        help="a worktree whose last commit is newer than this is preserved (default 30)")
    parser.add_argument("--git-timeout", type=float, default=20.0, help="timeout for each git call (default 20)")
    parser.add_argument("--sizes", action="store_true", help="also weigh the node_modules trees (walks every file)")
    parser.add_argument("--sessions", action="store_true", help="also list the agent processes that exist")
    parser.add_argument("--hook-log", metavar="FILE", help="a hook log to compute a rejection rate from, if it has a denominator")
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
        with_sizes=args.sizes,
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
