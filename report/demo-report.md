# Workspace triage report

Collector `agent-workspace-triage 1.1`, read only. Reference time 2026-09-18. Roots scanned: archive, data, docs-site, experiments, infra, integrations, internal, labs, migrations, ml, mobile, ops, partners, platform, prototypes, sandbox, services, tools, vendor, web.

Fixture convention: 131 candidate directories, including 41 unregistered. Illustrative hypothesis, not a reconstruction. The composition and every situation built into this workspace are written in fixture/MANIFEST.md.

Every line below is one directory: what was observed, the evidence behind it, the decision it earns, and the check that is still missing. Nothing here was deleted, and no cleanup command is printed.

## Coverage

| Root | Coverage | Examined | Not opened | Errors |
|---|---|---|---|---|
| archive | bounded (6 candidate directories not descended into) | 6 | 6 | none |
| data | bounded (7 candidate directories not descended into) | 7 | 7 | none |
| docs-site | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| experiments | bounded (7 candidate directories not descended into) | 7 | 7 | none |
| infra | bounded (8 candidate directories not descended into) | 8 | 8 | none |
| integrations | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| internal | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| labs | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| migrations | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| ml | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| mobile | bounded (8 candidate directories not descended into) | 8 | 8 | none |
| ops | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| partners | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| platform | bounded (11 candidate directories not descended into) | 11 | 11 | none |
| prototypes | bounded (5 candidate directories not descended into) | 5 | 5 | none |
| sandbox | bounded (7 candidate directories not descended into) | 7 | 7 | none |
| services | bounded (8 candidate directories not descended into) | 8 | 8 | none |
| tools | bounded (6 candidate directories not descended into) | 6 | 6 | none |
| vendor | bounded (7 candidate directories not descended into) | 7 | 7 | none |
| web | bounded (11 candidate directories not descended into) | 11 | 11 | none |

Depth limit in force: 3 levels below each root. The walk stops at a candidate directory instead of descending into it, so a working tree nested inside another one is not discovered. Excluded names: .cache, .git, .gradle, .hg, .mypy_cache, .next, .nuxt, .pytest_cache and the rest of the built in list.

`complete` means nothing was left unopened. `bounded` means the walk finished inside the limits above and left the counted subtrees unopened. `partial` means it stopped for a reason it did not choose, and partial is never read as nothing found, and never as clean.

The time budget of 120s bounds the discovery walk of one root. It does not bound the whole run: every git inspection has its own timeout (30s), and the node_modules count of each candidate directory receives that budget again.

## Counts

- candidate directories: 131
- linked worktrees in scope: 72
- linked worktrees owner outside scope: 1
- worktree metadata unavailable: 5
- independent repositories: 12
- not registered by any repository: 41
- node modules trees: 83
- registered entries without directory: 3

- decisions: 28 keep, 56 removal candidate to confirm, 47 undetermined

## Keep (28)

A positive reason to preserve was found, and each reason carries the confirmation it still needs. These are the directories a count based cleanup would have taken.

### `archive/billing-service-wt-003`

- Observation: a linked worktree of billing-service on branch wt/task-003
- Evidence: attached to billing-service; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `archive/mobile-bff`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 5 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `data/auth-service`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 6 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `data/auth-service-wt-059`

- Observation: a linked worktree of auth-service on branch wt/task-059
- Evidence: attached to auth-service; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `experiments/admin-tools`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 6 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `infra/billing-service`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 6 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `infra/media-service-wt-038`

- Observation: a linked worktree of media-service on branch wt/task-038
- Evidence: attached to media-service; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `internal/notifications-wt-010`

- Observation: a linked worktree of notifications on branch wt/task-010
- Evidence: attached to notifications; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `migrations/mobile-bff-wt-052`

- Observation: a linked worktree of mobile-bff on branch wt/task-052
- Evidence: attached to mobile-bff; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `mobile/media-service`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 6 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `platform/api-gateway`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 11 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `platform/api-gateway-wt-oauth-refresh`

