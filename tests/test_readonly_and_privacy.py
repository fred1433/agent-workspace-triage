"""Control 5: read only, and nothing leaves the machine.

Read only is not the absence of a remove command. A plain `git status` can
refresh and write the index, which is why every call here carries
--no-optional-locks. The test below fingerprints everything the collector
touches, runs it, and fingerprints again.
"""

import ast
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import sys
import threading
import unittest
from pathlib import Path

import support
import triage

ALLOWED_IMPORTS = {
    "__future__", "argparse", "dataclasses", "datetime", "fnmatch", "json", "os",
    "pathlib", "re", "subprocess", "sys", "time",
}

NETWORK_MODULES = {
    "socket", "ssl", "urllib", "urllib3", "http", "httplib", "requests", "ftplib",
    "smtplib", "telnetlib", "asyncio", "xmlrpc", "webbrowser", "poplib", "imaplib",
}


def fingerprint(root: Path) -> dict[str, str]:
    """Everything under root: size, mode, modification time, content digest."""
    marks: dict[str, str] = {}
    for current, directories, files in os.walk(root, followlinks=False):
        directories.sort()
        for name in sorted(directories) + sorted(files):
            path = os.path.join(current, name)
            relative = os.path.relpath(path, root)
            try:
                info = os.lstat(path)
            except OSError as exc:
                marks[relative] = f"unreadable:{exc.errno}"
                continue
            if os.path.islink(path):
                marks[relative] = f"link:{os.readlink(path)}"
                continue
            if os.path.isdir(path):
                marks[relative] = f"dir:{oct(info.st_mode)}:{info.st_mtime_ns}"
                continue
            digest = hashlib.sha256()
            try:
                with open(path, "rb") as handle:
                    for block in iter(lambda: handle.read(65536), b""):
                        digest.update(block)
            except OSError as exc:
                marks[relative] = f"unreadable:{exc.errno}"
                continue
            marks[relative] = f"file:{info.st_size}:{info.st_mtime_ns}:{digest.hexdigest()}"
    return marks


