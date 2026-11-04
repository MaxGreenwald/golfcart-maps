"""scripts/check_agents_md.py fails closed, and web-ci keeps every existing step.

Must-fail: a cited file that is not in the tree, a branch note for a branch
already merged into master, and a line with the stale phrase "says beta".
Must-pass: a short file that cites a real path (globs and placeholders do not
count) and the repo AGENTS.md. Each failure's stdout says how to fix it.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "check_agents_md.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "web-ci.yml")
LIMIT = 16 * 1024

sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_pr_body  # noqa: E402


def run(body, root=None):
    fd, path = tempfile.mkstemp(prefix="agents-", suffix=".md")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return subprocess.run(
            [sys.executable, SCRIPT, "--root", root or ROOT, path],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    finally:
        os.remove(path)


def prove(label, proc):
    print("PROOF %s exit=%s\n%s" % (label, proc.returncode, proc.stdout), file=sys.stderr, flush=True)


CLEAN = """# fixture

Where a check lives only on an unmerged branch, the branch is named.

`scripts/check_agents_md.py`
`scripts/test_*.py`
`public/data/<id>/`
`ios/*.swift`
"""


class AgentsMd(unittest.TestCase):
    def test_missing_check_file_fails(self):
        proc = run("`scripts/missing_check.py`\n")
        prove("missing check file", proc)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("scripts/missing_check.py", proc.stdout)
        self.assertIn("Fix:", proc.stdout)
        self.assertIn("RESULT 1 FAIL", proc.stdout)
        self.assertNotIn("says beta", proc.stdout)

    def test_merged_branch_note_fails(self):
        proc = run("`scripts/check_agents_md.py` branch no-verified-claims\n")
        prove("merged branch note", proc)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("already merged into master", proc.stdout)
        self.assertIn("no-verified-claims", proc.stdout)
        self.assertIn("Fix: drop 'branch no-verified-claims'", proc.stdout)
        self.assertIn("RESULT 1 FAIL", proc.stdout)

    def test_says_beta_fails(self):
        proc = run("`scripts/check_agents_md.py`\nOutbound text says beta.\n")
        prove("says beta", proc)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("stale phrase 'says beta'", proc.stdout)
        self.assertIn("Fix: remove 'says beta'", proc.stdout)
        self.assertIn("RESULT 1 FAIL", proc.stdout)

    def test_missing_branch_fails(self):
        proc = run("`scripts/check_agents_md.py` branch no-such-branch-7a62\n")
        prove("missing branch", proc)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("does not exist", proc.stdout)
        self.assertIn("fetch-depth: 0", proc.stdout)
        self.assertIn("Fix:", proc.stdout)

    def test_over_16kib_fails_and_exact_limit_passes(self):
        base = "`scripts/check_agents_md.py`\n"
        exact = base + ("x" * (LIMIT - len(base.encode("utf-8"))))
        self.assertEqual(len(exact.encode("utf-8")), LIMIT)
        ok = run(exact)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("RESULT ALL PASS", ok.stdout)
        over = run(exact + "x")
        prove("over 16 KiB", over)
        self.assertEqual(over.returncode, 1, over.stdout + over.stderr)
        self.assertIn("16 KiB", over.stdout)
        self.assertIn("Fix:", over.stdout)

    def test_clean_fixture_passes(self):
        proc = run(CLEAN)
        prove("clean fixture", proc)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_repo_agents_md_passes(self):
        proc = subprocess.run(
            [sys.executable, SCRIPT],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        prove("repo AGENTS.md", proc)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_check_guards_adds_the_step_and_removes_nothing(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        missing, report = test_pr_body.check_guards(text)
        print(report, file=sys.stderr, flush=True)
        self.assertEqual(missing, [], report)
        self.assertIn("added data: python scripts/check_agents_md.py", report)
        self.assertIn("agents-md check added", report)
        self.assertNotIn("REMOVED", report)

    def test_check_guards_flags_a_removed_agents_step(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace(
            "python scripts/check_agents_md.py",
            "python scripts/removed_agents.py",
            1,
        )
        missing, report = test_pr_body.check_guards(text)
        self.assertTrue(missing, report)
        self.assertIn("REMOVED data: python scripts/check_agents_md.py", report)


if __name__ == "__main__":
    unittest.main()
