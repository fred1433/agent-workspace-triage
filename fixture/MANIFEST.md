# The synthetic workspace: what it contains, and the convention behind its numbers

The report on the page is not typed by hand. It is the output of the collector,
run on the workspace this directory builds, with real git repositories in it.
This file says what that workspace is, so the report can be read with the right
amount of trust.

## The convention, stated so it can be contested

The counts come from a description of a real workspace: 131 worktree
directories across 20 roots, 83 node_modules trees, 41 directories git no
longer tracks.

That description does not say whether the 41 are inside the 131 or in addition
to them, and it says nothing about their shape. So a choice had to be made, and
here it is, in the open:

> **131 candidate directories, of which 41 are not registered by any
> repository.** An illustrative hypothesis, not a reproduction.

Second choice, for the same reason: **the twenty roots are not twenty
repositories**. Twelve repositories of their own live inside them, and the
worktrees are spread across the roots the way they spread in practice, which is
not evenly.

A number in the report is therefore one of three things, and the report keeps
them apart: measured on this workspace, assumed while building it, or not
available at all.

## Composition

<!-- composition:start -->
```
roots: 20
candidate_directories: 131
independent_repositories: 12
linked_worktrees_in_scope: 72
linked_worktrees_owner_outside_scope: 1
worktree_metadata_unavailable: 5
not_registered_by_any_repository: 41
registrations_without_directory: 3
node_modules_trees: 83
```
<!-- composition:end -->

A test compares this block with the workspace the builder actually produces, so
this file cannot quietly drift away from it.

## The situations, and why each one exists

Every situation below is built on purpose, because it is a case where a
cleanup driven by counts takes the wrong decision.

| Directory | What it is | Why it is here |
|---|---|---|
| `infra-cdk-baseline` | a repository with its own history | a count sees one more directory, git sees a repository that answers to nobody else |
| `api-gateway-wt-oauth-refresh` | a worktree holding files in no commit | the work exists only there |
| `web-console-wt-billing-table` | tracked files modified, not committed | the same, in a form that a clean check catches only if it runs |
| `api-gateway-wt-rate-limits` | commits the default branch does not contain | removing the directory would not lose the branch, but nothing says the branch was kept anywhere else |
| `web-console-wt-checkout-v2` | a worktree moved on disk | git repairs this, it does not forget it, and the registration still names the old path |
| `api-gateway-wt-on-external-volume` | a worktree locked on purpose | a lock is a decision someone already took, usually about storage that is not always mounted |
| `worker-pipeline-wt-local-env` | an ignored file no build regenerates | an environment file is ignored by git and is still the only copy |
| `web-console-wt-search-filters` | recent activity | work in flight is not residue |
| `api-gateway-wt-legacy-export` | clean, contained, old | the case where a removal proposal is defensible, once the named confirmations are made |
| `web-console-wt-old-typography` | only ignored files a build regenerates | node_modules is not a reason to preserve anything |
| `vendor-sdk-wt-patch-2` | a valid worktree whose owner lives outside the scanned roots | the collector does not read outside the roots it was given, so it says what is missing |
| `worker-pipeline-wt-retry-policy` | a worktree whose metadata directory is gone | the attachment cannot be read, so nothing can be concluded from it |
| `web-console-copy-2` | a directory no repository claims | this is the shape of the directories a count calls orphaned, and it is exactly where a decision needs more than a count |

Two more things exist in the workspace and are not directories to decide about:
registrations that name a directory which is not on disk, and node_modules
trees. Pruning a registration removes the registration. It removes no
directory.