class ReadOnly(unittest.TestCase):
    def test_nothing_under_the_scanned_roots_changes(self):
        fixture = support.fresh_fixture("small")
        before = fingerprint(fixture)
        support.collect(fixture)
        after = fingerprint(fixture)
        changed = sorted(
            path for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        self.assertEqual([], changed,
                         "the collector modified files, indexes, references or configuration")

    def test_the_fingerprint_would_notice_a_change(self):
        """The detector is exercised, not assumed."""
        fixture = support.fresh_fixture("small")
        before = fingerprint(fixture)
        (Path(support.roots_of(fixture)[0]) / "a-new-file.txt").write_text("x", encoding="utf-8")
        after = fingerprint(fixture)
        self.assertNotEqual(before, after)

    def test_every_external_command_is_allowed_and_carries_the_read_only_flag(self):
        fixture = support.build_fixture("small")
        triage.COMMAND_TRACE.clear()
        support.collect(fixture)
        self.assertTrue(triage.COMMAND_TRACE)
        for call in triage.COMMAND_TRACE:
            argv = call["argv"]
            self.assertIn(argv[0], triage.ALLOWED_EXECUTABLES, argv)
            if argv[0] == "git":
                self.assertIn("--no-optional-locks", argv, argv)

    def test_an_executable_outside_the_allow_list_is_refused(self):
        with self.assertRaises(triage.CommandError):
            triage.run_command(["curl", "https://example.invalid"])
        self.assertEqual({"git", "ps", "lsof"}, triage.ALLOWED_EXECUTABLES)


class NoNetwork(unittest.TestCase):
    def test_the_collector_imports_nothing_outside_a_named_list(self):
        """An allow list, not a deny list: a deny list is a list of the network
        clients somebody thought of."""
        source = (support.ROOT / "triage.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(set(), imported - ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS))
        self.assertEqual(set(), imported & NETWORK_MODULES, sorted(imported & NETWORK_MODULES))

    def test_no_name_of_a_socket_or_an_http_client_appears_in_the_collector(self):
        source = (support.ROOT / "triage.py").read_text(encoding="utf-8")
        forbidden = {"socket", "create_connection", "urlopen", "Request", "HTTPConnection",
                     "HTTPSConnection", "connect", "sendto", "getaddrinfo", "requests", "httpx"}
        seen = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Name) and node.id in forbidden:
                seen.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in forbidden:
                seen.add(node.attr)
        self.assertEqual(set(), seen, sorted(seen))

    def test_the_collection_runs_with_no_network_namespace_at_all(self):
        """The strong control: no network exists while the collector runs.

        A proxy variable only catches a client that honours it. A namespace with
        nothing in it catches everything, and the report still comes out whole,
        which is what says the collector never needed a network.
        """
        required = os.environ.get("TRIAGE_REQUIRE_NAMESPACE") == "1"
        if not shutil.which("unshare"):
            if required:
                self.fail("unshare was required for this run and is not installed")
            self.skipTest("unshare is not available on this platform")
        probe = subprocess.run(["unshare", "-rn", "true"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
        if probe.returncode != 0:
            if required:
                self.fail(f"a network namespace was required and could not be created: {probe.stderr.strip()}")
            self.skipTest("this machine does not allow an unprivileged network namespace")

        fixture = support.build_fixture("small")
        roots = []
        for root in support.roots_of(fixture):
            roots += ["--root", root]
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "report.json")
            done = subprocess.run(
                ["unshare", "-rn", sys.executable, str(support.ROOT / "triage.py"), *roots,
                 "--now", support.REFERENCE_TIME, "--json", out],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600,
            )
            self.assertEqual(0, done.returncode, done.stderr)
            report = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertGreater(report["counts"]["candidate_directories"], 0,
                           "the collection has to be whole with no network, not merely quiet")

    def test_a_listener_set_as_a_proxy_counts_no_connection(self):
        fixture = support.build_fixture("small")
        connections = []
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(8)
        server.settimeout(0.3)
        stop = threading.Event()

        def accept_loop():
            while not stop.is_set():
                try:
                    client, _address = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                connections.append(1)
                client.close()

        thread = threading.Thread(target=accept_loop, daemon=True)
        thread.start()
        address = f"http://127.0.0.1:{server.getsockname()[1]}"
        try:
            environment = dict(os.environ)
            for name in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                environment[name] = address
            roots = []
            for root in support.roots_of(fixture):
                roots += ["--root", root]
            done = subprocess.run(
                [sys.executable, str(support.ROOT / "triage.py"), *roots,
                 "--now", support.REFERENCE_TIME, "--json", os.devnull],
                env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300,
            )
            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual([], connections, "the collector opened a connection")

            # The listener is exercised: it does count when something connects.
            probe = socket.create_connection(("127.0.0.1", server.getsockname()[1]), timeout=2)
            probe.close()
            for _ in range(30):
                if connections:
                    break
                threading.Event().wait(0.1)
            self.assertEqual([1], connections, "the listener does not count, so the result above proved nothing")
        finally:
            stop.set()
            server.close()
            thread.join(timeout=2)


class Privacy(unittest.TestCase):
    def test_the_report_carries_names_not_contents(self):
        fixture = support.fresh_fixture("small")
        secret = "DATABASE_URL=postgres://localhost/only-here"
        report = support.collect(fixture)
        text = json.dumps(report) + triage.markdown(report, None, None, False)
        self.assertNotIn(secret, text, "a file content reached the report")
        self.assertNotIn("postgres://", text)
        self.assertIn(".env", text, "the name of the file is what makes the decision readable")

    def test_the_report_carries_no_absolute_path_of_this_machine(self):
        fixture = support.fresh_fixture("small")
        report = support.collect(fixture)
        text = json.dumps(report) + triage.markdown(report, None, None, False)
        self.assertNotIn(str(fixture), text)
        self.assertNotIn(str(Path.home()), text)


if __name__ == "__main__":
    unittest.main()
