"""Publication traceability: the page carries the report this commit produces.

A green badge next to a report copied by hand proves nothing. These two tests
close that gap: the committed report is rebuilt from the code and compared byte
for byte, and the manifest is compared with the workspace the builder produces.
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

import support

REPORT = support.ROOT / "report" / "demo-report.md"
PAGE = support.ROOT / "site" / "index.html"


class Publication(unittest.TestCase):
    def test_the_committed_report_and_page_are_what_this_commit_produces(self):
        done = subprocess.run(
            [sys.executable, str(support.ROOT / "build_demo.py"), "--check"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900,
        )
        self.assertEqual(0, done.returncode, done.stderr or done.stdout)

    def test_the_report_names_its_collector_and_its_reference_time(self):
        text = REPORT.read_text(encoding="utf-8")
        self.assertIn("agent-workspace-triage", text)
        self.assertIn("Reference time", text)
        self.assertIn("read only", text)

    def test_the_report_carries_no_cleanup_command(self):
        text = REPORT.read_text(encoding="utf-8").lower()
        for forbidden in ("rm -rf", "git worktree remove", "git clean -", "xargs rm"):
            self.assertNotIn(forbidden, text)


class Manifest(unittest.TestCase):
    def test_the_manifest_numbers_are_the_ones_the_builder_produces(self):
        text = (support.ROOT / "fixture" / "MANIFEST.md").read_text(encoding="utf-8")
        block = text.split("<!-- composition:start -->", 1)[1].split("<!-- composition:end -->", 1)[0]
        declared = {}
        for line in block.splitlines():
            match = re.match(r"^\s*([a-z_]+):\s*(\d+)\s*$", line)
            if match:
                declared[match.group(1)] = int(match.group(2))
        self.assertTrue(declared, "the manifest carries no composition block")

        import json
        built = json.loads((support.ROOT / "report" / "fixture-composition.json").read_text(encoding="utf-8"))
        for key, value in declared.items():
            with self.subTest(key=key):
                self.assertEqual(value, built[key], f"the manifest says {key} is {value}")

    def test_the_manifest_states_the_convention_rather_than_claiming_a_reproduction(self):
        text = (support.ROOT / "fixture" / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn("illustrative hypothesis", text)
        self.assertIn("not a reproduction", text)


if __name__ == "__main__":
    unittest.main()
