"""Control 1: git classification, and the decisions are the oracle.

The counts are a secondary control. What has to hold is that each situation
earns the decision a person would defend, for the reason that person would give.
"""

import os
import unittest

import support


class DecisionsOnTheFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = support.build_fixture("small")
        cls.report = support.collect(cls.fixture)
        cls.rows = support.by_name(cls.report)
        cls.expected = support.expected_decisions()

    def test_every_named_situation_earns_its_decision(self):
        for name, expectation in self.expected.items():
            if name.startswith("_"):
                continue
            with self.subTest(situation=name):
                self.assertIn(name, self.rows, f"the fixture no longer builds {name}")
                row = self.rows[name]
                self.assertEqual(
                    expectation["decision"], row["decision"],
                    f"{name}: {expectation['because']}",
                )
                if "evidence_contains" in expectation:
                    haystack = " ".join(row["evidence"] + row["preserved_because"])
                    self.assertIn(expectation["evidence_contains"], haystack)
                if "remaining_contains" in expectation:
                    self.assertIn(expectation["remaining_contains"], row["remaining_condition"])

    def test_an_independent_repository_is_never_a_removal_candidate(self):
        for row in self.report["decisions"]:
            if row["kind"] == "independent repository":
                self.assertEqual("keep", row["decision"], row["path"])

    def test_moved_and_locked_are_not_treated_as_abandoned(self):
        for name in ("web-console-wt-checkout-v2", "api-gateway-wt-on-external-volume"):
            row = self.rows[name]
            self.assertEqual("linked worktree", row["kind"])
            self.assertNotEqual("removal candidate, to confirm", row["decision"])

    def test_a_registration_without_a_directory_is_not_a_directory(self):
        absent = self.report["registered_entries_without_directory"]
        self.assertTrue(absent, "the fixture builds at least one registration with no directory")
        recorded = {row["recorded_path"] for row in absent}
        listed = set(self.rows)
        self.assertEqual(set(), recorded & listed,
                         "a registration with no directory must not appear as a directory to decide about")
        for row in absent:
            if row.get("explained_by"):
                self.assertIn(row["explained_by"], row["note"],
                              "a registration explained by a move names the directory it belongs to")
            else:
                self.assertIn("removes the registration", row["note"])

    def test_counts_match_the_composition_the_fixture_reports(self):
        composition = support.composition_of(self.fixture)
        counts = self.report["counts"]
        for key in ("candidate_directories", "linked_worktrees_in_scope", "independent_repositories",
                    "not_registered_by_any_repository", "worktree_metadata_unavailable",
                    "linked_worktrees_owner_outside_scope", "node_modules_trees"):
            with self.subTest(count=key):
                self.assertEqual(composition[key], counts[key])
        self.assertEqual(
            counts["candidate_directories"],
            counts["keep"] + counts["removal_candidates_to_confirm"] + counts["undetermined"],
        )

    def test_the_report_prints_no_cleanup_command(self):
        text = support.triage.markdown(self.report, None, None, False).lower()
        for forbidden in ("rm -rf", "git worktree remove", "git clean -", "find . -delete", "xargs rm"):
            self.assertNotIn(forbidden, text, f"the report must not carry {forbidden}")


if __name__ == "__main__":
    unittest.main()
