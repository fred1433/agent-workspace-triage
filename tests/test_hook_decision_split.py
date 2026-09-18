"""The hook example: three decisions kept apart, tested offline.

Contract this is written against, read from the engine that is installed:
Claude Code 2.1.270, PreToolUse. Exit code 0 may carry
hookSpecificOutput.permissionDecision (allow, deny, ask). Emitting no decision
lets the normal permission flow continue, which is not the same as returning
allow. Nothing is claimed here for any other engine.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import support

HOOK = str(support.ROOT / "hooks" / "decision_split.sh")


def call(payload, log=None, extra_env=None) -> subprocess.CompletedProcess:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    environment = dict(os.environ)
    if log:
        environment["HOOK_LOG"] = log
    environment.update(extra_env or {})
    return subprocess.run([HOOK], input=body, env=environment, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)


def decision_of(result) -> str | None:
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


class ThreeDecisionsKeptApart(unittest.TestCase):
    def test_an_oversized_ordinary_call_degrades_the_advisory_check_and_grants_nothing(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "y" * 200000}})
        self.assertEqual(0, result.returncode)
        self.assertIsNone(decision_of(result),
                          "an operational limit must not turn into a permission decision")
        self.assertNotIn("permissionDecision", result.stdout)
        self.assertIn("No permission decision was emitted", result.stderr)

    def test_a_forbidden_write_stays_forbidden_at_the_same_size(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/secrets/key.pem", "content": "y" * 200000}})
        self.assertEqual("deny", decision_of(result),
                         "a degraded advisory check must not lift an authorization refusal")

    def test_a_forbidden_write_stays_forbidden_at_a_small_size(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "small"}})
        self.assertEqual("deny", decision_of(result))

    def test_an_ordinary_write_receives_no_decision(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "small"}})
        self.assertIsNone(decision_of(result))

    def test_a_target_that_cannot_be_read_is_refused_not_granted(self):
        beyond = {"tool_name": "Write", "tool_input": {"content": "y" * 200000, "file_path": "/repo/app.ts"}}
        result = call(beyond)
        self.assertEqual("deny", decision_of(result),
                         "when the target is past the bounded prefix, the write is refused, never granted")
        reason = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("could not be read", reason)

    def test_a_reading_tool_is_never_denied_by_this_hook(self):
        result = call({"tool_name": "Read", "tool_input": {"file_path": "/repo/.env"}})
        self.assertIsNone(decision_of(result))


class ControllerErrors(unittest.TestCase):
    def test_a_log_that_cannot_be_written_is_visible_and_changes_no_decision(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "x"}},
                      log="/nonexistent-directory/hook.log")
        self.assertEqual("deny", decision_of(result), "a failing log must not weaken an authorization refusal")
        self.assertIn("hook log could not be written", result.stderr,
                      "a controller error must be visible, never silent")

    def test_the_log_carries_a_denominator_the_collector_can_use(self):
        import triage
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "hook.jsonl")
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "ok"}}, log=log)
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "y" * 200000}}, log=log)
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "x"}}, log=log)
            rate = triage.hook_rejection_rate(log)
            self.assertTrue(rate["computable"])
            self.assertEqual(3, rate["examined"])
            self.assertEqual(1, rate["rejected"])


if __name__ == "__main__":
    unittest.main()
