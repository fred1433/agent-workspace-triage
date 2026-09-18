# agent workspace triage

A read only pass over a sprawling agent workspace that ends in decisions rather
than counts: what to preserve and why, what could be removed once named
confirmations are made, and what cannot be concluded yet, with the next check
spelled out.

Nothing here connects to anything. One file, Python 3.11 or newer, standard
library only.

```bash
python3 triage.py --root ~/code --root ~/work --markdown triage.md
```

The report published at <https://workspace-triage.theaipipe.com> is the output
of this collector on the synthetic workspace built by `fixture/make_fixture.py`,
regenerated and compared byte for byte on every commit.

## What it decides, and how

Every directory that looks like a working tree gets one of three statuses, and
the scope of each one is explicit.

| Status | What it means |
|---|---|
| **Keep** | a positive reason to preserve was found: untracked work, uncommitted changes, commits the default branch does not contain, an ignored file no build regenerates, a lock, a move that git repairs, or recent activity |
| **Removal candidate, to confirm** | every check in scope passed, and the confirmations that are left are named |
| **Undetermined** | something is missing, with the next check named |

Missing information and an inspection that did not finish both produce
**undetermined**, never a removal candidate. That rule is what the tests spend
most of their time on.

Each line carries the same four parts: what was observed, the evidence, the
decision, the condition that is still open.

## What git is actually asked

A directory that is not registered is not the same thing as a directory that
can go. The collector separates:

- a repository with its own history, which answers to nobody else;
- a valid linked worktree of a repository inside the roots you named;
- a worktree attached to a repository outside those roots, which is a question, not a finding;
- a worktree whose metadata directory is gone;
- a worktree that was moved, which `git worktree repair` fixes;
- a worktree that is locked, usually because its storage is not always there;
- a registration that names a directory which is not on disk, which is metadata: pruning it removes the registration and removes no directory;
- a directory that looks like a working tree and that no repository claims.

## Boundaries, and how each one is tested

- **No external call.** The collector imports no network module, runs only
  `git`, `ps` and `lsof` from a fixed allow list, and a test runs it behind a
  listener that counts connections and sees none. The listener is exercised in
  the same test, so a zero means something.
- **Read only for real.** Read only is not the absence of a remove command: a
  plain `git status` can refresh and write the index, which is why every call
  carries `--no-optional-locks`. A test fingerprints every file, directory,
  index, reference and configuration under the roots, runs the collector, and
  compares.
- **No cleanup command.** The report names the condition that is left, never a
  command to paste. A status is a proposal with its evidence.
- **Names, not contents.** File names appear in the report. File contents do
  not, and neither do absolute paths of the machine that ran it.
- **A walk that stops early says so.** There is a time budget per root, a depth
  limit, explicit exclusions, symlinks that are counted and not followed, and
  unreadable directories that become errors. Partial coverage is never
  published as a clean result.

## What it does not do

- It does not detect a hung session. `--sessions` lists the agent processes
  that exist with their age, terminal and working directory, and reports
  progress as `unknown (no progress source)`. A process name and an age
  describe a process, not the progress of the work it was given. Detecting a
  suspected block needs a progress event or a declared wait, a session
  identity, and a documented threshold.
- It does not compute a rejection rate out of a log of refusals. With
  `--hook-log` it computes one only when the log carries the calls examined,
  and says `rate: not computable from this log` otherwise. See `HOOK.md`.
- It does not weigh `node_modules` unless you ask with `--sizes`, because
  weighing walks every file, and that walk is the one that times out.
- It does not read anything outside the roots you name.

## Narrowing a search without removing anything

The symptom that usually starts this is a search that walks everything and
times out. Deleting directories is one way to fix that, and it is the one that
loses work. Narrowing the walk is the other, it is reversible, and it can be
checked.

```bash
# how much is being walked today
rg --files | wc -l

# a scope file at the top of the workspace, next to the roots
cat > .ignore <<'SCOPE'
node_modules/
dist/
build/
.next/
.turbo/
*-wt-*/          # the worktrees you are not working in right now
SCOPE

# how much is walked after
rg --files | wc -l

# and the part that matters: the results you expect are still found
rg -n "createCheckoutSession" --stats
```

`rg` and `fd` both read `.ignore`, and most editors accept an equivalent
exclusion list, so one file narrows the three of them. Keep the pattern that
excludes worktrees narrow enough to name, and check a search you rely on before
and after. Nothing is removed, and the change is undone by deleting one file.

## The workspace the report runs on

`fixture/make_fixture.py` builds real small git repositories, with each
situation created for a reason named in `fixture/MANIFEST.md`. The counts come
from a description of a real workspace, and the convention chosen to turn that
description into a buildable one is stated there rather than implied: 131
candidate directories, of which 41 are not registered by any repository, an
illustrative hypothesis.

```bash
python3 fixture/make_fixture.py --out /tmp/demo-workspace --scale full
python3 build_demo.py            # regenerates report/demo-report.md
python3 -m unittest discover -s tests -t tests
```

## The controls

| Control | Where |
|---|---|
| git classification, and the decisions as the oracle | `tests/test_decisions.py` |
| work protection: untracked work, missing information, incomplete inspection | `tests/test_work_protection.py` |
| sensitivity, and a mutation that disables a preservation control | `tests/test_sensitivity_and_mutation.py` |
| bounded walk: budget, permissions, symlinks, depth | `tests/test_bounded_walk.py` |
| read only, no network, names not contents | `tests/test_readonly_and_privacy.py` |
| sessions and the rejection rate refusing to guess | `tests/test_sessions_and_hook_log.py` |
| the hook example, three decisions kept apart | `tests/test_hook_decision_split.py` |
| the published report is the one this commit produces | `tests/test_publication_and_manifest.py` |

The expected decisions live in `tests/expected_decisions.json`, written by
hand from the situations rather than recomputed from the classifier. Disabling
the preservation control has to break a case, and it does.

## Also here

- `CASE.md`: one operational incident, what changed after it, and where that
  stops applying.
- `HOOK.md`: keeping an authorization refusal, an operational limit and a
  controller error apart, against a named engine version.

MIT licensed.
