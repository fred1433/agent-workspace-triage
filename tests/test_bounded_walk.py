"""Control 4: a walk that does not finish says so.

The symptom that starts this whole exercise is a search that walks everything
and times out. A tool that answers that symptom has to be able to stop early,
and an early stop must never be published as a clean result.
"""

import os
import stat
import unittest

import support


class BoundedWalk(unittest.TestCase):
    def test_an_exhausted_budget_is_partial_coverage_never_a_clean_result(self):
        fixture = support.build_fixture("small")
        report = support.collect(fixture, budget=0.0)
        partial = [root for root in report["coverage"] if root["coverage"] == "partial"]
        self.assertTrue(partial, "a budget of zero must produce partial coverage")
        for root in partial:
            self.assertIn("budget", root["reason"])
        self.assertLess(report["counts"]["candidate_directories"],
                        support.collect(fixture)["counts"]["candidate_directories"])

    def test_a_root_that_cannot_be_read_is_an_error_not_an_absence(self):
        fixture = support.fresh_fixture("small")
        root = support.first_root(fixture)
        closed = fixture / "workspace" / root / "closed-to-us"
        closed.mkdir()
        (closed / "package.json").write_text("{}\n", encoding="utf-8")
        os.chmod(closed, 0o000)
        try:
            report = support.collect(fixture, max_depth=4)
            readable = os.access(closed, os.R_OK)
        finally:
            os.chmod(closed, stat.S_IRWXU)
        if readable:
            self.skipTest("this account can read a directory with no permissions, so there is nothing to observe")
        roots = {root["root"]: root for root in report["coverage"]}
        self.assertEqual("partial", roots[root]["coverage"])
        self.assertTrue(any("permission denied" in error for error in roots[root]["errors"]))

    def test_symlinks_are_counted_and_not_followed(self):
        fixture = support.fresh_fixture("small")
        root = support.first_root(fixture)
        link = fixture / "workspace" / root / "a-link-back-to-the-root"
        os.symlink(fixture / "workspace" / root, link)
        report = support.collect(fixture)
        roots = {root["root"]: root for root in report["coverage"]}
        self.assertGreaterEqual(roots[root]["symlinks_not_followed"], 1)
        self.assertNotEqual("partial", roots[root]["coverage"],
                            "not following a symlink is a decision, not a failure")
        self.assertIn("symlink", roots[root]["reason"],
                      "a decision that leaves something unopened is named, not implied by silence")

    def test_the_depth_limit_is_visible_and_can_be_raised(self):
        fixture = support.fresh_fixture("small")
        root = os.path.basename(support.roots_of(fixture)[1])
        deep = fixture / "workspace" / root / "one" / "two" / "three" / "a-deep-project"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text("{}\n", encoding="utf-8")

        shallow = support.collect(fixture, max_depth=2)
        self.assertNotIn("a-deep-project", support.by_name(shallow))
        roots = {root["root"]: root for root in shallow["coverage"]}
        self.assertGreaterEqual(roots[root]["depth_limit_reached"], 1,
                                "a directory left unopened because of the depth limit is reported")
        self.assertEqual("bounded", roots[root]["coverage"],
                         "a root with a subtree left unopened is not complete")

        deeper = support.collect(fixture, max_depth=6)
        self.assertIn("a-deep-project", support.by_name(deeper))


if __name__ == "__main__":
    unittest.main()
