"""scripts/test_*.py must not print FAIL and exit 0.

The meta-check is scripts/check_test_exit.py (web-ci). These tests also
plant one failing ck in a copy of scripts/test_focus.py and show that copy
fails the meta-check, then leave no plant file behind.
"""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")


def load(name, filename):
    path = os.path.join(SCRIPTS, filename)
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


CHECK = load("gcm_check_test_exit", "check_test_exit.py")
VERIFY = load("gcm_verify_live", "verify_live")


class CheckExit(unittest.TestCase):
    def test_repo_scripts_cannot_print_fail_and_exit_0(self):
        problems = []
        for path in CHECK.default_paths():
            problems.extend(CHECK.analyze_path(path))
        self.assertEqual(problems, [])
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "check_test_exit.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)

    def test_planted_failing_ck_in_a_copy_of_test_focus_fails_the_meta_check(self):
        """Copy test_focus.py, plant one failing ck, drop finish(); the meta-check must fail."""
        with open(os.path.join(SCRIPTS, "test_focus.py"), encoding="utf-8") as handle:
            original = handle.read()
        self.assertIn("from _check import ck, finish", original)
        self.assertIn("finish()", original)
        planted = original.replace("from _check import ck, finish\n", "")
        planted = planted.replace(
            "finish()",
            'print("RESULT", "ALL PASS" if not fails else "%d FAIL: %s" % (len(fails), fails))',
        )
        planted = (
            "fails = []\n"
            "def ck(n, c, x=\"\"):\n"
            "    print((\"PASS \" if c else \"FAIL \") + str(n), x)\n"
            "    if not c:\n"
            "        fails.append(n)\n"
            "ck(\"planted\", False)\n"
            + planted
        )
        directory = tempfile.mkdtemp(prefix="gcm-exit-plant-")
        path = os.path.join(directory, "test_exit_plant.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(planted)
        problems = CHECK.analyze_path(path)
        self.assertTrue(problems, "planted copy should fail the meta-check")
        self.assertTrue(any("exit 0" in item or "FAIL" in item for item in problems))
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "check_test_exit.py"), path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("RESULT", proc.stdout)
        self.assertIn("FAIL", proc.stdout)
        # The planted ck itself, without the browser half, still exits 0.
        tail = os.path.join(directory, "test_exit_plant_tail.py")
        with open(tail, "w", encoding="utf-8") as handle:
            handle.write(
                "fails = []\n"
                "def ck(n, c, x=\"\"):\n"
                "    print((\"PASS \" if c else \"FAIL \") + str(n), x)\n"
                "    if not c:\n"
                "        fails.append(n)\n"
                "ck(\"planted\", False)\n"
                "print(\"RESULT\", \"ALL PASS\" if not fails else \"%d FAIL: %s\" % (len(fails), fails))\n"
            )
        ran = subprocess.run([sys.executable, tail], capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertIn("FAIL planted", ran.stdout)
        self.assertIn("RESULT 1 FAIL", ran.stdout)
        self.assertFalse(os.path.exists(os.path.join(SCRIPTS, "test_exit_plant.py")))

    def test_shared_helper_exits_1_when_a_ck_fails(self):
        script = textwrap.dedent(
            """
            import sys
            sys.path.insert(0, %r)
            from _check import ck, finish
            ck("planted", False)
            finish()
            """
            % SCRIPTS
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("FAIL planted", proc.stdout)
        self.assertIn("RESULT 1 FAIL:", proc.stdout)

    def test_shared_helper_exits_0_when_every_ck_passes(self):
        script = textwrap.dedent(
            """
            import sys
            sys.path.insert(0, %r)
            from _check import ck, finish
            ck("ok", True)
            finish()
            """
            % SCRIPTS
        )
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_runpy_preserves_finish_exit_code(self):
        """scripts/live_notrack.py runs the suite with runpy. SystemExit must stick."""
        directory = tempfile.mkdtemp(prefix="gcm-runpy-")
        path = os.path.join(directory, "test_tiny.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                "import sys\n"
                "sys.path.insert(0, %r)\n"
                "from _check import ck, finish\n"
                "ck('planted', False)\n"
                "finish()\n" % SCRIPTS
            )
        proc = subprocess.run(
            [sys.executable, "-c", "import runpy\nrunpy.run_path(%r, run_name='__main__')\n" % path],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("RESULT 1 FAIL:", proc.stdout)

    def test_verify_live_result_line_fails_even_when_exit_code_is_0(self):
        old = "FAIL far away -> San Diego default\nRESULT 1 FAIL: ['far away -> San Diego default']\n"
        self.assertTrue(VERIFY.result_line_lists_failures(old))
        self.assertFalse(VERIFY.suite_passed(0, old))
        self.assertFalse(VERIFY.suite_passed(0, "RESULT chromium 2 FAIL: ['a']\n"))
        self.assertTrue(VERIFY.suite_passed(0, "PASS default region sd\nRESULT ALL PASS\n"))
        self.assertFalse(VERIFY.suite_passed(1, "RESULT ALL PASS\n"))
        self.assertTrue(VERIFY.suite_passed(0, "layout only, no RESULT line\n"))


if __name__ == "__main__":
    unittest.main()
