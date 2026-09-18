# Three decisions a size limit should not be allowed to merge

A control that rejects a share of calls on a size limit is usually doing three
different things at once, and the trouble comes from the merge, not from the
limit.

1. **An authorization refusal.** This write is not allowed here. Nothing about
   the size of the call changes that.
2. **An operational limit.** The input is too large for an advisory check to
   run. The check degrades. It grants nothing.
3. **A controller error.** Something inside the control failed. That has to be
   visible, and it must never turn into a permission.

`hooks/decision_split.sh` is a small example that keeps the three apart, with
its tests in `tests/test_hook_decision_split.py`. It is an example on our side,
not a correction of a control we have not seen.

## The contract it is written against

Claude Code 2.1.270, `PreToolUse`, whose documented behaviour is:

- the call arrives as JSON on standard input;
- exit code 0 may carry a JSON body, and `hookSpecificOutput.permissionDecision`
  is one of `allow`, `deny` or `ask`;
- exit code 2 shows standard error to the model and blocks the call;
- **any other exit code shows standard error to the user only and continues
  with the tool call.**

Two consequences worth stating before writing any control for this engine.

**Emitting no decision is not `allow`.** A hook that stays silent lets the
normal permission flow continue, and that flow can still ask or refuse.
Silence is the correct output for a check that has nothing to say, and it is
the wrong output for a check that was supposed to refuse.

**A control that crashes does not block anything.** Since any exit code outside
0 and 2 continues with the call, the refusal path cannot depend on the part of
the control that can fail. In the example, the authorization decision is taken
first, from a bounded prefix of the input, with two text extractions and no
parsing of the whole payload. The advisory check, which is the part that can be
slow or fail, runs afterwards and cannot lift a refusal.

Nothing is claimed here for any other engine.

## What the tests hold it to

Two contrasted cases, then the failure modes:

| Case | Expected |
|---|---|
| Large call, ordinary path | no decision emitted, advisory check recorded as degraded, normal flow continues |
| Large call, protected path | refusal, unchanged by the size |
| Small call, protected path | refusal |
| Small call, ordinary path | no decision |
| Target path beyond the bounded prefix | refusal, because an authorization that cannot be checked is not granted |
| Log directory not writable | the refusal is unchanged, and the failure is visible on standard error |

The fifth line is the one that decides whether the design holds. A call whose
content comes before its target path, and which is larger than the prefix, is
exactly the call an oversize rule tends to wave through.

## The rate needs a denominator

"About one call in four" cannot be read from a log of refusals. It needs the
calls examined over a period, the reasons kept apart, and retries counted as
retries rather than as new refusals. The example hook writes one record per
call, refused or not, which is what makes the rate computable at all:

```json
{"ts":"2026-09-18T09:12:44Z","outcome":"observed","reason":"advisory-degraded-oversize","bytes":200079,"advisory":"degraded"}
{"ts":"2026-09-18T09:12:51Z","outcome":"rejected","reason":"protected-path","bytes":412,"advisory":"not-run"}
```

`triage.py --hook-log <file>` computes the rate from records like these, and
says `rate: not computable from this log` when the denominator is missing,
which is the common case. Splitting the work into smaller pieces is not
proposed here as a finding: anyone living with such a limit is already doing it.
