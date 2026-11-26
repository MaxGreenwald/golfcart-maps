"""scripts/test_structured_data.py fails a date-only VideoObject uploadDate.

Must-fail: a fixture page whose uploadDate is the date-only value 2026-11-08
exits 1 and names uploadDate. Must-pass: the same page with a timezone offset,
and @graph plus JSON-LD arrays, exit 0.
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "test_structured_data.py")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "structured_data")


def run(name):
    return subprocess.run(
        [sys.executable, SCRIPT, os.path.join(FIXTURES, name)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class StructuredDataCheck(unittest.TestCase):
    def test_date_only_uploaddate_fails_and_names_field(self):
        proc = run("date_only_uploaddate")
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 1, out)
        self.assertIn("uploadDate", out)
        self.assertIn("VideoObject", out)
        self.assertIn("page.html", out)
        self.assertIn("ISO 8601", out)
        self.assertIn("timezone", out.lower())

    def test_timezone_uploaddate_passes(self):
        proc = run("ok_uploaddate")
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("RESULT ALL PASS", out)
        self.assertNotIn("FAIL", out)

    def test_graph_and_array_blocks_pass(self):
        proc = run("graph_and_array")
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("RESULT ALL PASS", out)
        self.assertNotIn("FAIL", out)


if __name__ == "__main__":
    unittest.main()