- Observation: a linked worktree of api-gateway on branch wt/oauth-refresh
- Evidence: attached to api-gateway; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (notes-from-the-session.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `platform/api-gateway-wt-on-external-volume`

- Observation: a linked worktree of api-gateway on branch wt/on-external-volume
- Evidence: attached to api-gateway; every commit on this branch is contained in origin/main
- Reason to preserve: git reports this worktree locked, and the reason recorded in the lock was not read
- Decision: Keep pending confirmation.
- Still open: Check why this worktree was locked, and whether the storage it stands on is available, before reconsidering removal.

### `platform/api-gateway-wt-rate-limits`

- Observation: a linked worktree of api-gateway on branch wt/rate-limits
- Evidence: attached to api-gateway; 1 commit not contained in origin/main
- Reason to preserve: 1 commit on this branch is not contained in origin/main
- Decision: Keep pending confirmation.
- Still open: Confirm that this commit exists on another reference before reconsidering removal.

### `platform/infra-cdk-baseline`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 0 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `prototypes/data-exports-wt-031`

- Observation: a linked worktree of data-exports on branch wt/task-031
- Evidence: attached to data-exports; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `sandbox/search-service`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 6 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `services/web-console`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 11 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `services/worker-pipeline-wt-local-env`

- Observation: a linked worktree of worker-pipeline on branch wt/local-env
- Evidence: attached to worker-pipeline; 1 ignored entry outside the assumed rebuildable list; every commit on this branch is contained in origin/main
- Reason to preserve: Ignored .env found. Its rebuildability and backup status were not checked.
- Decision: Keep pending confirmation.
- Still open: Confirm how this file can be restored before reconsidering removal.

### `tools/notifications`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 5 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `tools/web-console-wt-045`

- Observation: a linked worktree of web-console on branch wt/task-045
- Evidence: attached to web-console; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `vendor/data-exports`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 5 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

### `vendor/worker-pipeline-wt-024`

- Observation: a linked worktree of worker-pipeline on branch wt/task-024
- Evidence: attached to worker-pipeline; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `web/search-service-wt-017`

- Observation: a linked worktree of search-service on branch wt/task-017
- Evidence: attached to search-service; 1 untracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 untracked file here and in no commit (scratch.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that this untracked work is kept somewhere else before reconsidering removal.

### `web/web-console-wt-billing-table`

- Observation: a linked worktree of web-console on branch wt/billing-table
- Evidence: attached to web-console; 1 modified tracked file; every commit on this branch is contained in origin/main
- Reason to preserve: 1 tracked file modified and not committed (README.md)
- Decision: Keep pending confirmation.
- Still open: Confirm that these uncommitted changes are kept somewhere else before reconsidering removal.

### `web/web-console-wt-checkout-v2`

- Observation: a linked worktree of web-console on branch wt/checkout
- Evidence: attached to web-console; the metadata records another path for this worktree; every commit on this branch is contained in origin/main
- Reason to preserve: the recorded path and the real path differ, which is what git worktree repair reconciles
- Decision: Keep pending confirmation.
- Still open: Reconcile the recorded path with the real path (git worktree repair) before deciding anything about this directory.

### `web/web-console-wt-search-filters`

- Observation: a linked worktree of web-console on branch wt/search-filters
- Evidence: attached to web-console; 1 commit not contained in origin/main
- Reason to preserve: 1 commit on this branch is not contained in origin/main; last commit 2 days before the reference time
- Decision: Keep pending confirmation.
- Still open: Confirm that this commit exists on another reference before reconsidering removal. Confirm this worktree is no longer in use before reconsidering removal.

### `web/worker-pipeline`

- Observation: a repository with its own history, holding its main working tree
- Evidence: .git is a directory, so this is not a linked worktree; 7 linked worktrees registered by this repository
- Reason to preserve: this is a repository of its own, not a linked worktree
- Decision: Keep. This is a repository of its own, not a linked worktree.
- Still open: Out of scope for worktree triage: it holds its own history, so it is compared with its remote, not with a parent.

## Removal candidate, to confirm (56)

The checks in scope were read and came back empty; they are listed as evidence. The confirmations that remain are named, because the scan read the filesystem and nothing else.

### `archive/notifications-wt-043`

- Observation: a linked worktree of notifications on branch wt/task-043
- Evidence: attached to notifications; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-043` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `archive/web-console-wt-023`

- Observation: a linked worktree of web-console on branch wt/task-023
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-023` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `data/mobile-bff-wt-019`

- Observation: a linked worktree of mobile-bff on branch wt/task-019
- Evidence: attached to mobile-bff; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-019` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `data/search-service-wt-039`

- Observation: a linked worktree of search-service on branch wt/task-039
- Evidence: attached to search-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-039` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `docs-site/admin-tools-wt-007`

- Observation: a linked worktree of admin-tools on branch wt/task-007
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-007` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `docs-site/billing-service-wt-047`

- Observation: a linked worktree of billing-service on branch wt/task-047
- Evidence: attached to billing-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-047` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `docs-site/media-service-wt-027`

- Observation: a linked worktree of media-service on branch wt/task-027
- Evidence: attached to media-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-027` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `experiments/admin-tools-wt-062`

- Observation: a linked worktree of admin-tools on branch wt/task-062
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-062` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `experiments/api-gateway-wt-022`

- Observation: a linked worktree of api-gateway on branch wt/task-022
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-022` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `experiments/data-exports-wt-042`

- Observation: a linked worktree of data-exports on branch wt/task-042
- Evidence: attached to data-exports; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-042` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `experiments/worker-pipeline-wt-002`

- Observation: a linked worktree of worker-pipeline on branch wt/task-002
- Evidence: attached to worker-pipeline; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-002` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `infra/admin-tools-wt-018`

- Observation: a linked worktree of admin-tools on branch wt/task-018
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-018` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `infra/billing-service-wt-058`

- Observation: a linked worktree of billing-service on branch wt/task-058
- Evidence: attached to billing-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-058` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `integrations/auth-service-wt-048`

- Observation: a linked worktree of auth-service on branch wt/task-048
- Evidence: attached to auth-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-048` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `integrations/mobile-bff-wt-008`

- Observation: a linked worktree of mobile-bff on branch wt/task-008
- Evidence: attached to mobile-bff; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-008` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `integrations/search-service-wt-028`

- Observation: a linked worktree of search-service on branch wt/task-028
- Evidence: attached to search-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-028` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `internal/mobile-bff-wt-030`

- Observation: a linked worktree of mobile-bff on branch wt/task-030
- Evidence: attached to mobile-bff; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-030` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `internal/search-service-wt-050`

- Observation: a linked worktree of search-service on branch wt/task-050
- Evidence: attached to search-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-050` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `labs/billing-service-wt-014`

- Observation: a linked worktree of billing-service on branch wt/task-014
- Evidence: attached to billing-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-014` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `labs/notifications-wt-054`

- Observation: a linked worktree of notifications on branch wt/task-054
- Evidence: attached to notifications; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-054` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `labs/web-console-wt-034`

- Observation: a linked worktree of web-console on branch wt/task-034
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-034` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `migrations/notifications-wt-032`

- Observation: a linked worktree of notifications on branch wt/task-032
- Evidence: attached to notifications; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-032` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `migrations/web-console-wt-012`

- Observation: a linked worktree of web-console on branch wt/task-012
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-012` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ml/auth-service-wt-026`

- Observation: a linked worktree of auth-service on branch wt/task-026
- Evidence: attached to auth-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-026` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ml/search-service-wt-006`

- Observation: a linked worktree of search-service on branch wt/task-006
- Evidence: attached to search-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-006` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ml/worker-pipeline-wt-046`

- Observation: a linked worktree of worker-pipeline on branch wt/task-046
- Evidence: attached to worker-pipeline; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-046` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `mobile/admin-tools-wt-040`

- Observation: a linked worktree of admin-tools on branch wt/task-040
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-040` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `mobile/api-gateway-wt-000`

- Observation: a linked worktree of api-gateway on branch wt/task-000
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-000` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `mobile/data-exports-wt-020`

- Observation: a linked worktree of data-exports on branch wt/task-020
- Evidence: attached to data-exports; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-020` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `mobile/media-service-wt-060`

- Observation: a linked worktree of media-service on branch wt/task-060
- Evidence: attached to media-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-060` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ops/api-gateway-wt-033`

- Observation: a linked worktree of api-gateway on branch wt/task-033
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-033` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ops/data-exports-wt-053`

- Observation: a linked worktree of data-exports on branch wt/task-053
- Evidence: attached to data-exports; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-053` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `ops/worker-pipeline-wt-013`

- Observation: a linked worktree of worker-pipeline on branch wt/task-013
- Evidence: attached to worker-pipeline; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-013` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `partners/admin-tools-wt-029`

- Observation: a linked worktree of admin-tools on branch wt/task-029
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-029` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `partners/data-exports-wt-009`

- Observation: a linked worktree of data-exports on branch wt/task-009
- Evidence: attached to data-exports; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-009` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `partners/media-service-wt-049`

- Observation: a linked worktree of media-service on branch wt/task-049
- Evidence: attached to media-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-049` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `platform/api-gateway-wt-055`

- Observation: a linked worktree of api-gateway on branch wt/task-055
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-055` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `platform/api-gateway-wt-legacy-export`

- Observation: a linked worktree of api-gateway on branch wt/legacy-export
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/legacy-export` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `platform/auth-service-wt-015`

- Observation: a linked worktree of auth-service on branch wt/task-015
- Evidence: attached to auth-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-015` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `platform/worker-pipeline-wt-035`

- Observation: a linked worktree of worker-pipeline on branch wt/task-035
- Evidence: attached to worker-pipeline; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-035` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `prototypes/admin-tools-wt-051`

- Observation: a linked worktree of admin-tools on branch wt/task-051
- Evidence: attached to admin-tools; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-051` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `prototypes/api-gateway-wt-011`

- Observation: a linked worktree of api-gateway on branch wt/task-011
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-011` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `sandbox/mobile-bff-wt-041`

- Observation: a linked worktree of mobile-bff on branch wt/task-041
- Evidence: attached to mobile-bff; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-041` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `sandbox/notifications-wt-021`

- Observation: a linked worktree of notifications on branch wt/task-021
- Evidence: attached to notifications; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-021` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `sandbox/search-service-wt-061`

- Observation: a linked worktree of search-service on branch wt/task-061
- Evidence: attached to search-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-061` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `sandbox/web-console-wt-001`

- Observation: a linked worktree of web-console on branch wt/task-001
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-001` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `services/billing-service-wt-036`

- Observation: a linked worktree of billing-service on branch wt/task-036
- Evidence: attached to billing-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-036` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `services/media-service-wt-016`

- Observation: a linked worktree of media-service on branch wt/task-016
- Evidence: attached to media-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-016` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `services/web-console-wt-056`

- Observation: a linked worktree of web-console on branch wt/task-056
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-056` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `tools/billing-service-wt-025`

- Observation: a linked worktree of billing-service on branch wt/task-025
- Evidence: attached to billing-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-025` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `tools/media-service-wt-005`

- Observation: a linked worktree of media-service on branch wt/task-005
- Evidence: attached to media-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-005` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `vendor/api-gateway-wt-044`

- Observation: a linked worktree of api-gateway on branch wt/task-044
- Evidence: attached to api-gateway; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-044` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `vendor/auth-service-wt-004`

- Observation: a linked worktree of auth-service on branch wt/task-004
- Evidence: attached to auth-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-004` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `web/auth-service-wt-037`

- Observation: a linked worktree of auth-service on branch wt/task-037
- Evidence: attached to auth-service; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-037` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `web/web-console-wt-old-typography`

- Observation: a linked worktree of web-console on branch wt/old-typography
- Evidence: attached to web-console; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/old-typography` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

### `web/worker-pipeline-wt-057`

- Observation: a linked worktree of worker-pipeline on branch wt/task-057
- Evidence: attached to worker-pipeline; no modified tracked file; no untracked file; no ignored entry outside the assumed rebuildable list; not locked; the recorded path matches the real path; last commit 2026-02-10, 219 days before the reference time; every commit on this branch is contained in origin/main
- Decision: Removal candidate, to confirm. The checks listed as evidence were read; the confirmations left are named.
- Still open: Confirm that no running process has this path as its working directory, and that `wt/task-057` is not the base of an open review. This run read the filesystem, not your processes and not your forges.

## Undetermined (47)

Something is missing. The next check is named. An undetermined line is work, not a shrug.

### `archive/billing-service-backup-25`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `archive/media-service-backup-5`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `data/notifications-backup-21`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `data/web-console-backup-1`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `data/wt-203`

- Observation: a worktree whose metadata directory is gone
- Evidence: .git points at auth-service/.git/worktrees/wt-203; that path does not exist
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The recorded metadata path does not exist (auth-service/.git/worktrees/wt-203). Find the owner repository, then decide with git worktree repair or by reading the directory content.

### `docs-site/admin-tools-backup-29`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `docs-site/data-exports-backup-9`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `experiments/auth-service-copy-4`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `experiments/worker-pipeline-copy-24`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `infra/admin-tools-copy-40`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `infra/data-exports-copy-20`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `infra/web-console-copy-2`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `infra/wt-202`

- Observation: a worktree whose metadata directory is gone
- Evidence: .git points at billing-service/.git/worktrees/wt-202; that path does not exist
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The recorded metadata path does not exist (billing-service/.git/worktrees/wt-202). Find the owner repository, then decide with git worktree repair or by reading the directory content.

### `integrations/mobile-bff-old-30`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `integrations/notifications-old-10`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `internal/notifications-copy-32`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `internal/web-console-copy-12`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `labs/billing-service-copy-36`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `labs/media-service-copy-16`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `migrations/billing-service-old-14`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `migrations/web-console-old-34`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `ml/mobile-bff-copy-8`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `ml/search-service-copy-28`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `mobile/api-gateway-old-22`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `mobile/worker-pipeline-old-2`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `mobile/wt-204`

- Observation: a worktree whose metadata directory is gone
- Evidence: .git points at media-service/.git/worktrees/wt-204; that path does not exist
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The recorded metadata path does not exist (media-service/.git/worktrees/wt-204). Find the owner repository, then decide with git worktree repair or by reading the directory content.

### `ops/auth-service-15-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `ops/worker-pipeline-35-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `partners/api-gateway-11-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `partners/data-exports-31-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `platform/auth-service-backup-37`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `platform/search-service-backup-17`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `prototypes/api-gateway-backup-33`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `prototypes/worker-pipeline-backup-13`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `sandbox/billing-service-3-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `sandbox/web-console-23-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `services/admin-tools-old-18`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `services/media-service-old-38`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `services/worker-pipeline-wt-retry-policy`

- Observation: a worktree whose metadata directory is gone
- Evidence: .git points at web-console/.git/worktrees/worker-pipeline-wt-retry-policy; that path does not exist
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The recorded metadata path does not exist (web-console/.git/worktrees/worker-pipeline-wt-retry-policy). Find the owner repository, then decide with git worktree repair or by reading the directory content.

### `tools/admin-tools-7-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `tools/media-service-27-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `vendor/auth-service-old-26`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `vendor/search-service-old-6`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `vendor/vendor-sdk-wt-patch-2`

- Observation: a valid worktree attached to a repository the scan was not asked to look at
- Evidence: metadata at vendor-sdk/.git/worktrees/vendor-sdk-wt-patch-2; owner repository is outside the scanned roots
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The owner repository is outside the roots you named (outside-scope/vendor-sdk). Include that root, or check this attachment before touching the directory.

### `web/mobile-bff-19-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `web/search-service-39-wip`

- Observation: a directory that looks like a working tree, with no link to any repository
- Evidence: no .git entry; project markers present on disk
- Decision: Undetermined. Nothing here supports a removal.
- Still open: No repository under the scanned roots claims this directory. Establish whether it is a copy, an export, or a working tree whose metadata was removed, and where its content lives now.

### `web/wt-201`

- Observation: a worktree whose metadata directory is gone
- Evidence: .git points at worker-pipeline/.git/worktrees/wt-201; that path does not exist
- Decision: Undetermined. Nothing here supports a removal.
- Still open: The recorded metadata path does not exist (worker-pipeline/.git/worktrees/wt-201). Find the owner repository, then decide with git worktree repair or by reading the directory content.

## Registrations without a directory (3)

These are entries in a repository that name a worktree directory which is not on disk. They are metadata. Pruning them removes the registration and removes no directory.

- `wt-300` recorded by `api-gateway` on branch `wt/absent-00`: this is a registration with no directory. Pruning removes the registration, it does not remove any directory that is still on disk.
- `wt-301` recorded by `web-console` on branch `wt/absent-01`: this is a registration with no directory. Pruning removes the registration, it does not remove any directory that is still on disk.
- `web-console-wt-checkout` recorded by `web-console` on branch `wt/checkout`: this is the previous path of web/web-console-wt-checkout-v2, which was moved on disk. Nothing is missing: git worktree repair reconciles the registration with the real path.

## Not measured in this run

- Agent sessions: not inventoried. The optional inventory lists processes with their age, terminal and working directory, and reports progress as unknown, because no progress source exists on the filesystem.
- Hook rejection rate: no hook log was given, so no rate is computed. A rate needs a log that says it records every call the control examined, over a period, with an identifier per attempt.
- node_modules sizes: counted, not weighed. Sizes are an option because weighing them walks every file, which is the walk that times out on a workspace this size.

## Boundaries

- no external service is called and no report is sent: the collector imports no network client, and a control runs a whole collection with no network access at all
- nothing under the roots you name is written: no file, no index, no reference, no configuration. Git is called with --no-optional-locks, and a repository that configures a content filter is left uninspected rather than have git run that filter. The report is written where you ask for it, and nowhere else
- no cleanup command is printed or executed; a status is a proposal with its evidence
- nothing outside the roots you name is read, including the owner of a worktree attached elsewhere, which is not asked anything at all
