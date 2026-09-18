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

That command reads your roots and writes one file, `triage.md`, where you asked
for it. It writes nothing else, anywhere.

The report published at <https://workspace-triage.theaipipe.com> is the output
of this collector on the synthetic workspace built by `fixture/make_fixture.py`,
regenerated and compared byte for byte on every commit.

## What it decides, and how

Every directory that looks like a working tree gets one of three statuses, and
the scope of each one is explicit.

| Status | What it means |
|---|---|
| **Keep** | a positive reason to preserve was found: untracked work, uncommitted changes, commits the reference branch does not contain, an ignored entry outside the assumed rebuildable list, a lock, a move that git repairs, or recent activity |
| **Removal candidate, to confirm** | the checks in scope were read and came back empty, they are listed as evidence, and the confirmations that are left are named |
| **Undetermined** | something is missing, with the next check named |

Missing information and an inspection that did not finish both produce
**undetermined**, never a removal candidate. That rule is what the tests spend
most of their time on.

Each line carries the same four parts: what was observed, the evidence, the
decision, the condition that is still open. Every reason to preserve carries a
condition of its own: a lock is confirmed by finding out why it was taken,
untracked work by finding out where else it lives. Nothing here establishes
that the content of a directory exists nowhere else, so nothing here says so.

## What git is actually asked

A directory that is not registered is not the same thing as a directory that
can go. The collector separates:

- a repository with its own history, which answers to nobody else;
- a valid linked worktree of a repository inside the roots you named;
- a worktree attached to a repository outside those roots, which is a question, not a finding;
- a worktree whose metadata directory is gone;
- a worktree that was moved, which `git worktree repair` fixes;
- a worktree that is locked, usually because its storage is not always there;
- a registration that names a directory which is not on disk, which is metadata: pruning it removes the registration and removes no directory, and when that registration is the previous path of a worktree that moved, the report says which one;
- a directory that looks like a working tree and that no repository claims.

## The two assumptions it makes, named as assumptions

**A branch is only compared against a reference that was established.** That
means `refs/remotes/origin/HEAD`, which a clone writes and `git remote set-head`
sets, or a reference you name with `--compare-with`. The branch a repository
happens to have checked out this morning is not that: comparing against it
produces removal candidates that mean nothing. A repository with no established
reference is reported as undetermined, with that as the next check.

**Some ignored entries are assumed to be build output.** `node_modules`, `dist`,
`.next` and the rest of a short list in `triage.py` are assumed to be written
again by a build, so they are not a reason to preserve anything. That assumption
is never verified: nothing here inspects a build. Anything else that is ignored
is treated as possibly the only copy of something, and the line says what was
not checked: *"Ignored .env found. Its rebuildability and backup status were not
checked."* `*.log` is deliberately not on the list, because an ignored log can
hold the only trace of an incident.

## Boundaries, and how each one is tested

- **No external call.** The collector imports no network module, and runs only
  `git`, `ps` and `lsof` from a fixed allow list. Two controls: a static reading
  of the source that fails on a network import, and a run of the whole
  collection inside a network namespace with nothing in it, in continuous
  integration, where the collection still produces its report. That namespace is
  created with `unshare -rn` where an unprivileged one is allowed and with
  `sudo -n unshare -n` where it is not, and a skip fails the run. A
  third test runs it behind a listener that counts connections and sees none;
  that one only covers what a proxy variable would catch, and the listener is
  exercised in the same test so that the zero means something.
- **Read only for real.** Read only is not the absence of a remove command: a
  plain `git status` can refresh and write the index, which is why every call
  carries `--no-optional-locks`. A test fingerprints every file, directory,
  index, reference and configuration under the roots, runs the collector, and
  compares.
- **Other people's commands are not run.** A git filter is a command, and git
  starts it while answering an ordinary question about a file. A repository that
  configures one is therefore left uninspected and reported as undetermined,
  rather than have git run a conversion on our behalf. The test builds a
  repository whose filter writes a witness file, and the witness never appears.
  What is read to find out: the attribute files git would use, which are the
  tracked ones, the one at the root of the working tree whether tracked or not,
  the per repository file and the per user file. An untracked attributes file
  sitting in a subdirectory is not read, so a filter assigned only from there
  would not be seen.
