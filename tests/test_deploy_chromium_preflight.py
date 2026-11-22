"""deploy_web.sh production refuses before the build or wrangler when Playwright Chromium is missing.

Run: python3 -m unittest tests.test_deploy_chromium_preflight -v

Why: on Nov 22 2026 (t596u) the Pages upload finished, then verify_live failed 0/12 only
because ~/.cache/ms-playwright was missing. The preflight now stops that before any upload.

Like tests/test_prod_gate.py, each case copies the deploy scripts into a temp git repo whose
master equals origin/master, with an allowlisted reusable ref, so the prod gate passes. npx
and wrangler on PATH and WRANGLER are stubs that write a sentinel: if either runs, the test
fails. GCM_BOT_LOG and GCM_DEPLOY_REFS point at temp files, never /workspace/gcm.

Missing case: PLAYWRIGHT_BROWSERS_PATH is an empty temp dir, so Playwright finds no browser
(on a machine without the playwright package the import fails, which is also "missing").
Present case: real Chromium. It is skipped where Chromium cannot launch (the data CI job)
and runs in the browser CI job, which installs Chromium. The temp repo has no build scripts,
so after the preflight passes the next step (check_single_source.py) fails: nothing deploys.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = (
    "deploy_web.sh",
    "prod_gate.sh",
    "check_new_region_only.py",
    "check_deploy_ref.py",
    "check_playwright_chromium.py",
)
MISSING_MSG = "Playwright Chromium missing; run: python3 -m playwright install chromium"


def chromium_launches():
    proc = subprocess.run(
        ["python3", os.path.join(ROOT, "scripts/check_playwright_chromium.py")],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


class ChromiumPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        bindir = os.path.join(self.tmp.name, "bin")
        os.makedirs(bindir)
        self.sentinel = os.path.join(self.tmp.name, "wrangler-invoked")
        stub = "#!/bin/sh\necho invoked >> '%s'\nexit 99\n" % self.sentinel
        for name in ("npx", "wrangler"):
            path = os.path.join(bindir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(stub)
            os.chmod(path, 0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = bindir + os.pathsep + self.env.get("PATH", "")
        self.env["WRANGLER"] = os.path.join(bindir, "wrangler")
        self.env.pop("CLOUDFLARE_API_TOKEN", None)
        self.env.pop("GIT_DIR", None)
        self.env.pop("GIT_WORK_TREE", None)
        self.log = os.path.join(self.tmp.name, "bot-log.md")
        self.env["GCM_BOT_LOG"] = self.log
        refs = os.path.join(self.tmp.name, "deploy_refs.json")
        with open(refs, "w", encoding="utf-8") as f:
            json.dump({"refs": [{"ref": "chat-123", "source": "test-source",
                                 "scope": "production deploy", "one_time": False}]}, f)
        self.env["GCM_DEPLOY_REFS"] = refs
        self.repo = self.make_repo()

    def make_repo(self):
        d = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(d, "scripts"))
        git = ["git", "-C", d]
        subprocess.check_call(git + ["init", "-b", "master"], stdout=subprocess.DEVNULL)
        subprocess.check_call(git + ["config", "user.email", "test@example.com"])
        subprocess.check_call(git + ["config", "user.name", "test"])
        subprocess.check_call(git + ["config", "commit.gpgsign", "false"])
        for fname in SCRIPTS:
            shutil.copy(os.path.join(ROOT, "scripts", fname), os.path.join(d, "scripts", fname))
        subprocess.check_call(git + ["add", "scripts"])
        subprocess.check_call(git + ["commit", "-m", "base"], stdout=subprocess.DEVNULL)
        subprocess.check_call(git + ["update-ref", "refs/remotes/origin/master", "HEAD"])
        return d

    def deploy(self):
        return subprocess.run(
            ["bash", os.path.join(self.repo, "scripts/deploy_web.sh"), "production", "--max-ok", "chat-123"],
            cwd=self.repo, env=self.env, capture_output=True, text=True,
        )

    def assert_nothing_deployed(self, proc):
        out = proc.stdout + "\n" + proc.stderr
        self.assertFalse(os.path.exists(self.sentinel), "wrangler ran:\n" + out)
        self.assertFalse(os.path.exists(self.log), "bot-log line written:\n" + out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "dist")), "build ran:\n" + out)

    def test_missing_chromium_refuses_before_build_and_upload(self):
        empty = os.path.join(self.tmp.name, "no-browsers")
        os.makedirs(empty)
        self.env["PLAYWRIGHT_BROWSERS_PATH"] = empty
        proc = self.deploy()
        print("MISSING-CHROMIUM exit=%s wrangler_called=%s" % (
            proc.returncode, "yes" if os.path.exists(self.sentinel) else "no"), flush=True)
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertIn("chromium preflight FAIL", proc.stderr)
        self.assertIn(MISSING_MSG, proc.stderr)
        self.assertNotIn("chromium preflight OK", proc.stdout)
        self.assert_nothing_deployed(proc)

    @unittest.skipUnless(chromium_launches(), "Playwright Chromium not installed here (runs in the browser CI job)")
    def test_present_chromium_passes_the_check(self):
        proc = self.deploy()
        print("PRESENT-CHROMIUM exit=%s" % proc.returncode, flush=True)
        self.assertIn("chromium preflight OK", proc.stdout, proc.stderr)
        self.assertNotIn(MISSING_MSG, proc.stderr)
        # Temp repo has no check_single_source.py, so the script stops at the next step.
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("check_single_source.py", proc.stderr)
        self.assert_nothing_deployed(proc)

    def test_preflight_runs_before_build_and_wrangler(self):
        with open(os.path.join(ROOT, "scripts/deploy_web.sh"), encoding="utf-8") as f:
            text = f.read()
        check = text.index("python3 scripts/check_playwright_chromium.py")
        self.assertLess(text.index("bash scripts/prod_gate.sh --max-ok"), check)
        self.assertLess(check, text.index("python3 scripts/build_web.py"))
        self.assertLess(check, text.index("pages deploy dist"))


if __name__ == "__main__":
    unittest.main()
