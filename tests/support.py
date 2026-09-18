"""Shared helpers for the tests: build a fixture once, run the collector on it."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import triage  # noqa: E402

REFERENCE_TIME = "2026-09-18T00:00:00+00:00"
_FIXTURES: dict[str, Path] = {}


def build_fixture(scale: str = "small") -> Path:
    """Build the synthetic workspace once per process and return its path."""
    if scale in _FIXTURES:
        return _FIXTURES[scale]
    holder = Path(tempfile.mkdtemp(prefix=f"triage-test-{scale}-"))
    atexit.register(shutil.rmtree, holder, ignore_errors=True)
    subprocess.run(
        [sys.executable, str(ROOT / "fixture" / "make_fixture.py"),
         "--out", str(holder / "fixture"), "--scale", scale],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    _FIXTURES[scale] = holder / "fixture"
    return _FIXTURES[scale]


def fresh_fixture(scale: str = "small") -> Path:
    """Build a workspace this test may modify. The caller owns it."""
    holder = Path(tempfile.mkdtemp(prefix=f"triage-test-mutable-{scale}-"))
    atexit.register(shutil.rmtree, holder, ignore_errors=True)
    subprocess.run(
        [sys.executable, str(ROOT / "fixture" / "make_fixture.py"),
         "--out", str(holder / "fixture"), "--scale", scale],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return holder / "fixture"


def now() -> datetime:
    """The reference time every test reads a report against."""
    return datetime.fromisoformat(REFERENCE_TIME)


def roots_of(fixture: Path) -> list[str]:
    return sorted(str(path) for path in (fixture / "workspace").iterdir() if path.is_dir())


def composition_of(fixture: Path) -> dict:
    return json.loads((fixture / "composition.json").read_text(encoding="utf-8"))


def collect(fixture: Path, **overrides) -> dict:
    options = dict(
        roots=roots_of(fixture),
        now=datetime.fromisoformat(REFERENCE_TIME),
        stale_days=30, budget=120.0, max_depth=3, excludes=[],
        git_timeout=30.0, with_sizes=False,
    )
    options.update(overrides)
    return triage.collect(**options)


def by_name(report: dict) -> dict[str, dict]:
    """Index the decisions by the last element of their path."""
    return {os.path.basename(row["path"]): row for row in report["decisions"]}


def find(fixture: Path, name: str) -> Path:
    """Locate a directory of the workspace by its name, never by a root path."""
    for candidate in (fixture / "workspace").glob(f"*/{name}"):
        return candidate
    raise AssertionError(f"the fixture no longer builds {name}")


def first_root(fixture: Path) -> str:
    return os.path.basename(roots_of(fixture)[0])


def expected_decisions() -> dict:
    return json.loads((ROOT / "tests" / "expected_decisions.json").read_text(encoding="utf-8"))
