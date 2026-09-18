"""The hook example: three decisions kept apart, tested offline.

What these tests establish, and what they do not. They run `hooks/decision_split.py`
as a program, feed it the JSON of a tool call and read what it writes. That is a
test of the script. None of them runs Claude Code, so none of them establishes
how the engine treats the output: the contract this script is written against
is quoted from the hooks reference, with the date it was read, in HOOK.md.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import support

HOOK = str(support.ROOT / "hooks" / "decision_split.py")


def call(payload, log=None, extra_env=None) -> subprocess.CompletedProcess:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    environment = dict(os.environ)
    environment.pop("HOOK_LOG", None)
    if log:
        environment["HOOK_LOG"] = log
    environment.update(extra_env or {})
    return subprocess.run([sys.executable, HOOK], input=body, env=environment, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)


def answer(result) -> dict:
    return json.loads(result.stdout)


def decision_of(result) -> str:
    return answer(result)["hookSpecificOutput"]["permissionDecision"]


class ThreeDecisionsKeptApart(unittest.TestCase):
    def test_an_oversized_ordinary_call_degrades_the_advisory_check_and_grants_nothing(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "y" * 200000}})
        self.assertEqual(0, result.returncode)
        self.assertEqual("abstain", decision_of(result),
                         "an operational limit must not turn into a permission decision")
        self.assertIn("No permission decision was emitted", answer(result)["systemMessage"])

    def test_a_forbidden_write_stays_forbidden_at_the_same_size(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/secrets/key.pem",
                                                            "content": "y" * 200000}})
        self.assertEqual("deny", decision_of(result),
                         "a degraded advisory check must not lift an authorization refusal")

    def test_a_forbidden_write_stays_forbidden_at_a_small_size(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "small"}})
        self.assertEqual("deny", decision_of(result))

    def test_an_ordinary_write_receives_no_decision(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "small"}})
        self.assertEqual("abstain", decision_of(result),
                         "abstain is the documented spelling of no decision, and it is not allow")

    def test_a_write_whose_target_cannot_be_read_is_refused_not_granted(self):
        result = call({"tool_name": "Write", "tool_input": {"content": "y" * 200000}})
        self.assertEqual("deny", decision_of(result),
                         "when no target can be read, the write is refused, never granted")
        self.assertIn("could not be read", answer(result)["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_reading_tool_is_never_denied_by_this_hook(self):
        result = call({"tool_name": "Read", "tool_input": {"file_path": "/repo/.env"}})
        self.assertEqual("abstain", decision_of(result))

    def test_the_protected_pattern_can_be_replaced(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/infra/live/main.tf", "content": "x"}},
                      extra_env={"HOOK_PROTECTED_PATTERN": "(^|/)infra/live/"})
        self.assertEqual("deny", decision_of(result))


class ControllerErrors(unittest.TestCase):
    def test_a_log_that_cannot_be_written_is_visible_and_changes_no_decision(self):
        result = call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "x"}},
                      log="/nonexistent-directory/hook.log")
        self.assertEqual("deny", decision_of(result), "a failing log must not weaken an authorization refusal")
        self.assertIn("could not be written", answer(result)["systemMessage"],
                      "a controller error must reach the person, and stderr does not on exit 0")

    def test_the_log_carries_what_a_rate_needs(self):
        import triage
        with tempfile.TemporaryDirectory() as folder:
            log = os.path.join(folder, "hook.jsonl")
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "ok"}}, log=log)
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "y" * 200000}}, log=log)
            call({"tool_name": "Write", "tool_input": {"file_path": "/repo/.env", "content": "x"}}, log=log)
            records = [json.loads(line) for line in Path(log).read_text(encoding="utf-8").splitlines()]
            self.assertEqual("contract", records[0]["record"], "the log opens by declaring what it holds")
            rate = triage.hook_rejection_rate(log)
            self.assertTrue(rate["computable"], rate.get("reason"))
            self.assertEqual(3, rate["attempts_examined"])
            self.assertEqual(1, rate["attempts_rejected"])
            self.assertIn("not identifiable", rate["initial_call_rate"],
                          "this log identifies attempts, not the call an attempt retries")


if __name__ == "__main__":
    unittest.main()
