# Three decisions a size limit should not be allowed to merge

A control that rejects a share of calls on a size limit is usually doing three
different things at once, and the trouble comes from the merge, not from the
limit.

1. **An authorization refusal.** This write is not allowed here. Nothing about
   the size of the call changes that.
2. **An operational limit.** The input is too large for an advisory check to
   run. The check degrades. It grants nothing.
3. **A controller error.** Something inside the control failed. That has to
   reach a person, and it must never turn into a permission.

`hooks/decision_split.py` is a small example that keeps the three apart, with
its tests in `tests/test_hook_decision_split.py`. It is an example on our side,
not a correction of a control we have not seen.

## The contract it is written against

Source: the Claude Code hooks reference, <https://code.claude.com/docs/en/hooks>,
consulted on **18 September 2026**. What it says about `PreToolUse`, in its own
words where the wording decides something:

- the call arrives as JSON on standard input, carrying `tool_name`,
  `tool_input` and `tool_use_id`, among other fields;
- **stderr is not a channel to a person on exit 0.** "Stderr from a hook that
  exits 0 goes to the debug log only, never the transcript, and Claude never
  sees it." To reach the person running the session, the page says to "return
  `systemMessage` in JSON output";
- exit code 2 blocks the call, "whether or not you print JSON";
- **any other exit code is decided by the JSON, not by the code.** "With a
  parsed object that passes schema validation ... Claude Code ignores the exit
  code and the JSON alone decides the outcome." Without valid JSON, exit code 1
  is a non blocking error and the action proceeds;
- `permissionDecision` is `allow`, `deny` or `abstain`, where `abstain` is
  documented as "No decision, continue to normal permission flow";
- **a timeout is not a gate.** A timed out command hook "doesn't block the tool
  call. The call continues through the normal permission flow, so don't count on
  a stalled hook to act as a gate." The default command timeout is 600 seconds.

Three consequences, which are why the example is shaped the way it is.

**Emitting no decision is not `allow`.** A hook that abstains lets the normal
permission flow continue, and that flow can still ask or refuse. Abstaining is
the correct output for a check that has nothing to say, and it is the wrong
output for a check that was supposed to refuse.

**A control that cannot run refuses.** Crashing, timing out and being
misconfigured all end with the call continuing through the normal permission
flow, and in a session that auto approves, continuing is granting. So the
example never treats its own failure as silence: an input it cannot decode, a
protected pattern it cannot compile, a tool name it cannot read, a target it
cannot read, all produce `deny` with the reason, and the person sees why.
The earlier version of this file claimed the authorization path never depended
on anything that can fail. That claim is withdrawn: simplifying a computation
does not establish it.

**The work stays small.** Since a hook that hangs is not a gate either, this
one decodes one JSON object, matches one regular expression and appends one
line. There is no network call and no subprocess in it.

## What the tests establish, and what they do not

The tests run `hooks/decision_split.py` as a program: they write the JSON of a
call to its standard input and read what it writes back. **That is a test of the
script.** Not one of them starts Claude Code, so none of them establishes how
the engine renders a `systemMessage`, honours `abstain`, or treats a timeout.
Those come from the reference above, quoted with the date it was read, and they
have not been exercised here. Nothing is claimed for Codex, for Kiro, or for
any other engine.

Tested cases:

| Case | Expected |
|---|---|
| Large call, ordinary path | `abstain`, advisory check recorded as degraded, normal flow continues |
| Large call, protected path | refusal, unchanged by the size |
| Small call, protected path | refusal |
| Small call, ordinary path | `abstain` |
| Protected path written as a JSON escape, `.env` | refusal, because the path is compared after decoding |
| `tool_name` arriving after a large field | refusal, because the whole call is decoded rather than a prefix |
| Input that is not JSON | refusal |
| Protected pattern that does not compile | refusal, and the reason reaches the person |
| Write with no readable target | refusal, because an authorization that cannot be checked is not granted |
| Log directory not writable | the refusal is unchanged, and the failure is reported in `systemMessage` |
| No log configured | said in `systemMessage`, rather than passing for a log with nothing in it |

The last three lines are the ones that decide whether the design holds. A
control is worth what it does on its bad day.

## The rate needs a denominator, and the log has to say so

"About one call in four" cannot be read from a log of refusals: refusals would
be both the numerator and the denominator. `triage.py --hook-log <file>`
therefore computes nothing at all unless three things are true of the log.

1. It opens with a **contract record** that declares every call the control
   examined is recorded there. A log that does not say it is complete is not
   treated as complete.
2. **Every line reads.** One malformed line and the answer is `not computable`:
   a log cannot be complete and partly unreadable at the same time.
3. **Every record carries a time and an attempt identifier**, so the period is
   known and two attempts are not one.

The example writes exactly that:

```json
{"record":"contract","complete":true,"scope":"every call this control examined is recorded here","control":"decision_split","version":1,"opened":"2026-09-18T09:12:40Z"}
{"record":"event","ts":"2026-09-18T09:12:44Z","outcome":"observed","reason":"advisory-degraded-oversize","bytes":200079,"advisory":"degraded","attempt":"toolu_01ABC"}
{"record":"event","ts":"2026-09-18T09:12:51Z","outcome":"rejected","reason":"protected-path","bytes":412,"advisory":"not-run","attempt":"toolu_01DEF"}
```

Two rates come out of it, and they answer different questions.

- **Per attempt**: refused attempts over attempts examined. A call refused and
  retried counts twice, which is the honest reading of what the control did.
- **Per initial call**: only when the records say which attempts belong to the
  same call, through a `call` field. The example cannot fill it in, because
  `tool_use_id` identifies an attempt and not the call it retries, so the
  collector answers `not identifiable from this log` rather than reusing the
  first number under a second name.

The advisory check in the example is a placeholder, and it is logged as
`not-implemented`, never as a check that ran and passed. Splitting the work into
smaller pieces is not proposed here as a finding: anyone living with such a
limit is already doing it.
