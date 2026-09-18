# One incident, and what changed after it

A single case, told the way it happened. Not a method, not a set of rules to
adopt. The last section is the part that matters if you want to reuse any of
it: where it stops applying.

## What was observed

Several sessions run at once here, and some of their work goes through one
shared browser that only exists once on the machine. One morning two sessions
that needed it sat still for tens of minutes. Nothing was broken, nothing was
logged, and the work simply did not start.

## The mechanism

The launcher carried a `pgrep` guard: if another instance of the same work was
already running, do not start. It had been written weeks earlier, after two
runs were lost while two instances overlapped. Those two runs were never
reproduced, and the guard stayed.

Two issues were identified.

The first: the contention was not where the guard was. The shared browser is
only contended during a short interface phase, one to two minutes, while the
rest of a run is waiting. The `pgrep` guard covered the whole run.

The second: a session blocked by the guard produced no output at all. The cost
of the guard was invisible, so nobody could notice it was being paid every day.

## What was changed

The guard was replaced by three smaller things:

- a file lock taken only for the interface phase and released before the wait;
- a bounded wait on that lock, with its own exit status when the bound is
  reached, so that a session waiting on the lock says so in its log;
- a registry of the shared browser keyed by process id, from which only the
  entries whose process is gone are reclaimed, so a live session never has its
  tab taken by another one tidying up.

## What was actually observed afterwards

The same day, three runs went through the shared browser in parallel. One
started while another had been waiting for twelve minutes, and both finished.
The waiting time appeared in the log of the session that waited, which is the
part that had been missing.

This is a rule introduced after the incident, and one day of observation. It is
not a result measured over weeks.

## Where this stops applying

This incident involved a shared browser, contended only during the interface
phase. The observation covers that day only. It does not establish a solution
for a bottleneck that lasts for the whole run.
