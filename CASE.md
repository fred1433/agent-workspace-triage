# One incident, and what changed after it

A single case, told the way it happened. Not a method, not a set of rules to
adopt. The last section is the part that matters if you want to reuse any of
it: where it stops applying.

## What was observed

Several sessions run at once here, and some of their work goes through one
shared endpoint that only exists once on the machine. One morning two sessions
that needed it sat still for tens of minutes. Nothing was broken, nothing was
logged, and the work simply did not start.

## The mechanism

The launcher carried a guard: if another instance of the same work was already
running, do not start. It had been written weeks earlier, after two runs were
lost while two instances overlapped. Those two runs were never reproduced, and
the guard stayed.

Two things were wrong with it, and only the second one is interesting.

The first: the contention was not where the guard was. The shared endpoint is
only contended during a short interface phase, one to two minutes, while the
rest of a run is waiting. The guard covered the whole run.

The second: a session blocked by the guard produced no output at all. The cost
of the guard was invisible, so nobody could notice it was being paid every day.

## What was changed

The guard was replaced by three smaller things:

- a file lock taken only for the interface phase and released before the wait;
- a bounded wait on that lock, with its own exit status when the bound is
  reached, so that a session waiting on the lock says so in its log;
- a registry of the shared resource keyed by process id, from which only the
  entries whose process is gone are reclaimed, so a live session never has its
  resource taken by another one tidying up.

## What was actually observed afterwards

The same day, three runs went through the shared endpoint in parallel. One
started while another had been waiting for twelve minutes, and both finished.
The waiting time appeared in the log of the session that waited, which is the
part that had been missing.

This is a rule introduced after the incident, and one day of observation. It is
not a result measured over weeks.

## Where this stops applying

It applies when a shared resource is contended during a short, identifiable
phase of a longer run. When the bottleneck is the whole run, for example a
machine wide resource or a rate limit on something external, a short lock only
moves the collision and a queue is the honest answer.

The transferable part is smaller and duller than the mechanism: a guard written
from an incident that was never reproduced, whose cost nobody can see, gets
more expensive every week it survives. The two candidates for that description
here were a guard around a shared resource and a size limit in front of a
check. The first was measured and replaced. The second is the subject of
`HOOK.md`.
