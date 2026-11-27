"""Freshness check for recurring Engineer job artifacts.

Run: python3 -m unittest tests.test_check_freshness -v

The must-fail fixture is a cf_headroom artifact dated 2026-11-20,
evaluated with a fixed now later than max_age_hours. The must-pass
fixture is a later artifact still inside the max age. A failing check
exits 1.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_freshness.py"
CONFIG = ROOT / "ops" / "expected_runs.json"
FIX_FAIL = ROOT / "tests" / "fixtures" / "freshness_must_fail"
FIX_PASS = ROOT / "tests" / "fixtures" / "freshness_must_pass"
# 2026-11-20 00:00 UTC plus more than 24 hours.
NOW_AFTER_NOV20 = "2026-11-22T00:00:00Z"
# 2026-11-21 00:00 UTC plus 18 hours (still inside 24 hours).
NOW_WITHIN_NOV21 = "2026-11-21T18:00:00Z"


def run_script(*args, env=None):
    proc_env = os.environ.copy()
    proc_env.pop("GCM_FRESHNESS_BASE", None)
    proc_env.pop("GCM_FRESHNESS_NOW", None)
    if env:
        proc_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=proc_env,
        check=False,
    )


class FreshnessFixtures(unittest.TestCase):
    def test_must_fail_nov20_artifact_exits_1(self):
        proc = run_script(
            "--config",
            str(CONFIG),
            "--base-dir",
            str(FIX_FAIL),
            "--now",
            NOW_AFTER_NOV20,
        )
        self.assertEqual(
            proc.returncode,
            1,
            "must-fail fixture must exit 1\n" + proc.stdout + "\n" + proc.stderr,
        )
        self.assertIn("STALE cf_headroom last=2026-11-20", proc.stdout)
        self.assertIn("STALE analytics_limit_trip_log last=2026-11-20", proc.stdout)
        self.assertNotIn("FRESHNESS PASS", proc.stdout)

    def test_must_pass_fixture_exits_0(self):
        proc = run_script(
            "--config",
            str(CONFIG),
            "--base-dir",
            str(FIX_PASS),
            "--now",
            NOW_WITHIN_NOV21,
        )
        self.assertEqual(
            proc.returncode,
            0,
            "must-pass fixture must exit 0\n" + proc.stdout + "\n" + proc.stderr,
        )
        self.assertEqual(proc.stdout.strip(), "FRESHNESS PASS")

    def test_missing_artifact_is_stale_last_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_script(
                "--config",
                str(CONFIG),
                "--base-dir",
                tmp,
                "--now",
                NOW_AFTER_NOV20,
            )
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertIn("STALE cf_headroom last=none", proc.stdout)
        self.assertIn("STALE analytics_limit_trip_log last=none", proc.stdout)

    def test_base_dir_env_matches_flag(self):
        proc = run_script(
            "--config",
            str(CONFIG),
            "--now",
            NOW_AFTER_NOV20,
            env={"GCM_FRESHNESS_BASE": str(FIX_FAIL)},
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertIn("STALE cf_headroom last=2026-11-20", proc.stdout)


if __name__ == "__main__":
    unittest.main()