- **Nothing outside the roots you name.** The scope check comes before any
  question: a repository outside the roots is not asked for its default branch
  either. A test records the directory of every command that ran and fails if
  one of them is outside.
- **No cleanup command.** The report names the condition that is left, never a
  command to paste. A status is a proposal with its evidence.
- **Names, not contents.** File names appear in the report. File contents do
  not, and neither do absolute paths of the machine that ran it, the free text
  somebody wrote in a lock file, or the text a failing command printed.
- **A walk that stops early says so, and so does a walk that stops on purpose.**
  Coverage has three states: `complete` when nothing was left unopened,
  `bounded` when the walk finished inside its limits and the report counts what
  those limits left unopened, `partial` when it stopped for a reason it did not
  choose. Partial coverage is never published as a clean result.

## What it does not do

- It does not detect a hung session. `--sessions` lists the agent processes
  that exist, with their age, terminal and working directory, and reports
  progress as `unknown (no progress source)`. The working directory is read
  from `/proc/<pid>/cwd` where that exists and from `lsof -a -p <pid> -d cwd`
  otherwise, and when neither answers the line says the directory is not
  available rather than leaving a blank. A process name and an age describe a
  process, not the progress of the work it was given. Detecting a suspected
  block needs a progress event or a declared wait, a session identity, and a
  documented threshold.
- It does not compute a rejection rate out of a log of refusals. With
  `--hook-log` it computes one only when the log declares that it records every
  call examined, every line reads, and every record carries a time and an
  attempt identifier. Otherwise it says `rate: not computable from this log`.
  See `HOOK.md`.
- It does not weigh `node_modules` unless you ask with `--sizes`, because
  weighing walks every file, and that walk is the one that times out.
- It does not bound the whole run with one number. `--budget-seconds` bounds the
  discovery walk of one root; every git call has `--git-timeout`; and the
  `node_modules` count of each candidate directory receives the budget again.

## Narrowing a search without removing anything

The symptom that usually starts this is a search that walks everything and
times out. Deleting directories is one way to fix that, and it is the one that
loses work. Narrowing the walk is the other, it is reversible, and it can be
checked.

```bash
# how much is being walked today
rg --files | wc -l

# add a scope file at the top of the workspace, next to the roots.
# append, never overwrite: an .ignore may already be there, and a comment
# only counts on a line of its own, never after a pattern.
cat >> .ignore <<'SCOPE'
node_modules/
dist/
build/
.next/
.turbo/
# the worktrees you are not working in right now
*-wt-*/
SCOPE

# how much is walked after
rg --files | wc -l

# and the part that matters: the results you expect are still found
rg -n "createCheckoutSession" --stats
```

`rg` and `fd` both read `.ignore`, and most editors accept an equivalent
exclusion list, so one file narrows the three of them. Keep the pattern that
excludes worktrees narrow enough to name, and check a search you rely on before
and after. Nothing is removed, and the change is undone by deleting the lines
you added.

## The workspace the report runs on

`fixture/make_fixture.py` builds real small git repositories, with each
situation created for a reason named in `fixture/MANIFEST.md`. The counts come
from a description of a real workspace, and the convention chosen to turn that
description into a buildable one is stated there rather than implied: 131
candidate directories, of which 41 are not registered by any repository, an
illustrative hypothesis and not a reconstruction.

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
| the counter-examples a review ran against this code | `tests/test_verdict_counterexamples.py` |

The expected decisions live in `tests/expected_decisions.json`, written by
hand from the situations rather than recomputed from the classifier. Disabling
the preservation control has to break a case, and it does.

`tests/test_verdict_counterexamples.py` is the file worth reading first. Each
test there is a case where this code claimed more than it had checked, or read
more than it said it would: a filter that ran under a read only promise, a
comparison branch nobody established, an ignored log waved through, a lock
reason copied into the report, a hook that lost its refusal when a path arrived
JSON escaped. They were reproduced before they were fixed.

## Also here

- `CASE.md`: one operational incident, what changed after it, and where that
  stops applying.
- `HOOK.md`: keeping an authorization refusal, an operational limit and a
  controller error apart, against a dated reference.

MIT licensed.
