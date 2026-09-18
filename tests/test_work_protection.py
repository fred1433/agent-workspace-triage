"""Control 2: work protection.

Untracked work, missing information or an inspection that did not finish must
all stop a directory from becoming a removal candidate. This is the control
that decides whether the tool can be trusted at all.
"""

import unittest

import support
import triage


class WorkProtection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = support.build_fixture("small")
        cls.report = support.collect(cls.fixture)
        cls.rows = support.by_name(cls.report)

    def test_untracked_work_is_never_a_removal_candidate(self):
        for row in self.report["decisions"]:
            has_untracked = any("untracked file" in reason for reason in row["preserved_because"])
            if has_untracked:
                self.assertEqual("keep", row["decision"], row["path"])

    def test_an_incomplete_inspection_is_undetermined_not_a_candidate(self):
        facts = {"kind": "linked worktree", "inspection_error": "git timed out after 20s"}
        decision, reasons, remaining = triage.decide(facts)
        self.assertEqual("undetermined", decision)
        self.assertEqual([], reasons)
        self.assertIn("inspection incomplete", remaining)

    def test_a_failing_git_makes_the_directory_undetermined(self):
        """With git refusing to answer, no directory may be proposed for removal."""
        original = triage.git

        def refusing(cwd, args, timeout=20.0):
            if args and args[0] in ("status", "rev-parse", "rev-list", "log"):
                raise triage.CommandError("git refused to describe this repository")
            return original(cwd, args, timeout)

        triage.git = refusing
        try:
            report = support.collect(self.fixture)
        finally:
            triage.git = original
        self.assertEqual(0, report["counts"]["removal_candidates_to_confirm"],
                         "an inspection that cannot run must not produce removal candidates")
        self.assertGreater(report["counts"]["undetermined"], 0)

    def test_missing_information_is_undetermined_with_the_next_check_named(self):
        for name in ("vendor-sdk-wt-patch-2",
                     "worker-pipeline-wt-retry-policy",
                     "web-console-copy-2"):
            row = self.rows[name]
            self.assertEqual("undetermined", row["decision"])
            self.assertGreater(len(row["remaining_condition"]), 40,
                               "an undetermined line without a next check is a shrug, not work")

    def test_ignored_files_a_build_regenerates_are_not_a_reason_to_preserve(self):
        kept = triage.classify_ignored(["node_modules/", "dist/", ".env", "local.sqlite"])
        self.assertEqual([".env", "local.sqlite"], kept)


if __name__ == "__main__":
    unittest.main()
