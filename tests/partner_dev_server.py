"""Start scripts/partner_dev.mjs (public/ plus the real partner Worker on an in-memory
database) for browser tests. Needs Node 22.5 or newer for node:sqlite.

    with PartnerDev(seed_dict) as dev:
        page.goto(dev.url + "/partner")
"""
import json
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def node_ok():
    node = shutil.which("node")
    if not node:
        return False
    r = subprocess.run([node, "-e", "require('node:sqlite')"], capture_output=True)
    return r.returncode == 0


class PartnerDev:
    def __init__(self, seed, env=None):
        self.seed = seed
        self.env = env or {}
        self.proc = None
        self.url = ""

    def __enter__(self):
        fd, self.seed_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(self.seed, f)
        env = dict(os.environ, PARTNER_DEV_ENV=json.dumps(self.env))
        self.proc = subprocess.Popen(
            ["node", os.path.join(ROOT, "scripts", "partner_dev.mjs"), "0", self.seed_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=ROOT,
        )
        lines = []
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("partner_dev.mjs exited: " + "".join(lines))
            lines.append(line)
            if line.startswith("READY "):
                self.url = line.split(" ", 1)[1].strip()
                return self

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc.stdout.close()
        try:
            os.unlink(self.seed_path)
        except OSError:
            pass


def sign_in(page, base, email):
    """Mock sign-in (DEV_AUTH_EMAIL path), then open the partner admin."""
    page.goto(base + "/partner", wait_until="domcontentloaded")
    page.evaluate(
        """async (email) => {
          const r = await fetch('/api/partner/auth/dev', {method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({email, expect: email})});
          if (!r.ok) throw new Error('sign in failed ' + r.status);
        }""",
        email,
    )
    page.goto(base + "/partner", wait_until="domcontentloaded")
