"""scripts/test_*.py must not shadow tests/test_*.py during unittest discover.

`python -m unittest discover -s tests` imports each file by basename. Earlier
tests insert scripts/ at sys.path[0], so a same-named script is what gets
imported. scripts/test_town_pages.py did that and raised
ModuleNotFoundError: No module named 'playwright' in the unit job, which does
not install Playwright. The browser sweep is scripts/test_town_map_pages.py
and still runs from scripts/verify_live (suite name test_town_pages).
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def test_py_names(folder):
    return {
        name
        for name in os.listdir(os.path.join(ROOT, folder))
        if name.startswith("test_") and name.endswith(".py")
    }


class ScriptShadow(unittest.TestCase):
    def test_no_shared_basenames(self):
        shared = sorted(test_py_names("scripts") & test_py_names("tests"))
        self.assertEqual(
            shared,
            [],
            "same basename in scripts/ and tests/ is imported from scripts/ "
            "during unittest discover -s tests once scripts/ is on sys.path",
        )

    def test_poisoned_path_imports_unit_town_pages(self):
        """scripts/ ahead of tests/ must load tests/test_town_pages.py, not Playwright."""
        code = r"""
import os, sys
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, "scripts"))
sys.path.insert(1, os.path.join(root, "tests"))
import test_town_pages
got = os.path.realpath(test_town_pages.__file__)
want = os.path.realpath(os.path.join(root, "tests", "test_town_pages.py"))
if got != want:
    raise SystemExit("imported %s" % got)
if "playwright" in sys.modules:
    raise SystemExit("playwright imported")
"""
        r = subprocess.run(
            [sys.executable, "-c", code, ROOT],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_verify_live_still_runs_the_browser_sweep(self):
        script = os.path.join(ROOT, "scripts", "test_town_map_pages.py")
        self.assertTrue(os.path.isfile(script))
        text = open(os.path.join(ROOT, "scripts", "verify_live"), encoding="utf-8").read()
        self.assertIn('"test_town_pages", "scripts/test_town_map_pages.py"', text)
        self.assertIn("sync_playwright", open(script, encoding="utf-8").read())
