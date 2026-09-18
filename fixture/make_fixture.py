#!/usr/bin/env python3
"""Build the synthetic workspace the demonstration report is computed on.

The point of this file is that the report you read is not typed by hand. It is
produced by the collector, on real small git repositories, built here, with
every situation created for a named reason. The composition and the convention
behind the totals are written in fixture/MANIFEST.md, and a test asserts that
the manifest and the built workspace agree.

Nothing here touches anything outside the directory you pass to --out.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_ENV = {
    "GIT_AUTHOR_NAME": "Fixture Builder",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture Builder",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "LC_ALL": "C",
}

OLD = "2026-02-10T09:00:00+00:00"      # stale next to the reference time
RECENT = "2026-09-15T10:00:00+00:00"   # inside the preservation window

# The roots and the repositories carry ordinary names, because a workspace does.
# The situations below are what makes each directory interesting, and the names
# are stable: the tests address the fixture through them, never through an index.
ROOT_NAMES = [
    "platform", "services", "web", "infra", "data", "mobile", "sandbox",
    "experiments", "archive", "vendor", "tools", "ml", "docs-site",
    "integrations", "partners", "internal", "prototypes", "migrations", "ops", "labs",
]

OWNER_NAMES = [
    "api-gateway", "web-console", "worker-pipeline", "billing-service", "auth-service",
    "media-service", "search-service", "admin-tools", "mobile-bff", "data-exports",
    "notifications",
]

SITUATIONS = {
    "infra-cdk-baseline": "a repository of its own, which a count based cleanup would treat as one more directory",
    "api-gateway-wt-oauth-refresh": "work that exists only here and is in no commit",
    "web-console-wt-billing-table": "tracked files modified and not committed",
    "api-gateway-wt-rate-limits": "commits that the default branch does not contain",
    "web-console-wt-checkout-v2": "a worktree moved on disk, which git repairs rather than forgets",
    "api-gateway-wt-on-external-volume": "a worktree locked on purpose, usually on removable or shared storage",
    "worker-pipeline-wt-local-env": "an ignored file a build does not regenerate, for example a local environment file",
    "web-console-wt-search-filters": "recent activity, which is in flight work rather than residue",
    "api-gateway-wt-legacy-export": "clean, contained in the default branch, and old",
    "web-console-wt-old-typography": "only ignored files a build regenerates, which is not a reason to preserve",
    "vendor-sdk-wt-patch-2": "a valid worktree whose owner is outside the roots the scan was given",
    "worker-pipeline-wt-retry-policy": "a worktree whose metadata directory is gone",
    "web-console-copy-2": "a directory that looks like a working tree and that no repository claims",
}


def run(argv: list[str], cwd: str | None = None, when: str | None = None) -> str:
    env = dict(os.environ)
    env.update(BASE_ENV)
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    done = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    if done.returncode != 0:
        raise SystemExit(f"fixture command failed: {' '.join(argv)}\n{done.stderr}")
    return done.stdout


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def node_modules_tree(directory: Path, count: int = 1) -> None:
    """A node_modules tree with a couple of files in it, not an empty folder."""
    places = [directory / "node_modules"]
    if count > 1:
        places.append(directory / "packages" / "api" / "node_modules")
    for place in places[:count]:
        write(place / ".package-lock.json", '{"lockfileVersion": 3}\n')
        write(place / "left-pad" / "index.js", "module.exports = function () {};\n")


def new_repo(path: Path, when: str = OLD) -> Path:
    run(["git", "init", "-q", "-b", "main", str(path)])
    run(["git", "config", "user.name", "Fixture Builder"], cwd=str(path))
    run(["git", "config", "user.email", "fixture@example.invalid"], cwd=str(path))
    run(["git", "config", "commit.gpgsign", "false"], cwd=str(path))
    write(path / "README.md", f"# {path.name}\n\nA small repository built by the fixture.\n")
    write(path / "package.json", '{\n  "name": "fixture",\n  "private": true\n}\n')
    write(path / ".gitignore", "node_modules/\ndist/\n.env\n*.log\n")
    run(["git", "add", "-A"], cwd=str(path))
    run(["git", "commit", "-q", "-m", "initial commit"], cwd=str(path), when=when)
    # What a clone leaves behind, and what the collector needs before it will
    # compare a branch with anything: a remote tracking branch and an
    # origin/HEAD that says which one is the default. Without them the
    # collector reports the repository as undetermined rather than comparing a
    # worktree with whatever branch happens to be checked out.
    head = run(["git", "rev-parse", "HEAD"], cwd=str(path)).strip()
    run(["git", "update-ref", "refs/remotes/origin/main", head], cwd=str(path))
    run(["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"], cwd=str(path))
    return path


def add_worktree(owner: Path, path: Path, branch: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "worktree", "add", "-q", "-b", branch, str(path), "main"], cwd=str(owner))
    return path


def build(out: Path, scale: str) -> dict:
    workspace = out / "workspace"
    outside = out / "outside-scope"
    workspace.mkdir(parents=True, exist_ok=True)
    outside.mkdir(parents=True, exist_ok=True)

    if scale == "full":
        n_roots, n_owners, n_filler, n_unregistered, n_broken, n_absent = 20, 11, 63, 41, 5, 2
    else:
        n_roots, n_owners, n_filler, n_unregistered, n_broken, n_absent = 6, 3, 3, 3, 1, 1

    roots = [workspace / ROOT_NAMES[index] for index in range(n_roots)]
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)

    owners: list[Path] = []
    for index in range(n_owners):
        owners.append(new_repo(roots[index % n_roots] / OWNER_NAMES[index % len(OWNER_NAMES)]))
    alpha = owners[0]

    # A repository of its own, owning no worktree: the directory a cleanup
    # driven by counts would treat as one more candidate.
    new_repo(roots[0] / "infra-cdk-baseline")

    placed_node_modules = 0
    by_name = {owner.name: owner for owner in owners}

    def owner_for(directory_name: str) -> Path:
        """Attach a worktree to the repository its name belongs to."""
        for candidate, owner in by_name.items():
            if directory_name.startswith(candidate + "-wt-"):
                return owner
        return alpha

    def situation(directory_name: str, root_index: int) -> Path:
        branch = "wt/" + directory_name.split("-wt-", 1)[1]
        owner = owner_for(directory_name)
        return add_worktree(owner, roots[root_index % n_roots] / directory_name, branch)

    # Work that exists only in this directory.
    untracked = situation("api-gateway-wt-oauth-refresh", 0)
    write(untracked / "notes-from-the-session.md", "A plan that was never committed.\n")

    # Tracked files changed and not committed.
    modified = situation("web-console-wt-billing-table", 2)
    write(modified / "README.md", "# changed in the worktree, not committed\n")

    # Commits the default branch does not contain.
    ahead = situation("api-gateway-wt-rate-limits", 0)
    write(ahead / "feature.py", "def feature():\n    return True\n")
    run(["git", "add", "-A"], cwd=str(ahead))
    run(["git", "commit", "-q", "-m", "a commit that lives only on this branch"], cwd=str(ahead), when=OLD)

    # A worktree moved on disk after it was created.
    moved_from = situation("web-console-wt-checkout", 2)
    moved_to = moved_from.parent / "web-console-wt-checkout-v2"
    os.rename(moved_from, moved_to)

    # A worktree locked on purpose.
    locked = situation("api-gateway-wt-on-external-volume", 0)
    run(["git", "worktree", "lock", "--reason", "external volume", str(locked)],
        cwd=str(owner_for("api-gateway-wt-on-external-volume")))

    # An ignored file no build regenerates, next to one that a build does.
    ignored_kept = situation("worker-pipeline-wt-local-env", 1)
    write(ignored_kept / ".env", "DATABASE_URL=postgres://localhost/only-here\n")
    node_modules_tree(ignored_kept)
    placed_node_modules += 1

    # Clean, contained in the default branch, and old.
    situation("api-gateway-wt-legacy-export", 0)

    # Only ignored files a build regenerates.
    regenerable = situation("web-console-wt-old-typography", 2)
    node_modules_tree(regenerable)
    write(regenerable / "dist" / "bundle.js", "console.log(1);\n")
    placed_node_modules += 1

    # Owner outside the roots the collector is given.
    outside_owner = new_repo(outside / "vendor-sdk")
    add_worktree(outside_owner, roots[9 % n_roots] / "vendor-sdk-wt-patch-2", "wt/patch-2")

    # Metadata gone: the worktree stays, its registration does not.
    broken_names = ["worker-pipeline-wt-retry-policy"] + [f"wt-{200 + i:03d}" for i in range(1, n_broken)]
    for index, name in enumerate(broken_names):
        owner = owners[(index + 1) % len(owners)]
        path = add_worktree(owner, roots[(index + 1) % n_roots] / name, f"wt/broken-{index:02d}")
        link = (path / ".git").read_text(encoding="utf-8").split("gitdir:", 1)[1].strip()
        shutil.rmtree(link)

    # Registration without a directory: metadata only, no directory to remove.
    for index in range(n_absent):
        owner = owners[index % len(owners)]
        path = add_worktree(owner, roots[(index + 2) % n_roots] / f"wt-{300 + index:03d}", f"wt/absent-{index:02d}")
        shutil.rmtree(path)

    # Directories no repository claims.
    leftover_shapes = ["{name}-copy-{n}", "{name}-backup-{n}", "{name}-old-{n}", "{name}-{n}-wip"]
    unregistered_names = ["web-console-copy-2"] + [
        leftover_shapes[i % len(leftover_shapes)].format(name=OWNER_NAMES[i % len(OWNER_NAMES)], n=i)
        for i in range(1, n_unregistered)
    ]
    for index, name in enumerate(unregistered_names):
        path = roots[(index + 3) % n_roots] / name
        write(path / "package.json", '{\n  "name": "leftover",\n  "private": true\n}\n')
        write(path / "src" / "index.ts", "export const value = 1;\n")
        if index < (30 if scale == "full" else 2):
            node_modules_tree(path)
            placed_node_modules += 1

    # Ordinary linked worktrees, the bulk of a workspace like this one.
    target_node_modules = 83 if scale == "full" else 8
    for index in range(n_filler):
        owner = owners[index % len(owners)]
        root = roots[(index + 5) % n_roots]
        path = add_worktree(owner, root / f"{owner.name}-wt-{index:03d}", f"wt/task-{index:03d}")
        if index % 7 == 3:
            write(path / "scratch.md", "a note left in the worktree\n")
        remaining = target_node_modules - placed_node_modules
        if remaining > 0:
            count = 2 if (index % 9 == 0 and remaining > 1) else 1
            node_modules_tree(path, count)
            placed_node_modules += count

    recent = situation("web-console-wt-search-filters", 2)
    write(recent / "recent.py", "value = 1\n")
    run(["git", "add", "-A"], cwd=str(recent))
    run(["git", "commit", "-q", "-m", "recent work"], cwd=str(recent), when=RECENT)
    run(["git", "merge", "-q", "--ff-only", "wt/search-filters"],
        cwd=str(owner_for("web-console-wt-search-filters")))

    composition = {
        "scale": scale,
        "roots": n_roots,
        "independent_repositories": n_owners + 1,
        "linked_worktrees_in_scope": 9 + n_broken + n_filler,
        "linked_worktrees_owner_outside_scope": 1,
        "worktree_metadata_unavailable": n_broken,
        "not_registered_by_any_repository": n_unregistered,
        "registrations_without_directory": n_absent + 1,
        "node_modules_trees": placed_node_modules,
        "candidate_directories": (n_owners + 1) + 9 + n_broken + n_filler + 1 + n_unregistered,
        "situations": SITUATIONS,
    }
    # The worktrees whose metadata was removed are no longer linked worktrees.
    composition["linked_worktrees_in_scope"] -= n_broken
    return composition


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the synthetic workspace the demonstration report runs on.")
    parser.add_argument("--out", required=True, help="an empty directory to build the workspace in")
    parser.add_argument("--scale", choices=("full", "small"), default="full")
    parser.add_argument("--print-composition", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out).absolute()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        print(f"--out must be empty: {out}", file=sys.stderr)
        return 2

    composition = build(out, args.scale)
    (out / "composition.json").write_text(json.dumps(composition, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.print_composition:
        print(json.dumps(composition, indent=2, sort_keys=True))
    else:
        print(f"built {composition['candidate_directories']} candidate directories under {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
