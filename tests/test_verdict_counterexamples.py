"""The counter-examples a review ran against this code, kept as tests.

Every case below was first reproduced against the published version, where it
failed. They are here so that it stays failed on purpose: each one is a place
where the tool claimed more than it had checked, or read more than it said it
would. The names say which claim is at stake, not which reviewer found it.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import support
import triage

HOOK = str(support.ROOT / "hooks" / "decision_split.py")


def git_here(path, *args, **env):
    environment = dict(os.environ)
    environment.update({
        "GIT_AUTHOR_NAME": "Fixture Builder", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture Builder", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "LC_ALL": "C",
    })
    environment.update(env)
    done = subprocess.run(["git", *args], cwd=str(path), env=environment, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {path}: {done.stderr}")
    return done.stdout


def small_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git_here(path, "init", "-q", "-b", "main")
    git_here(path, "config", "user.name", "Fixture Builder")
    git_here(path, "config", "user.email", "fixture@example.invalid")
    git_here(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
    (path / "package.json").write_text('{"name":"x"}\n', encoding="utf-8")
    (path / ".gitignore").write_text("node_modules/\ndist/\n.env\n*.log\n", encoding="utf-8")
    git_here(path, "add", "-A")
    git_here(path, "commit", "-q", "-m", "initial")
    return path


def establish_default_branch(path: Path) -> None:
    """What a clone leaves behind: a remote tracking branch and origin/HEAD."""
    head = git_here(path, "rev-parse", "HEAD").strip()
    git_here(path, "update-ref", "refs/remotes/origin/main", head)
    git_here(path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


class KeepReasonsCarryTheirOwnCondition(unittest.TestCase):
    """Point 2: one sentence was injected into every preserved directory.

    "What this directory holds exists nowhere else" was written under a lock, a
    move and a recent commit alike. Nothing had checked that no copy existed.
    """

    @classmethod
    def setUpClass(cls):
        cls.report = support.collect(support.build_fixture("small"))
        cls.rows = support.by_name(cls.report)

    def test_no_preserved_directory_claims_its_content_exists_nowhere_else(self):
        for row in self.report["decisions"]:
            if row["decision"] == "keep":
                self.assertNotIn("exists nowhere else", row["remaining_condition"], row["path"])

    def test_the_ignored_file_case_says_what_was_not_checked(self):
        row = self.rows["worker-pipeline-wt-local-env"]
        evidence = " ".join(row["evidence"] + row["preserved_because"])
        self.assertIn("Ignored .env found. Its rebuildability and backup status were not checked.", evidence)
        self.assertEqual("Keep pending confirmation.", row["decision_sentence"])
        self.assertIn("Confirm how this file can be restored before reconsidering removal.",
                      row["remaining_condition"])

    def test_each_preservation_reason_carries_a_condition_of_its_own(self):
        locked = self.rows["api-gateway-wt-on-external-volume"]["remaining_condition"]
        moved = self.rows["web-console-wt-checkout-v2"]["remaining_condition"]
        untracked = self.rows["api-gateway-wt-oauth-refresh"]["remaining_condition"]
        self.assertIn("lock", locked.lower())
        self.assertIn("repair", moved.lower())
        self.assertIn("untracked", untracked.lower())
        self.assertEqual(3, len({locked, moved, untracked}),
                         "one universal phrase must not be replaced by another universal phrase")

    def test_a_removal_candidate_shows_the_negative_results_that_were_read(self):
        row = self.rows["api-gateway-wt-legacy-export"]
        self.assertEqual("removal candidate, to confirm", row["decision"])
        evidence = " ".join(row["evidence"]).lower()
        for expected in ("no modified tracked file", "no untracked file", "not locked",
                         "the recorded path matches the real path", "last commit"):
            with self.subTest(expected=expected):
                self.assertIn(expected, evidence)
        self.assertTrue(any("origin/" in line for line in row["evidence"]),
                        "the reference the branch was compared against belongs in the evidence")


class MissingInformationNeverProducesACandidate(unittest.TestCase):
    """Point 3: three ways a removal candidate was produced without the facts."""

    def test_a_failing_log_read_makes_the_inspection_incomplete(self):
        """Only `git log` fails. The date disappears and the line stayed complete."""
        fixture = support.build_fixture("small")
        original = triage.git

        def refusing(cwd, args, timeout=20.0, allow_exit=(0,)):
            if args and args[0] == "log":
                raise triage.CommandError("refused")
            return original(cwd, args, timeout, allow_exit)

        triage.git = refusing
        try:
            report = support.collect(fixture)
        finally:
            triage.git = original
        rows = support.by_name(report)
        row = rows["api-gateway-wt-legacy-export"]
        self.assertNotEqual("removal candidate, to confirm", row["decision"],
                            "a date that could not be read is missing information, not a passed check")
        self.assertNotEqual("complete", row["inspection"])

    def test_a_comparison_reference_that_was_never_established_is_missing_information(self):
        """No origin/HEAD. The owner simply had another branch checked out."""
        with tempfile.TemporaryDirectory(prefix="triage-ce-base-") as folder:
            root = Path(folder) / "root"
            owner = small_repo(root / "owner")
            git_here(owner, "checkout", "-q", "-b", "feature")
            (owner / "only-on-feature.txt").write_text("x\n", encoding="utf-8")
            git_here(owner, "add", "-A")
            git_here(owner, "commit", "-q", "-m", "a commit that lives only on feature")
            git_here(owner, "worktree", "add", "-q", "-b", "wt/task", str(root / "wt-task"), "main")

            report = triage.collect(roots=[str(root)], now=support.now(), stale_days=0, budget=60.0,
                                    max_depth=3, excludes=[], git_timeout=30.0, with_sizes=False)
            row = support.by_name(report)["wt-task"]
            self.assertNotEqual("removal candidate, to confirm", row["decision"],
                                "the branch a worktree is compared against has to be established, not picked up")
            text = json.dumps(row)
            self.assertNotIn("feature", text,
                             "the branch the owner happened to have checked out is not a comparison reference")

    def test_an_ignored_log_file_is_not_assumed_to_be_rebuildable(self):
        """An ignored incident.log can hold the only copy of a trace."""
        fixture = support.fresh_fixture("small")
        target = support.find(fixture, "api-gateway-wt-legacy-export")
        (target / "incident.log").write_text("the only copy of a trace\n", encoding="utf-8")
        row = support.by_name(support.collect(fixture))["api-gateway-wt-legacy-export"]
        self.assertEqual("keep", row["decision"],
                         "*.log was exempt by name, so a file that exists only here was waved through")

    def test_the_rebuildable_list_is_named_as_an_assumption(self):
        text = (support.ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("assumed", text)
        self.assertNotIn("*.log", triage.ASSUMED_REBUILDABLE)


class NothingIsReadOutsideTheNamedRoots(unittest.TestCase):
    """Point 4: owners were queried before the scope check, in pre-collection."""

    def test_no_command_runs_outside_the_roots_that_were_named(self):
        fixture = support.build_fixture("small")
        roots = [os.path.realpath(root) for root in support.roots_of(fixture)]
        triage.COMMAND_TRACE.clear()
        report = support.collect(fixture)
        outside = []
        for call in triage.COMMAND_TRACE:
            cwd = call.get("cwd")
            if cwd and not any(triage.is_within(cwd, root) for root in roots):
                outside.append([cwd, call["argv"][-3:]])
        self.assertEqual([], outside,
                         "a command ran in a repository the scan was not asked to look at")
        self.assertEqual("undetermined", support.by_name(report)["vendor-sdk-wt-patch-2"]["decision"])

    def test_the_boundary_is_stated_where_the_report_states_boundaries(self):
        report = support.collect(support.build_fixture("small"))
        self.assertIn("outside_scope", report["boundaries"])


class NoUncontrolledConversionIsRun(unittest.TestCase):
    """Point 5: a git clean filter is a command, and a status inspection runs it."""

    def build_workspace(self, folder: Path) -> tuple[Path, Path]:
        root = folder / "root"
        owner = small_repo(root / "owner")
        establish_default_branch(owner)
        witness = folder / "the-filter-ran"
        script = folder / "filter.sh"
        script.write_text(f'#!/bin/sh\n: > "{witness}"\ncat\n', encoding="utf-8")
        script.chmod(0o755)
        git_here(owner, "config", "filter.witness.clean", str(script))
        (owner / ".gitattributes").write_text("* filter=witness\n", encoding="utf-8")
        (owner / "tracked.txt").write_text("aaaa\n", encoding="utf-8")
        git_here(owner, "add", "-A")
        git_here(owner, "commit", "-q", "-m", "a repository that converts its content")
        git_here(owner, "worktree", "add", "-q", "-b", "wt/task", str(root / "wt-task"), "main")
        # A modification of the same length: what makes git read and convert.
        (root / "wt-task" / "tracked.txt").write_text("bbbb\n", encoding="utf-8")
        os.utime(root / "wt-task" / "tracked.txt", (time.time() + 2, time.time() + 2))
        if witness.exists():
            witness.unlink()
        return root, witness

    def test_the_collector_never_runs_the_filter_of_an_inspected_repository(self):
        with tempfile.TemporaryDirectory(prefix="triage-ce-filter-") as folder:
            root, witness = self.build_workspace(Path(folder))
            report = triage.collect(roots=[str(root)], now=support.now(), stale_days=30, budget=60.0,
                                    max_depth=3, excludes=[], git_timeout=30.0, with_sizes=False)
            self.assertFalse(witness.exists(),
                             "a configured filter ran during the inspection and wrote under the scanned root")
            row = support.by_name(report)["wt-task"]
            self.assertEqual("undetermined", row["decision"])
            self.assertIn("filter", row["remaining_condition"].lower())


class TheReportCarriesNamesAndNotFreeText(unittest.TestCase):
    """Point 5: the free text of a lock file came back out in the report."""

    def test_the_text_of_a_lock_file_never_reaches_the_report(self):
        with tempfile.TemporaryDirectory(prefix="triage-ce-lock-") as folder:
            root = Path(folder) / "root"
            owner = small_repo(root / "owner")
            establish_default_branch(owner)
            git_here(owner, "worktree", "add", "-q", "-b", "wt/task", str(root / "wt-task"), "main")
            git_here(owner, "worktree", "lock", "--reason",
                     "WITNESSSTRING-e7f1 kept on the drive of the person who left", str(root / "wt-task"))
            report = triage.collect(roots=[str(root)], now=support.now(), stale_days=30, budget=60.0,
                                    max_depth=3, excludes=[], git_timeout=30.0, with_sizes=False)
            text = json.dumps(report) + triage.markdown(report, None, None, False)
            self.assertNotIn("WITNESSSTRING", text, "free text from a file was reproduced in the report")
            self.assertIn("locked", text.lower(), "the fact of the lock is what the decision needs")

    def test_the_text_of_a_command_failure_never_reaches_the_report(self):
        fixture = support.build_fixture("small")
        original = triage.run_command

        def failing(argv, cwd=None, timeout=20.0, allow_exit=(0,)):
            if argv[0] == "git" and "status" in argv:
                raise triage.CommandError("fatal: WITNESSSTRING-4b21 in /somewhere/private/path")
            return original(argv, cwd=cwd, timeout=timeout, allow_exit=allow_exit)

        triage.run_command = failing
        try:
            report = support.collect(fixture)
        finally:
            triage.run_command = original
        text = json.dumps(report) + triage.markdown(report, None, None, False)
        self.assertNotIn("WITNESSSTRING", text, "the text of a failure was copied into the report")


class BoundsAreVisibleInTheReportAPersonReads(unittest.TestCase):
    """Point 6: a project below the depth limit vanished under `complete`."""

    def test_a_subtree_left_unopened_is_not_published_as_complete(self):
        fixture = support.fresh_fixture("small")
        root = Path(support.roots_of(fixture)[1])
        deep = root / "one" / "two" / "three" / "a-deep-project"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text("{}\n", encoding="utf-8")

        report = support.collect(fixture, max_depth=2)
        rows = {row["root"]: row for row in report["coverage"]}
        self.assertNotEqual("complete", rows[root.name]["coverage"],
                            "a root with unopened subtrees may not be reported as complete")
        text = triage.markdown(report, None, None, False)
        self.assertIn("depth limit", text.lower(),
                      "the limit that hid a directory belongs in the report, not only in the JSON")
        self.assertIn("not opened", text.lower())

    def test_the_budget_is_described_as_bounding_the_walk_and_not_the_run(self):
        text = triage.markdown(support.collect(support.build_fixture("small")), None, None, False).lower()
        self.assertIn("does not bound the whole run", text)


class TheHookKeepsItsRefusal(unittest.TestCase):
    """Point 8: three inputs that made the refusal disappear."""

    def call(self, payload, log=None, extra_env=None):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        environment = dict(os.environ)
        if log:
            environment["HOOK_LOG"] = log
        environment.update(extra_env or {})
        return subprocess.run([sys.executable, HOOK], input=body, env=environment, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

    def decision_of(self, result):
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_a_protected_path_written_with_a_json_escape_is_still_refused(self):
        body = '{"tool_name":"Write","tool_input":{"file_path":"/repo/\\u002eenv","content":"x"}}'
        self.assertEqual("deny", self.decision_of(self.call(body)),
                         "the path was compared before the JSON escape was decoded")

    def test_a_tool_name_after_a_large_prefix_is_still_read(self):
        payload = {"tool_input": {"content": "y" * 200000, "file_path": "/repo/secrets/key.pem"},
                   "tool_name": "Write"}
        self.assertEqual("deny", self.decision_of(self.call(payload)),
                         "the fields were read from a bounded prefix, so a large call lost its refusal")

    def test_an_invalid_configuration_refuses_rather_than_passing_silently(self):
        result = self.call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "x"}},
                           extra_env={"HOOK_PROTECTED_PATTERN": "(["})
        self.assertEqual("deny", self.decision_of(result),
                         "a control that cannot run must not let the call through")
        self.assertIn("could not", json.loads(result.stdout).get("systemMessage", "").lower())

    def test_an_input_that_is_not_valid_json_refuses(self):
        result = self.call("{not json at all")
        self.assertEqual("deny", self.decision_of(result))

    def test_the_absence_of_a_log_is_reported_rather_than_silent(self):
        result = self.call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "x"}})
        self.assertIn("no log", json.loads(result.stdout).get("systemMessage", "").lower())

    def test_the_advisory_check_is_labelled_for_what_it_is(self):
        with tempfile.TemporaryDirectory(prefix="triage-ce-hooklog-") as folder:
            log = os.path.join(folder, "hook.jsonl")
            self.call({"tool_name": "Write", "tool_input": {"file_path": "/repo/app.ts", "content": "x"}}, log=log)
            events = [json.loads(line) for line in Path(log).read_text(encoding="utf-8").splitlines() if line.strip()]
            advisory = [event.get("advisory") for event in events if event.get("record") == "event"]
            self.assertEqual(["not-implemented"], advisory,
                             "a placeholder that always passes must not be logged as a check that ran")


class TheRateRefusesAnUnprovenDenominator(unittest.TestCase):
    """Point 9: two refusals produced examined: 2, rejected: 2, rate: 1.0."""

    def write_log(self, lines) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        for line in lines:
            handle.write((line if isinstance(line, str) else json.dumps(line)) + "\n")
        handle.close()
        return handle.name

    def test_refusals_are_not_their_own_denominator(self):
        result = triage.hook_rejection_rate(self.write_log([
            {"outcome": "rejected", "reason": "size limit"},
            {"outcome": "rejected", "reason": "size limit"},
        ]))
        self.assertFalse(result["computable"])
        self.assertIn("not computable from this log", result["reason"])

    def test_a_malformed_line_is_not_ignored_under_a_claim_of_completeness(self):
        result = triage.hook_rejection_rate(self.write_log([
            {"record": "contract", "complete": True, "hook": "decision_split", "version": 1},
            {"record": "event", "ts": "2026-09-18T09:00:00Z", "outcome": "observed", "attempt": "a1"},
            "{ this line is broken",
        ]))
        self.assertFalse(result["computable"])
        self.assertIn("could not be read", result["reason"])

    def test_the_rate_is_per_attempt_and_the_per_call_rate_is_only_claimed_when_identifiable(self):
        path = self.write_log([
            {"record": "contract", "complete": True, "hook": "decision_split", "version": 1},
            {"record": "event", "ts": "2026-09-18T09:00:00Z", "outcome": "observed", "attempt": "a1"},
            {"record": "event", "ts": "2026-09-18T09:00:10Z", "outcome": "rejected", "attempt": "a2",
             "reason": "protected-path"},
        ])
        result = triage.hook_rejection_rate(path)
        self.assertTrue(result["computable"])
        self.assertEqual(0.5, result["attempt_rate"])
        self.assertIn("not identifiable", result["initial_call_rate"])


class SessionsAreCollectedAndRendered(unittest.TestCase):
    """Point 12: the working directory reader was never wired outside the tests."""

    def test_the_working_directory_of_a_real_process_is_read_in_normal_use(self):
        with tempfile.TemporaryDirectory(prefix="triage-ce-session-") as folder:
            target = os.path.realpath(folder)
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], cwd=target)
            try:
                table = f"  {child.pid}     1  00:00:05 ttys004  claude\n"
                original = triage.read_process_table
                triage.read_process_table = lambda: table
                try:
                    inventory = triage.inventory_sessions(support.now())
                finally:
                    triage.read_process_table = original
            finally:
                child.terminate()
                child.wait(timeout=10)
        if not inventory.get("available"):
            self.skipTest("no process table on this platform")
        row = inventory["sessions"][0]
        if row["working_directory"].startswith("not available"):
            self.skipTest("neither /proc nor lsof can report a working directory on this machine")
        self.assertEqual(target, os.path.realpath(row["working_directory"]))

    def test_an_unreadable_working_directory_is_said_to_be_unavailable(self):
        table = "  999999     1  00:00:05 ttys004  claude\n"
        original = triage.read_process_table
        triage.read_process_table = lambda: table
        try:
            inventory = triage.inventory_sessions(support.now())
        finally:
            triage.read_process_table = original
        self.assertTrue(inventory["sessions"][0]["working_directory"].startswith("not available"))

    def test_the_report_renders_the_session_lines_and_not_only_their_number(self):
        inventory = triage.inventory_sessions(
            support.now(),
            table="  501     1  04:11:02 ttys004  claude\n",
            cwd_lookup=lambda pid: "/synthetic/workspace",
        )
        text = triage.markdown(support.collect(support.build_fixture("small")), inventory, None, False)
        self.assertIn("501", text)
        self.assertIn("/synthetic/workspace", text)
        self.assertIn("04:11:02", text)


class ThePageAndTheReadmeSayWhatTheCodeDoes(unittest.TestCase):
    """Points 5, 11 and 13: sentences the code does not support."""

    def setUp(self):
        self.page = (support.ROOT / "site" / "index.html").read_text(encoding="utf-8")
        self.readme = (support.ROOT / "README.md").read_text(encoding="utf-8")

    def test_the_page_does_not_claim_the_collector_writes_nothing_at_all(self):
        self.assertNotIn("writes nothing at all", self.page)
        self.assertIn("triage.md", self.page, "the page names the file the command writes")

    def test_the_page_carries_the_convention_of_the_workspace_it_shows(self):
        self.assertIn("Fixture convention: 131 candidate directories, including 41 unregistered.", self.page)
        self.assertIn("Illustrative hypothesis, not a reconstruction.", self.page)
        self.assertIn("fixture/MANIFEST.md", self.page)

    def test_the_page_does_not_count_registrations_among_the_directories(self):
        match = re.search(r"The other 128 directories[^.]*\.", self.page)
        self.assertIsNotNone(match, "the page still describes the rest of the report")
        self.assertNotIn("registration", match.group(0),
                         "three registrations without a directory are not part of the 128 directories")

    def test_the_page_links_the_case_and_the_hook_and_the_commit_it_shows(self):
        self.assertIn("/blob/main/CASE.md", self.page)
        self.assertIn("/blob/main/HOOK.md", self.page)
        self.assertIn("/commit/", self.page)

    def test_the_readme_scope_file_does_not_hide_a_comment_on_a_pattern_line(self):
        block = self.readme.split("cat >", 1)[1].split("```", 1)[0]
        for line in block.splitlines():
            if "*-wt-*" in line:
                self.assertNotIn("#", line,
                                 "an ignore file reads a trailing # as part of the pattern, not as a comment")
        self.assertNotIn("cat > .ignore", self.readme,
                         "writing over an existing scope file is not a reversible change")


class TheMovedWorktreeRegistrationIsTiedToItsRepair(unittest.TestCase):
    """Point 11: the old path was listed as an absent entry with no context."""

    def test_the_old_path_of_a_moved_worktree_names_the_directory_it_belongs_to(self):
        report = support.collect(support.build_fixture("small"))
        absent = report["registered_entries_without_directory"]
        moved = [row for row in absent if "checkout" in row["recorded_path"]]
        self.assertTrue(moved, "the fixture still moves a worktree on disk")
        self.assertIn("web-console-wt-checkout-v2", json.dumps(moved),
                      "an absent registration that is the previous path of a moved worktree says so")


if __name__ == "__main__":
    unittest.main()
