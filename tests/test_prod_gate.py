"""Production deploys refuse before wrangler without an allowlisted Max OK ref.

Run: python3 -m unittest tests.test_prod_gate -v

The ahead-of-origin cases copy the deploy scripts into a temp git repo whose master
has one local commit on top of origin/master. The no-ref cases also hit the real
scripts in this checkout. WRANGLER is a stub, and npx/wrangler on PATH are stubs:
if either runs, the test fails. GCM_BOT_LOG points at a temp file, never
/workspace/gcm/bot-log.md. GCM_DEPLOY_REFS points at a temp allowlist, never
/workspace/gcm/approvals/deploy_refs.json. setUp seeds the refs the older cases
pass (chat-123, card-456, card-9, chat-99) as reusable rows (one_time false).
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
    "deploy_worker.sh",
    "prod_gate.sh",
    "check_new_region_only.py",
    "check_deploy_ref.py",
)


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
        self.seed_allowlist([
            self.allow_row("chat-123"),
            self.allow_row("card-456"),
            self.allow_row("card-9"),
            self.allow_row("chat-99"),
        ])

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

    def allow_row(self, ref, one_time=False):
        return {
            "ref": ref,
            "source": "test-source",
            "scope": "production deploy",
            "one_time": one_time,
        }

    def seed_allowlist(self, rows):
        path = os.path.join(self.tmp.name, "deploy_refs.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"refs": rows}, handle)
            handle.write("\n")
        self.env["GCM_DEPLOY_REFS"] = path
        return path

    def used_path(self):
        return os.path.join(os.path.dirname(self.env["GCM_DEPLOY_REFS"]), "deploy_refs_used.json")

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
        self.assertEqual(worker.count(call), 2)
        prod_tail = worker.split('if [ "$mode" = production ]; then', 1)[1]
        self.assertLess(prod_tail.index("$W deploy"), prod_tail.index("--mark-used"))
        self.assertNotIn("--mark-used", worker.split("\nelse\n", 1)[1])


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


class Allowlist(ProdGate):
    """--max-ok must be a row in the allowlist. The file is not in the repo.

    Must-fail: invented ref, gary-relay-* even when listed, reused one_time ref,
    missing allowlist. Must-pass: dry run of a seeded one_time ref does not mark it used.
    """

    def test_invented_ref_not_in_allowlist(self):
        d = self.make_repo("invented")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", "invented-ref"],
            d,
        )
        self.assert_refused_before_wrangler(proc, "not in the approval allowlist", "ALLOWLIST-MISS web")
        self.assertIn("invented-ref", proc.stderr)
        self.assertNotIn("only from master", proc.stderr)
        log = self.env["GCM_BOT_LOG"]
        proc = self.run_script(
            os.path.join(ROOT, "scripts/prod_gate.sh"),
            ["--append-log", "--max-ok", "invented-ref", "--status", "PASS"],
            ROOT,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("not in the approval allowlist", proc.stderr)
        self.assertFalse(os.path.exists(log), proc.stderr)
        self.assertFalse(os.path.exists(self.used_path()))

    def test_relay_ref_refused_even_when_listed(self):
        relay = "gary-relay-2694-max-1649PT"
        other = "Gary-RELAY-9"
        self.seed_allowlist([self.allow_row(relay), self.allow_row(other, one_time=True)])
        d = self.make_repo("relay")
        for ref in (relay, other):
            proc = self.run_script(
                os.path.join(d, "scripts/deploy_web.sh"),
                ["production", "--max-ok", ref],
                d,
            )
            self.assert_refused_before_wrangler(proc, "looks relayed", "RELAY " + ref)
            self.assertIn("not Max's own approval", proc.stderr)
            self.assertNotIn("not in the approval allowlist", proc.stderr)
        self.env["GCM_DEPLOY_REFS"] = os.path.join(self.tmp.name, "missing-relay.json")
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", relay, "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("looks relayed", proc.stderr)
        self.assertNotIn("approval allowlist is missing", proc.stderr)
        self.assertFalse(os.path.exists(self.used_path()))

    def test_reused_one_time_ref_refused(self):
        ref = "once-9"
        self.seed_allowlist([self.allow_row(ref, one_time=True)])
        gate = os.path.join(ROOT, "scripts/prod_gate.sh")
        proc = self.run_script(gate, ["--append-log", "--max-ok", ref, "--status", "PASS"], ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(self.env["GCM_BOT_LOG"], encoding="utf-8") as handle:
            self.assertEqual(len(handle.read().splitlines()), 1)
        with open(self.used_path(), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["refs"], [ref])
        # The log line alone is enough. Deleting the used-ref record must not revive it.
        os.remove(self.used_path())
        d = self.make_repo("reused")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", ref],
            d,
        )
        self.assert_refused_before_wrangler(proc, "one_time and was already used", "REUSED web")
        proc = self.run_script(gate, ["--append-log", "--max-ok", ref, "--status", "FAIL"], ROOT)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("one_time and was already used", proc.stderr)
        with open(self.env["GCM_BOT_LOG"], encoding="utf-8") as handle:
            self.assertEqual(len(handle.read().splitlines()), 1)

    def test_missing_allowlist_refused(self):
        missing = os.path.join(self.tmp.name, "no-such-allowlist.json")
        self.env["GCM_DEPLOY_REFS"] = missing
        d = self.make_repo("missing-allow")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", "chat-123"],
            d,
        )
        self.assert_refused_before_wrangler(proc, "approval allowlist is missing", "ALLOWLIST-FILE-MISS")
        self.assertIn(missing, proc.stderr)
        gate = os.path.join(ROOT, "scripts/prod_gate.sh")
        proc = self.run_script(gate, ["--append-log", "--max-ok", "chat-123", "--status", "PASS"], ROOT)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("approval allowlist is missing", proc.stderr)
        self.assertFalse(os.path.exists(self.env["GCM_BOT_LOG"]))
        self.env.pop("GCM_DEPLOY_REFS", None)
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "chat-123", "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("/workspace/gcm/approvals/deploy_refs.json", proc.stderr)
        self.assertIn("approval allowlist is missing", proc.stderr)

    def test_invalid_and_unreadable_allowlist_refused(self):
        bad = os.path.join(self.tmp.name, "bad.json")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("{")
        self.env["GCM_DEPLOY_REFS"] = bad
        d = self.make_repo("bad-allow")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", "chat-123"],
            d,
        )
        self.assert_refused_before_wrangler(proc, "approval allowlist is invalid", "ALLOWLIST-INVALID-JSON")
        with open(bad, "w", encoding="utf-8") as handle:
            json.dump({"refs": [{"ref": "chat-123", "source": "test-source", "scope": "production deploy", "one_time": "true"}]}, handle)
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "chat-123", "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("one_time must be true or false", proc.stderr)
        if os.geteuid() == 0:
            return
        os.chmod(bad, 0)
        self.addCleanup(os.chmod, bad, 0o644)
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "chat-123", "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("approval allowlist is unreadable", proc.stderr)

    def test_dry_run_seeded_one_time_ref_does_not_mark(self):
        ref = "dry-ok"
        self.seed_allowlist([self.allow_row(ref, one_time=True)])
        d = self.make_repo("dry-run")
        gate = os.path.join(d, "scripts/prod_gate.sh")
        args = ["--max-ok", ref, "--paths", "scripts"]
        for n in (1, 2):
            proc = self.run_script(gate, args, d)
            print("DRY-RUN %s exit=%s" % (n, proc.returncode), flush=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(os.path.exists(self.sentinel))
            self.assertFalse(os.path.exists(self.used_path()))
            self.assertFalse(os.path.exists(self.env["GCM_BOT_LOG"]))

    def test_mark_used_is_idempotent_and_then_check_refuses(self):
        ref = "once-worker"
        self.seed_allowlist([self.allow_row(ref, one_time=True)])
        gate = os.path.join(ROOT, "scripts/prod_gate.sh")
        for n in (1, 2):
            proc = self.run_script(gate, ["--mark-used", "--max-ok", ref], ROOT)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(self.used_path(), encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["refs"], [ref], "mark %s" % n)
        d = self.make_repo("marked")
        proc = self.run_script(
            os.path.join(d, "scripts/deploy_web.sh"),
            ["production", "--max-ok", ref],
            d,
        )
        self.assert_refused_before_wrangler(proc, "one_time and was already used", "MARKED-THEN-CHECK")
        proc = self.run_script(gate, ["--mark-used", "--max-ok", ref], ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(self.used_path(), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["refs"], [ref])

    def test_one_time_refuses_when_used_record_cannot_be_written(self):
        folder = os.path.join(self.tmp.name, "ro-allow")
        os.makedirs(folder)
        path = os.path.join(folder, "deploy_refs.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"refs": [self.allow_row("once-ro", one_time=True)]}, handle)
        os.chmod(folder, 0o555)
        self.addCleanup(os.chmod, folder, 0o755)
        self.env["GCM_DEPLOY_REFS"] = path
        d = self.make_repo("ro-allow-repo")
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "once-ro", "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("used-ref record directory is not writable", proc.stderr)
        self.assertFalse(os.path.exists(self.sentinel))

    def test_invalid_used_record_refuses(self):
        ref = "once-bad-used"
        self.seed_allowlist([self.allow_row(ref, one_time=True)])
        with open(self.used_path(), "w", encoding="utf-8") as handle:
            handle.write("{")
        d = self.make_repo("bad-used")
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", ref, "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("used-ref record is invalid", proc.stderr)

    def test_new_region_log_ref_skips_allowlist(self):
        self.env["GCM_DEPLOY_REFS"] = os.path.join(self.tmp.name, "missing.json")
        gate = os.path.join(ROOT, "scripts/prod_gate.sh")
        proc = self.run_script(
            gate, ["--append-log", "--max-ok", "new-region-ok:t390s2042", "--status", "PASS"], ROOT
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(self.env["GCM_BOT_LOG"], encoding="utf-8") as handle:
            line = handle.read().strip()
        self.assertRegex(line, r" max-ok=new-region-ok:t390s2042 PASS$")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "deploy_refs_used.json")))
        proc = self.run_script(
            gate, ["--append-log", "--max-ok", "new-region-ok:gary-relay-1", "--status", "PASS"], ROOT
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("looks relayed", proc.stderr)
        with open(self.env["GCM_BOT_LOG"], encoding="utf-8") as handle:
            self.assertEqual(len(handle.read().splitlines()), 1)

    def test_new_region_ok_token_is_not_a_max_ok_bypass(self):
        d = self.make_repo("nr-bypass")
        proc = self.run_script(
            os.path.join(d, "scripts/prod_gate.sh"),
            ["--max-ok", "new-region-ok:t390s2042", "--paths", "scripts"],
            d,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("not in the approval allowlist", proc.stderr)
        self.assertFalse(os.path.exists(self.used_path()))


if __name__ == "__main__":
    unittest.main()
