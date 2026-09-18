#!/usr/bin/env python3
"""Build the demonstration report, from the fixture, with the current collector.

The report published on the page is the output of this file at the commit that
was tested. `--check` rebuilds it and fails if a single byte differs, so the
page cannot drift away from the code. Nothing here reaches the network.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import triage  # noqa: E402

REFERENCE_TIME = "2026-09-18T00:00:00+00:00"
STALE_DAYS = 30
BUDGET = 120.0
MARK_START = "<!-- report:start -->"
MARK_END = "<!-- report:end -->"
DECISIONS_START = "<!-- decisions:start -->"
DECISIONS_END = "<!-- decisions:end -->"
COMMIT_START = "<!-- commit:start -->"
COMMIT_END = "<!-- commit:end -->"

# The convention that turned a description of a workspace into a buildable one.
# It travels with the report itself, not only with the page, because the report
# is the thing somebody downloads and reads on its own.
PROVENANCE = (
    "Fixture convention: 131 candidate directories, including 41 unregistered. "
    "Illustrative hypothesis, not a reconstruction. The composition and every situation built into this "
    "workspace are written in fixture/MANIFEST.md."
)

# The three decisions the page opens with, one of each status, named here so
# that they come from the generated report and never from a hand written copy.
FEATURED = (
    "worker-pipeline-wt-local-env",
    "api-gateway-wt-legacy-export",
    "web-console-copy-2",
)


def generate(scale: str = "full") -> tuple[str, dict, dict]:
    workspace = Path(tempfile.mkdtemp(prefix="agent-workspace-triage-"))
    try:
        subprocess.run(
            [sys.executable, str(HERE / "fixture" / "make_fixture.py"), "--out", str(workspace / "fixture"), "--scale", scale],
            check=True, stdout=subprocess.PIPE, text=True,
        )
        composition = json.loads((workspace / "fixture" / "composition.json").read_text(encoding="utf-8"))
        roots = sorted(str(path) for path in (workspace / "fixture" / "workspace").iterdir() if path.is_dir())
        now = datetime.fromisoformat(REFERENCE_TIME).astimezone(timezone.utc)
        report = triage.collect(
            roots=roots, now=now, stale_days=STALE_DAYS, budget=BUDGET, max_depth=3,
            excludes=[], git_timeout=30.0, with_sizes=False,
        )
        report["provenance_note"] = PROVENANCE
        text = triage.markdown(report, sessions=None, hook=None, with_sizes=False)
        return text, report, composition
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def with_code(text: str) -> str:
    """Escape, then turn `x` into a code span."""
    out = escape(text)
    while out.count("`") >= 2:
        out = out.replace("`", "<code>", 1).replace("`", "</code>", 1)
    return out.replace("`", "")


def decisions_html(report: dict) -> str:
    """The featured decisions, rendered from the report this commit produces.

    Compact on purpose: the status, the path and the decision are what a reader
    needs in the first screen. The other three parts are one click away, and
    they are the same four parts as every line of the report.
    """
    rows = {os.path.basename(row["path"]): row for row in report["decisions"]}
    blocks = []
    for name in FEATURED:
        row = rows[name]
        verdict = row["decision_sentence"]
        if row["preserved_because"]:
            joined = "; ".join(row["preserved_because"])
            verdict += " " + joined + ("" if joined.endswith(".") else ".")
        blocks.append(
            f'''<div class="decision">
      <div class="status">{escape(row["decision"])}</div>
      <div class="path">{escape(row["path"])}</div>
      <p class="verdict"><strong>{with_code(verdict)}</strong></p>
      <details>
        <summary>What was observed, the evidence, and what is still open</summary>
        <dl>
          <dt>Observed</dt>
          <dd>{with_code(row["observation"])}</dd>
          <dt>Evidence</dt>
          <dd>{with_code("; ".join(row["evidence"]))}</dd>
          <dt>Still open</dt>
          <dd>{with_code(row["remaining_condition"])}</dd>
        </dl>
      </details>
    </div>'''
        )
    return "\n    ".join(blocks)


def inject_into_site(markdown_text: str, report: dict) -> bool:
    """Put the generated report inside the page, between its two markers."""
    page = HERE / "site" / "index.html"
    if not page.exists():
        return False
    html = page.read_text(encoding="utf-8")
    for start, end in ((MARK_START, MARK_END), (DECISIONS_START, DECISIONS_END)):
        if start not in html or end not in html:
            return False
    block = f"{MARK_START}\n<pre class=\"report\">{escape(markdown_text)}</pre>\n      {MARK_END}"
    head, rest = html.split(MARK_START, 1)
    _old, tail = rest.split(MARK_END, 1)
    html = head + block + tail

    decisions = f"{DECISIONS_START}\n    {decisions_html(report)}\n    {DECISIONS_END}"
    head, rest = html.split(DECISIONS_START, 1)
    _old, tail = rest.split(DECISIONS_END, 1)
    html = head + decisions + tail

    page.write_text(html, encoding="utf-8")
    return True


def stamp(sha: str) -> int:
    """Name, on the page, the commit whose code produced the report it shows.

    It runs after the commit that carries the report, because a commit cannot
    contain its own identifier. The report is byte for byte the same on both, so
    the check that the page carries the output of the code still holds.
    """
    page = HERE / "site" / "index.html"
    html = page.read_text(encoding="utf-8")
    if COMMIT_START not in html or COMMIT_END not in html:
        print("the page carries no commit marker", file=sys.stderr)
        return 1
    link = (f'The report above is produced by commit '
            f'<a href="https://github.com/fred1433/agent-workspace-triage/commit/{sha}">{sha[:10]}</a>, '
            f'the one the tests ran on.')
    head, rest = html.split(COMMIT_START, 1)
    _old, tail = rest.split(COMMIT_END, 1)
    page.write_text(head + COMMIT_START + link + COMMIT_END + tail, encoding="utf-8")
    print(f"the page names commit {sha[:10]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the demonstration report.")
    parser.add_argument("--check", action="store_true", help="fail if the committed report is not what the code produces")
    parser.add_argument("--scale", choices=("full", "small"), default="full")
    parser.add_argument("--site", action="store_true", help="also write the report into the page")
    parser.add_argument("--stamp", metavar="SHA",
                        help="write into the page the commit that produced the report it carries")
    args = parser.parse_args(argv)

    if args.stamp:
        return stamp(args.stamp)

    text, report, composition = generate(args.scale)
    md_path = HERE / "report" / "demo-report.md"
    json_path = HERE / "report" / "demo-report.json"
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.check:
        problems = []
        if not md_path.exists() or md_path.read_text(encoding="utf-8") != text:
            problems.append("report/demo-report.md is not what the collector produces at this commit")
            committed = md_path.read_text(encoding="utf-8").splitlines() if md_path.exists() else []
            diff = list(difflib.unified_diff(committed, text.splitlines(),
                                             "committed", "produced now", lineterm="", n=1))
            problems.extend(diff[:60])
        if not json_path.exists() or json_path.read_text(encoding="utf-8") != payload:
            problems.append("report/demo-report.json is not what the collector produces at this commit")
        composition_path = HERE / "report" / "fixture-composition.json"
        composition_payload = json.dumps(composition, indent=2, sort_keys=True) + "\n"
        if not composition_path.exists() or composition_path.read_text(encoding="utf-8") != composition_payload:
            problems.append("report/fixture-composition.json is not what the fixture builds at this commit")
        page = HERE / "site" / "index.html"
        if page.exists():
            html = page.read_text(encoding="utf-8")
            if escape(text) not in html:
                problems.append("site/index.html does not carry the report this commit produces")
            if decisions_html(report) not in html:
                problems.append("site/index.html does not carry the featured decisions this commit produces")
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            print("run: python3 build_demo.py --site", file=sys.stderr)
            return 1
        print("the published report is the one this commit produces")
        return 0

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(text, encoding="utf-8")
    json_path.write_text(payload, encoding="utf-8")
    (HERE / "report" / "fixture-composition.json").write_text(
        json.dumps(composition, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.site:
        inject_into_site(text, report)
    print(f"report written: {report['counts']['candidate_directories']} candidate directories, "
          f"{report['counts']['keep']} keep, {report['counts']['removal_candidates_to_confirm']} removal candidates, "
          f"{report['counts']['undetermined']} undetermined")
    return 0


if __name__ == "__main__":
    sys.exit(main())
