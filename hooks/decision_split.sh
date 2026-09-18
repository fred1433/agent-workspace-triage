#!/usr/bin/env bash
# decision_split.sh: a PreToolUse hook that keeps three decisions apart.
#
#   1. Authorization. A forbidden write stays forbidden. This decision is taken
#      first, on a bounded prefix of the input, and it never depends on the part
#      that can fail.
#   2. Operational limit. An input too large for the advisory check degrades
#      that check and says so. It emits no decision, which lets the normal
#      permission flow continue. Emitting no decision is not "allow".
#   3. Controller error. Anything that goes wrong inside the hook is visible on
#      stderr and in the log. It is never silent, and it never turns into a
#      permission.
#
# Engine and version this was written and tested against: Claude Code 2.1.270,
# PreToolUse, whose documented contract is: input is the JSON of the tool call
# on stdin; exit code 0 with a JSON body may carry
# hookSpecificOutput.permissionDecision, one of allow, deny or ask; exit code 2
# shows stderr to the model and blocks the call; any other exit code shows
# stderr to the user only AND CONTINUES WITH THE TOOL CALL. That last line is
# the reason the authorization decision is computed first and simply: a hook
# that crashes does not block anything.
#
# Nothing is claimed here for any other engine.
#
# Configuration, all optional:
#   HOOK_PROTECTED_PATTERN  extended regex of paths that may not be written
#   HOOK_ADVISORY_MAX_BYTES size above which the advisory check degrades
#   HOOK_LOG                where to append one JSON record per call

set -u

PROTECTED_PATTERN="${HOOK_PROTECTED_PATTERN:-(^|/)(\.env|\.git/|secrets/|infra/production/)}"
ADVISORY_MAX_BYTES="${HOOK_ADVISORY_MAX_BYTES:-65536}"
LOG="${HOOK_LOG:-}"
WRITING_TOOLS="Write|Edit|NotebookEdit|MultiEdit"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# The log is best effort. When it fails, the failure is visible, and it changes
# no decision.
record() { # outcome reason bytes advisory
  local line
  line=$(printf '{"ts":"%s","outcome":"%s","reason":"%s","bytes":%s,"advisory":"%s"}' \
    "$(now)" "$1" "$2" "$3" "$4")
  if [ -n "$LOG" ]; then
    if ! printf '%s\n' "$line" >>"$LOG" 2>/dev/null; then
      printf 'decision_split: the hook log could not be written (%s). The decision below was taken anyway.\n' \
        "$LOG" >&2
    fi
  fi
}

# The call is read as a stream: a bounded prefix first, then the rest is only
# counted. Nothing is written to disk, so there is no temporary file to remove
# and no cleanup that can fail.
prefix=$(head -c 65536)
rest=$(wc -c | tr -d " ")
prefix_bytes=$(printf '%s' "$prefix" | wc -c | tr -d " ")
size=$((prefix_bytes + rest))

# 1. Authorization, on that bounded prefix, with no dependency on the rest.
tool=$(printf '%s' "$prefix" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
target=$(printf '%s' "$prefix" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
if [ -z "$target" ]; then
  target=$(printf '%s' "$prefix" | sed -n 's/.*"notebook_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
fi

deny() {
  record "rejected" "$1" "$size" "$2"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$3"
  exit 0
}

if printf '%s' "$tool" | grep -Eq "^($WRITING_TOOLS)$"; then
  if [ -z "$target" ]; then
    # The target could not be read. Authorization is never granted by a failure
    # to check it.
    deny "target-unreadable" "not-run" \
      "the target path could not be read from the first 64 kB of the call, so this write cannot be authorized"
  fi
  if printf '%s' "$target" | grep -Eq "$PROTECTED_PATTERN"; then
    deny "protected-path" "not-run" \
      "this path is protected by policy, and that does not change with the size of the call"
  fi
fi

# 2. Operational limit. Above the threshold the advisory check degrades. No
# decision is emitted, so the normal permission flow continues. This is not an
# authorization, and it grants nothing.
if [ "$size" -gt "$ADVISORY_MAX_BYTES" ]; then
  record "observed" "advisory-degraded-oversize" "$size" "degraded"
  printf 'decision_split: advisory check skipped, the call is %s bytes, above the advisory limit of %s. No permission decision was emitted; the normal permission flow applies.\n' \
    "$size" "$ADVISORY_MAX_BYTES" >&2
  exit 0
fi

# The advisory check itself. It is consultative: it reports, it does not
# authorize. Here it is a placeholder that always passes.
record "observed" "advisory-passed" "$size" "run"
exit 0
