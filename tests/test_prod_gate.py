"""Production deploys refuse before wrangler without Max's OK ref, or when HEAD is ahead of origin.

Run: python3 -m unittest tests.test_prod_gate -v

The ahead-of-origin cases copy the deploy scripts into a temp git repo whose master
has one local commit on top of origin/master. The no-ref cases also hit the real
scripts in this checkout. WRANGLER is a stub, and npx/wrangler on PATH are stubs:
if either runs, the test fails. GCM_BOT_LOG points at a temp file, never
/workspace/gcm/bot-log.md.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPTS = ("deploy_web.sh", "deploy_worker.sh", "prod_gate.sh", "check_new_region_only.py")


class ProdGate(unittest.TestCase):
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
        self.env["GCM_BOT_LOG"] = os.path.join(self.tmp.name, "bot-log.md")
        self.env.pop("GIT_DIR", None)
        self.env.pop("GIT_WORK_TREE", None)

    def _clear_sentinel(self):
        if os.path.exists(self.sentinel):
            os.remove(self.sentinel)

    def assert_refused_before_wrangler(self, proc, needle, label):
        invoked = os.path.exists(self.sentinel)
        print("%s exit=%s wrangler_called=%s" % (label, proc.returncode, "yes" if invoked else "no"), flush=True)
        self.assertEqual(proc.returncode, 1, proc.stdout + "\n" + proc.stderr)
        self.assertFalse(invoked, "wrangler ran:\n" + proc.stdout + "\n" + proc.stderr)
        self.assertIn(needle, proc.stderr, proc.stdout + "\n" + proc.stderr)
        self._clear_sentinel()

    def run_script(self, script, args, cwd):
        self._clear_sentinel()
        return subprocess.run(
            ["bash", script, *args], cwd=cwd, env=self.env, capture_output=True, text=True
        )

    def make_repo(self, name, ahead=False):
        """Temp repo on master. origin/master is the first commit; ahead adds one local commit."""
        d = os.path.join(self.tmp.name, name)
        os.makedirs(d)
        git = ["git", "-C", d]
        subprocess.check_call(git + ["init", "-b", "master"], stdout=subprocess.DEVNULL)
        subprocess.check_call(git + ["config", "user.email", "test@example.com"])
        subprocess.check_call(git + ["config", "user.name", "test"])
        subprocess.check_call(git + ["config", "commit.gpgsign", "false"])
        scripts = os.path.join(d, "scripts")
        os.makedirs(scripts)
        for fname in SCRIPTS:
            shutil.copy(os.path.join(ROOT, "scripts", fname), os.path.join(scripts, fname))
        subprocess.check_call(git + ["add", "scripts"])
        subprocess.check_call(git + ["commit", "-m", "base"], stdout=subprocess.DEVNULL)
        subprocess.check_call(git + ["update-ref", "refs/remotes/origin/master", "HEAD"])
        if ahead:
            subprocess.check_call(git + ["commit", "--allow-empty", "-m", "local only"], stdout=subprocess.DEVNULL)
            head = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
            origin = subprocess.check_output(git + ["rev-parse", "refs/remotes/origin/master"], text=True).strip()
            self.assertNotEqual(head, origin)
            self.assertEqual(subprocess.check_output(git + ["rev-parse", "--abbrev-ref", "HEAD"], text=True).strip(), "master")
        return d

    def test_web_no_max_ok_exits_1_before_wrangler(self):
        # Real entrypoint, whatever branch this checkout is on.
        proc = self.run_script(os.path.join(ROOT, "scripts/deploy_web.sh"), ["production"], ROOT)
        self.assert_refused_before_wrangler(proc, "--max-ok", "NO-MAX-OK web real")
        proc = self.run_script(
            os.path.join(ROOT, "scripts/deploy_web.sh"), ["production", "--max-ok"], ROOT
        )
        self.assert_refused_before_wrangler(proc, "--max-ok", "NO-MAX-OK web real empty-flag")
        # Temp master that matches origin/master, so the miss is the ref and not the branch.
        d = self.make_repo("web-aligned")
        proc = self.run_script(os.path.join(d, "scripts/deploy_web.sh"), ["production"], d)
        self.assert_refused_before_wrangler(proc, "--max-ok", "NO-MAX-OK web aligned-master")
        self.assertNotIn("only from master", proc.stderr)
        self.assertNotIn("is not origin/master", proc.stderr)

    def test_web_ahead_of_origin_exits_1_before_wrangler(self):
        d = self.make_repo("web-ahead", ahead=True)
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", "chat-123"],
            d,
        )
        self.assert_refused_before_wrangler(proc, "is not origin/master", "AHEAD web")
        self.assertNotIn("only from master", proc.stderr)
        self.assertIn("no unpushed or local-only commits", proc.stderr)

    def test_worker_no_max_ok_exits_1_before_wrangler(self):
        for name in ("partner", "analytics"):
            proc = self.run_script(
                os.path.join(ROOT, "scripts/deploy_worker.sh"), ["production", name], ROOT
            )
            self.assert_refused_before_wrangler(proc, "--max-ok", "NO-MAX-OK worker %s real" % name)
        d = self.make_repo("worker-aligned")
        for name in ("partner", "analytics"):
            proc = self.run_script(
                os.path.join(d, "scripts/deploy_worker.sh"), ["production", name], d
            )
            self.assert_refused_before_wrangler(proc, "--max-ok", "NO-MAX-OK worker %s aligned-master" % name)
            self.assertNotIn("only from master", proc.stderr)

    def test_worker_ahead_of_origin_exits_1_before_wrangler(self):
        d = self.make_repo("worker-ahead", ahead=True)
        for name in ("partner", "analytics"):
            proc = self.run_script(
                os.path.join(d, "scripts/deploy_worker.sh"),
                ["production", name, "--max-ok", "card-456"],
                d,
            )
            self.assert_refused_before_wrangler(proc, "is not origin/master", "AHEAD worker %s" % name)
            self.assertNotIn("only from master", proc.stderr)

    def test_dirty_tree_still_refuses_before_wrangler(self):
        d = self.make_repo("web-dirty")
        os.makedirs(os.path.join(d, "public"))
        with open(os.path.join(d, "public", "x.txt"), "w", encoding="utf-8") as f:
            f.write("x\n")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", "chat-123"],
            d,
        )
        self.assert_refused_before_wrangler(
            proc, "uncommitted changes in public/ functions/ lib/; commit first", "DIRTY web"
        )

    def test_gate_passes_when_head_equals_origin_master(self):
        d = self.make_repo("gate-ok")
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "card-9", "--paths", "scripts"],
            d,
        )
        print("GATE-OK exit=%s wrangler_called=%s" % (proc.returncode, "yes" if os.path.exists(self.sentinel) else "no"), flush=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(self.sentinel))

    def test_bot_log_line_goes_to_temp_file(self):
        log = self.env["GCM_BOT_LOG"]
        gate = os.path.join(ROOT, "scripts/prod_gate.sh")
        proc = self.run_script(gate, ["--append-log", "--max-ok", "chat-99", "--status", "PASS"], ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(log, encoding="utf-8") as f:
            line = f.read().strip()
        print("BOT-LOG %s" % line, flush=True)
        self.assertRegex(line, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT commit=[0-9a-f]{12} max-ok=chat-99 PASS$")
        proc = self.run_script(gate, ["--append-log", "--max-ok", "chat-99", "--status", "FAIL"], ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(log, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertRegex(lines[-1], r" max-ok=chat-99 FAIL$")
        self.assertNotIn("/workspace/gcm/bot-log.md", "\n".join(lines))
        # Missing ref writes nothing.
        os.remove(log)
        proc = self.run_script(gate, ["--append-log", "--status", "PASS"], ROOT)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertFalse(os.path.exists(log))
        with open(gate, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("GCM_BOT_LOG:-/workspace/gcm/bot-log.md", text)

    def test_deploy_scripts_call_the_gate_before_wrangler(self):
        with open(os.path.join(ROOT, "scripts/deploy_web.sh"), encoding="utf-8") as f:
            web = f.read()
        call = "bash scripts/prod_gate.sh"
        self.assertLess(web.index(call), web.index("pages deploy"))
        tail = web.split("pages deploy", 1)[1]
        self.assertLess(tail.index("verify_live"), tail.index("--append-log"))
        self.assertLess(tail.index("--append-log"), tail.index('exit "$rc"'))
        self.assertIn("https://golfcartmap.com", tail)
        with open(os.path.join(ROOT, "scripts/deploy_worker.sh"), encoding="utf-8") as f:
            worker = f.read()
        self.assertLess(worker.index(call), worker.index("$W deploy"))
        self.assertEqual(worker.count(call), 1)


class NewRegionOk(ProdGate):
    """Max, Oct 30 2026 (t390s2042): a diff that only adds new regions may ship with
    --new-region-ok instead of --max-ok. Anything else still needs --max-ok."""

    def region_repo(self, name, change):
        d = self.make_repo(name)
        git = ["git", "-C", d]
        data = os.path.join(d, "public", "data")
        os.makedirs(os.path.join(data, "sd"))
        with open(os.path.join(data, "regions.json"), "w", encoding="utf-8") as f:
            json.dump([{"id": "sd", "name": "San Diego"}], f)
        with open(os.path.join(data, "sd", "index.json"), "w", encoding="utf-8") as f:
            f.write("{}\n")
        subprocess.check_call(git + ["add", "-A"])
        subprocess.check_call(git + ["commit", "-m", "live"], stdout=subprocess.DEVNULL)
        live = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
        change(d, data)
        subprocess.check_call(git + ["add", "-A"])
        subprocess.check_call(git + ["commit", "-m", "next"], stdout=subprocess.DEVNULL)
        subprocess.check_call(git + ["update-ref", "refs/remotes/origin/master", "HEAD"])
        return d, live

    @staticmethod
    def add_town(d, data):
        with open(os.path.join(data, "regions.json"), "w", encoding="utf-8") as f:
            json.dump([{"id": "sd", "name": "San Diego"}, {"id": "newtown", "name": "New Town"}], f)
        os.makedirs(os.path.join(data, "newtown", "tiles"))
        for rel in ("index.json", "tiles/0_0.json"):
            with open(os.path.join(data, "newtown", rel), "w", encoding="utf-8") as f:
                f.write("{}\n")

    def gate(self, d, live):
        return self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--new-region-ok", "t390s2042", "--live-commit", live],
            d,
        )

    def test_new_region_only_diff_passes_the_gate(self):
        d, live = self.region_repo("nr-ok", self.add_town)
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--new-region-ok", "t390s2042", "--live-commit", live, "--paths", "public"],
            d,
        )
        print("NEW-REGION-OK exit=%s" % proc.returncode, flush=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("new-region check PASS", proc.stdout)

    def test_existing_region_or_code_change_needs_max_ok(self):
        def edit_existing(d, data):
            self.add_town(d, data)
            with open(os.path.join(data, "sd", "index.json"), "w", encoding="utf-8") as f:
                f.write('{"x": 1}\n')

        def edit_existing_entry(d, data):
            with open(os.path.join(data, "regions.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "sd", "name": "SD"}, {"id": "newtown"}], f)
            os.makedirs(os.path.join(data, "newtown"))
            with open(os.path.join(data, "newtown", "index.json"), "w", encoding="utf-8") as f:
                f.write("{}\n")

        def edit_code(d, data):
            self.add_town(d, data)
            with open(os.path.join(d, "public", "app.js"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")

        def add_file_to_existing(d, data):
            self.add_town(d, data)
            with open(os.path.join(data, "sd", "extra.json"), "w", encoding="utf-8") as f:
                f.write("{}\n")

        for label, change in (("existing-region-file", edit_existing),
                              ("existing-region-entry", edit_existing_entry),
                              ("code", edit_code),
                              ("add-into-existing-region", add_file_to_existing)):
            d, live = self.region_repo("nr-" + label, change)
            proc = self.gate(d, live)
            self.assert_refused_before_wrangler(proc, "this deploy needs --max-ok", "NEW-REGION-FAIL " + label)

    def test_new_region_ok_without_live_commit_is_refused(self):
        d, _ = self.region_repo("nr-nolive", self.add_town)
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"), ["production", "--new-region-ok", "t390s2042"], d
        )
        self.assert_refused_before_wrangler(proc, "--live-commit", "NEW-REGION no live commit")


if __name__ == "__main__":
    unittest.main()
