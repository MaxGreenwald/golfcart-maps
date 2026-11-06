"""scripts/check_no_agent_chatter.py fails conversation residue and passes a clean tree.

Deny phrases are joined only in memory or in a temp file, which this test
deletes. The repo copy of the check must stay clean under its own scan.
"""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
SCRIPT = os.path.join(SCRIPTS, "check_no_agent_chatter.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "web-ci.yml")
AGENTS = os.path.join(ROOT, "AGENTS.md")


def load():
    loader = importlib.machinery.SourceFileLoader("gcm_check_no_agent_chatter", SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


CHECK = load()


def run_check(args, env=None):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


class NoAgentChatter(unittest.TestCase):
    def test_clean_tree_exits_0(self):
        proc = run_check([])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_planted_comment_exits_1(self):
        """One comment line matching deny entry 1 fails the process."""
        phrase = "".join(CHECK.PIECES[0])
        directory = tempfile.mkdtemp(prefix="gcm-chatter-plant-")
        path = os.path.join(directory, "plant.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# " + phrase + " x; now y\n")
        try:
            hits = CHECK.scan_path(path, CHECK.compile_patterns())
            self.assertEqual(hits, [f"{path}:1: chat residue #1"])
            proc = run_check([path])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("FAIL", proc.stdout)
            self.assertIn("chat residue #1", proc.stdout)
            self.assertIn("RESULT 1 FAIL", proc.stdout)
            self.assertNotIn(phrase, proc.stdout)
        finally:
            os.remove(path)
            os.rmdir(directory)
        self.assertFalse(os.path.exists(path))

    def test_each_deny_entry_is_a_hit(self):
        patterns = CHECK.compile_patterns()
        self.assertEqual(len(patterns), len(CHECK.PIECES))
        for index, parts in enumerate(CHECK.PIECES, start=1):
            line = "note " + "".join(parts) + " end"
            hits = CHECK.scan_text("sample.py", line, patterns)
            self.assertIn(f"sample.py:1: chat residue #{index}", hits)

    def test_near_miss_is_clean(self):
        patterns = CHECK.compile_patterns()
        phrase = "".join(CHECK.PIECES[0])
        # A longer word sharing the same prefix is not a hit.
        longer = phrase + "come"
        self.assertEqual(CHECK.scan_text("sample.py", "# " + longer, patterns), [])
        self.assertEqual(CHECK.scan_text("sample.py", "x = 1\n", patterns), [])

    def test_walk_skips_research_and_archive(self):
        phrase = "".join(CHECK.PIECES[0])
        root = tempfile.mkdtemp(prefix="gcm-chatter-tree-")
        try:
            for rel in ("research/note.py", "archive/old.swift", "public/app.js", "ios/App.swift"):
                folder = os.path.join(root, os.path.dirname(rel))
                os.makedirs(folder, exist_ok=True)
                body = "ok = 1\n" if rel.startswith("public/") or rel.startswith("ios/") else "# " + phrase + "\n"
                with open(os.path.join(root, rel), "w", encoding="utf-8") as handle:
                    handle.write(body)
            files = CHECK.iter_source_files(root)
            rels = sorted(os.path.relpath(path, root) for path in files)
            self.assertEqual(rels, ["ios/App.swift", "public/app.js"])
            hits = []
            patterns = CHECK.compile_patterns()
            for path in files:
                hits.extend(CHECK.scan_path(path, patterns, root=root))
            self.assertEqual(hits, [])
            # An explicit path is still scanned, so a plant outside the walk can fail.
            planted = os.path.join(root, "research", "note.py")
            direct = CHECK.scan_path(planted, patterns, root=root)
            self.assertEqual(direct, ["research/note.py:1: chat residue #1"])
        finally:
            for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                for name in filenames:
                    os.remove(os.path.join(dirpath, name))
                os.rmdir(dirpath)

    def test_pr_body_hit_exits_1_and_clean_body_exits_0(self):
        phrase = "".join(CHECK.PIECES[2])
        dirty = os.environ.copy()
        dirty["PR_BODY"] = "Summary\n\n" + phrase + "\n"
        proc = run_check(["--pr-body"], env=dirty)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("<pr-body>:3: chat residue #3", proc.stdout)
        self.assertNotIn(phrase, proc.stdout)
        clean = os.environ.copy()
        clean["PR_BODY"] = "Summary\n\nDrivers see the same map.\n"
        proc = run_check(["--pr-body"], env=clean)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS (pr body)", proc.stdout)

    def test_workflow_and_agents_name_the_check(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            workflow = handle.read()
        self.assertIn("python scripts/check_no_agent_chatter.py\n", workflow)
        self.assertIn("python scripts/check_no_agent_chatter.py --pr-body\n", workflow)
        with open(AGENTS, encoding="utf-8") as handle:
            agents = handle.read()
        self.assertIn("`scripts/check_no_agent_chatter.py`", agents)
