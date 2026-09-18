"""Control 6 and the rate: two inventories that refuse to guess.

The session inventory lists processes. It does not detect a blocked session,
and the tests hold it to that. The rejection rate is computed only when the log
carries a denominator, and the test with a log of refusals only asserts that
the answer is a refusal to compute.
"""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import support
import triage

# A process table written here, on purpose, so that nothing in this test can be
# mistaken for an observation made on a real machine.
SYNTHETIC_TABLE = """\
  501     1  04:11:02 ttys004  claude
  777     1  2-03:20:11 ??      codex
  912   777  00:00:31 ttys009  kiro
  333     1  01:02:03 ttys001  bash
"""


class Sessions(unittest.TestCase):
    def setUp(self):
        self.report = triage.inventory_sessions(
            datetime.fromisoformat(support.REFERENCE_TIME),
            table=SYNTHETIC_TABLE,
            cwd_lookup=lambda pid: f"/synthetic/workspace/{pid}",
        )

    def test_only_the_agent_processes_are_listed(self):
        self.assertEqual(["claude", "codex", "kiro"], [row["process"] for row in self.report["sessions"]])

    def test_progress_is_unknown_for_every_session(self):
        for row in self.report["sessions"]:
            self.assertEqual("unknown (no progress source)", row["progress"])

    def test_nothing_in_the_inventory_claims_a_session_is_blocked(self):
        rows = json.dumps(self.report["sessions"]).lower()
        for word in ("hung", "stuck", "stalled", "blocked", "dead", "idle"):
            self.assertNotIn(word, rows, f"no listed session may be called {word}")
        self.assertIn("never claims a session is hung", self.report["note"],
                      "the boundary is written next to the inventory, not left to the reader")

    def test_a_session_with_no_terminal_is_described_not_judged(self):
        without_terminal = [row for row in self.report["sessions"] if row["terminal"] == "none"]
        self.assertEqual(1, len(without_terminal))
        self.assertEqual("unknown (no progress source)", without_terminal[0]["progress"])


class HookRate(unittest.TestCase):
    def write_log(self, records) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for record in records:
            handle.write(json.dumps(record) + "\n")
        handle.close()
        return handle.name

    def test_a_log_of_refusals_only_cannot_produce_a_rate(self):
        path = self.write_log([
            {"reason": "size limit"},
            {"reason": "size limit"},
        ])
        result = triage.hook_rejection_rate(path)
        self.assertFalse(result["computable"])
        self.assertIn("not computable from this log", result["reason"])

    def test_a_log_with_a_denominator_produces_a_rate_and_keeps_retries_apart(self):
        path = self.write_log([
            {"ts": "2026-09-01T10:00:00Z", "outcome": "observed"},
            {"ts": "2026-09-01T10:01:00Z", "outcome": "observed"},
            {"ts": "2026-09-01T10:02:00Z", "outcome": "rejected", "reason": "size limit"},
            {"ts": "2026-09-01T10:03:00Z", "outcome": "rejected", "reason": "size limit", "retry_of": "3"},
        ])
        result = triage.hook_rejection_rate(path)
        self.assertTrue(result["computable"])
        self.assertEqual(4, result["examined"])
        self.assertEqual(2, result["rejected"])
        self.assertEqual(1, result["retries"])
        self.assertEqual(0.5, result["rate"])
        self.assertEqual({"size limit": 2}, result["reasons"])

    def test_a_log_that_cannot_be_read_says_so(self):
        result = triage.hook_rejection_rate("/nonexistent/hook.log")
        self.assertFalse(result["computable"])
        self.assertIn("could not be read", result["reason"])

    def test_the_report_says_no_rate_was_computed_when_no_log_was_given(self):
        fixture = support.build_fixture("small")
        text = triage.markdown(support.collect(fixture), None, None, False)
        self.assertIn("no hook log was given, so no rate is computed", text)


if __name__ == "__main__":
    unittest.main()
