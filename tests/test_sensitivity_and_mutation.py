"""Control 3: the decisions move for the right reason, and the checks bite.

A test suite that only counts can pass while the logic protects the wrong
object. So: adding one reason to preserve must change one status and leave the
totals alone, and disabling a preservation control must break the case that
depends on it. If the mutation does not break anything, the control was
decoration.
"""

import unittest
from pathlib import Path

import support
import triage


class Sensitivity(unittest.TestCase):
    def test_one_added_reason_changes_one_status_and_no_count(self):
        fixture = support.fresh_fixture("small")
        before = support.collect(fixture)
        target = support.by_name(before)["api-gateway-wt-legacy-export"]
        self.assertEqual("removal candidate, to confirm", target["decision"])

        path = support.find(fixture, "api-gateway-wt-legacy-export") / ".env"
        path.write_text("DATABASE_URL=postgres://localhost/only-here\n", encoding="utf-8")

        after = support.collect(fixture)
        moved = support.by_name(after)["api-gateway-wt-legacy-export"]
        self.assertEqual("keep", moved["decision"])
        self.assertIn("does not regenerate", " ".join(moved["preserved_because"]))
        self.assertEqual(before["counts"]["candidate_directories"], after["counts"]["candidate_directories"],
                         "the number of directories did not change, only one decision did")
        self.assertEqual(before["counts"]["keep"] + 1, after["counts"]["keep"])


class Mutation(unittest.TestCase):
    def test_disabling_the_preservation_control_breaks_the_expected_case(self):
        """The strong mutation: with preservation disabled, work stops being protected."""
        fixture = support.build_fixture("small")
        healthy = support.by_name(support.collect(fixture))["api-gateway-wt-oauth-refresh"]
        self.assertEqual("keep", healthy["decision"])

        original = triage.preservation_reasons
        triage.preservation_reasons = lambda facts: []
        try:
            mutated = support.by_name(support.collect(fixture))["api-gateway-wt-oauth-refresh"]
        finally:
            triage.preservation_reasons = original

        self.assertNotEqual(
            "keep", mutated["decision"],
            "with the preservation control disabled, a directory holding untracked work must stop being a keep; "
            "if it stays a keep, the expected result was not produced by that control",
        )
        self.assertEqual("removal candidate, to confirm", mutated["decision"])

    def test_the_count_check_detects_one_extra_directory(self):
        """The weaker mutation, kept because it catches discovery regressions."""
        fixture = support.fresh_fixture("small")
        composition = support.composition_of(fixture)
        extra = Path(support.roots_of(fixture)[0]) / "an-extra-leftover"
        (extra / "src").mkdir(parents=True)
        (extra / "package.json").write_text('{"name": "extra"}\n', encoding="utf-8")

        counts = support.collect(fixture)["counts"]
        self.assertNotEqual(composition["candidate_directories"], counts["candidate_directories"])
        self.assertEqual(composition["candidate_directories"] + 1, counts["candidate_directories"])


if __name__ == "__main__":
    unittest.main()
