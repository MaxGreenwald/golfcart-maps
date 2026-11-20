"""Cloudflare free-tier headroom check: fixtures, projection, recovery.

Run: python3 -m unittest tests.test_cf_headroom -v

The must-fail fixture is the 19 Nov 2026 gcm-analytics Durable Object rows
read cap (5,000,000 by 14:23 UTC / 6:23 AM PT). The must-pass fixture is the
post-fix usage of about 189,242 rows read after the 7:48 PM PT 19 Nov deploy.
Repo convention: a failing check exits 1.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "cf_headroom.py"
FIX_FAIL = ROOT / "tests" / "fixtures" / "cf_headroom_nov19_fail.json"
FIX_PASS = ROOT / "tests" / "fixtures" / "cf_headroom_postfix_pass.json"


def load_mod():
    spec = importlib.util.spec_from_file_location("cf_headroom", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = load_mod()


def run_script(*args, env=None):
    proc_env = os.environ.copy()
    proc_env.pop("CLOUDFLARE_API_TOKEN", None)
    proc_env.pop("GCM_STATS_KEY", None)
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


class HeadroomHelpers(unittest.TestCase):
    def test_wrangler_targets_include_repo_workers_and_sdr(self):
        names = MOD.load_targets(ROOT)
        self.assertEqual(names, ["gcm-analytics", "gcm-partner", "gcm-sdr-chat"])
        wrangler = MOD.load_wrangler_production_names(ROOT)
        self.assertIn("gcm-analytics", wrangler)
        self.assertIn("gcm-partner", wrangler)
        self.assertNotIn("gcm-analytics-preview", wrangler)
        self.assertNotIn("gcm-partner-preview", wrangler)

    def test_official_free_limits(self):
        self.assertEqual(MOD.FREE_LIMITS["do_rows_read"], 5_000_000)
        self.assertEqual(MOD.FREE_LIMITS["do_rows_written"], 100_000)
        self.assertEqual(MOD.FREE_LIMITS["kv_reads"], 100_000)
        self.assertEqual(MOD.FREE_LIMITS["kv_writes"], 1_000)
        self.assertEqual(MOD.FREE_LIMITS["worker_requests"], 100_000)

    def test_projection_and_classify(self):
        now = datetime(2026, 11, 19, 14, 23, tzinfo=timezone.utc)
        hours = MOD.hours_elapsed(now)
        self.assertAlmostEqual(hours, 14 + 23 / 60, places=6)
        projected = MOD.project_used(5_000_000, hours)
        self.assertGreater(projected, 8_000_000)
        status, pct = MOD.classify(projected, 5_000_000)
        self.assertEqual(status, "FAIL")
        self.assertGreaterEqual(pct, 80)

        post = datetime(2026, 11, 20, 4, 58, tzinfo=timezone.utc)
        post_hours = MOD.hours_elapsed(post)
        post_proj = MOD.project_used(189_242, post_hours)
        post_status, post_pct = MOD.classify(post_proj, 5_000_000)
        self.assertEqual(post_status, "OK")
        self.assertLess(post_pct, 50)

    def test_warn_threshold_is_fifty_percent(self):
        status, pct = MOD.classify(2_500_000, 5_000_000)
        self.assertEqual(status, "WARN")
        self.assertAlmostEqual(pct, 50.0)
        status_ok, _ = MOD.classify(2_499_999, 5_000_000)
        self.assertEqual(status_ok, "OK")
        status_fail, _ = MOD.classify(4_000_000, 5_000_000)
        self.assertEqual(status_fail, "FAIL")

    def test_near_baseline_definition(self):
        self.assertTrue(MOD.is_near_baseline(75, 100))
        self.assertFalse(MOD.is_near_baseline(74.9, 100))
        self.assertTrue(MOD.is_near_baseline(125, 100))
        self.assertEqual(MOD.NEAR_MIN_FRACTION, 0.75)
        self.assertEqual(MOD.BASELINE_FIRST, date(2026, 11, 12))
        self.assertEqual(MOD.BASELINE_LAST, date(2026, 11, 18))


class HeadroomFixtures(unittest.TestCase):
    def test_nov19_fixture_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fail.txt"
            proc = run_script("--fixture", str(FIX_FAIL), "--out", str(out))
        self.assertEqual(
            proc.returncode,
            1,
            "must-fail fixture must exit 1\n"
            + proc.stdout
            + "\n"
            + proc.stderr,
        )
        self.assertIn("RESULT 1 FAIL", proc.stdout)
        self.assertIn("gcm-analytics  do_rows_read", proc.stdout)
        self.assertIn("used=5000000", proc.stdout)
        self.assertIn("FAIL", proc.stdout)
        # Projected full day is well above the 5,000,000 cap.
        self.assertRegex(proc.stdout, r"projected=8[0-9]{6}")

    def test_postfix_fixture_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pass.txt"
            proc = run_script("--fixture", str(FIX_PASS), "--out", str(out))
            self.assertTrue(out.is_file(), proc.stdout + "\n" + proc.stderr)
            saved = out.read_text(encoding="utf-8")
        self.assertEqual(
            proc.returncode,
            0,
            "must-pass fixture must exit 0\n"
            + proc.stdout
            + "\n"
            + proc.stderr,
        )
        self.assertIn("RESULT ALL PASS", proc.stdout)
        self.assertIn("used=189242", proc.stdout)
        status_lines = [
            line for line in proc.stdout.splitlines()
            if line and not line.startswith("#") and not line.startswith("RESULT")
        ]
        self.assertTrue(status_lines, proc.stdout)
        self.assertTrue(all(line.endswith("  OK") for line in status_lines), proc.stdout)
        self.assertEqual(saved, proc.stdout)

    def test_warn_fixture_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "warn.json"
            out = Path(tmp) / "warn.txt"
            path.write_text(
                json.dumps(
                    {
                        "now": "2026-11-20T12:00:00Z",
                        "counters": [
                            {
                                "worker": "gcm-analytics",
                                "counter": "do_rows_read",
                                "used": 1_500_000,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            proc = run_script("--fixture", str(path), "--out", str(out))
        # 1,500,000 used after 12 hours projects to 3,000,000, which is 60%.
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        self.assertIn("WARN", proc.stdout)
        self.assertIn("RESULT 1 WARN", proc.stdout)
        self.assertNotIn("RESULT 1 FAIL", proc.stdout)


class HeadroomRecovery(unittest.TestCase):
    def _write(self, tmp, body):
        path = Path(tmp) / "rec.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_recovery_requires_under_fifty_and_near_baseline(self):
        daily = {
            "2026-11-12": {"sessions": 70},
            "2026-11-13": {"sessions": 70},
            "2026-11-14": {"sessions": 70},
            "2026-11-15": {"sessions": 70},
            "2026-11-16": {"sessions": 70},
            "2026-11-17": {"sessions": 70},
            "2026-11-18": {"sessions": 70},
            "2026-11-20": {"sessions": 70},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                {
                    "recovery": {
                        "day": "2026-11-20",
                        "counters": [
                            {
                                "worker": "gcm-analytics",
                                "counter": "do_rows_read",
                                "used": 200_000,
                            }
                        ],
                        "daily": daily,
                    }
                },
            )
            out = Path(tmp) / "out.txt"
            proc = run_script("--recovery", "--fixture", str(path), "--out", str(out))
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        self.assertIn("incident_fixed: yes", proc.stdout)
        self.assertIn("near: yes", proc.stdout)
        self.assertIn("RESULT ALL PASS", proc.stdout)

    def test_recovery_fails_when_volume_is_short(self):
        daily = {
            "2026-11-12": {"sessions": 70},
            "2026-11-13": {"sessions": 70},
            "2026-11-14": {"sessions": 70},
            "2026-11-15": {"sessions": 70},
            "2026-11-16": {"sessions": 70},
            "2026-11-17": {"sessions": 70},
            "2026-11-18": {"sessions": 70},
            "2026-11-19": {"sessions": 22},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                {
                    "recovery": {
                        "day": "2026-11-19",
                        "counters": [
                            {
                                "worker": "gcm-analytics",
                                "counter": "do_rows_read",
                                "used": 1000,
                            }
                        ],
                        "daily": daily,
                    }
                },
            )
            proc = run_script(
                "--recovery",
                "--fixture",
                str(path),
                "--out",
                str(Path(tmp) / "out.txt"),
            )
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertIn("incident_fixed: no", proc.stdout)
        self.assertIn("near: no", proc.stdout)
        self.assertIn("RESULT", proc.stdout)
        self.assertIn("FAIL", proc.stdout)

    def test_recovery_fails_when_a_counter_was_over_fifty(self):
        daily = {
            "2026-11-12": {"sessions": 70},
            "2026-11-13": {"sessions": 70},
            "2026-11-14": {"sessions": 70},
            "2026-11-15": {"sessions": 70},
            "2026-11-16": {"sessions": 70},
            "2026-11-17": {"sessions": 70},
            "2026-11-18": {"sessions": 70},
            "2026-11-19": {"sessions": 70},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                {
                    "recovery": {
                        "day": "2026-11-19",
                        "counters": [
                            {
                                "worker": "gcm-analytics",
                                "counter": "do_rows_read",
                                "used": 5_000_000,
                            }
                        ],
                        "daily": daily,
                    }
                },
            )
            proc = run_script(
                "--recovery",
                "--fixture",
                str(path),
                "--out",
                str(Path(tmp) / "out.txt"),
            )
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertIn("incident_fixed: no", proc.stdout)
        self.assertIn("headroom: not under 50%", proc.stdout)


if __name__ == "__main__":
    unittest.main()
