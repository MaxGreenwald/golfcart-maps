"""PR bodies need Summary, Evidence, and Merge danger (scripts/check_pr_body.py).

Must-fail: a body with no Merge danger section exits 1 and names that section.
Must-fail: Evidence that only prints PASS, a stale EVIDENCE sha, or no stamp
for the PR head exits 1 and says to rerun scripts/evidence.sh on HEAD.
Must-pass: a body with all three sections, Evidence that has command output
or a URL, and (when PR_HEAD_SHA is set) a matching stamp or Actions URL.
check_guards reads .github/workflows/web-ci.yml and shows the pr-body step
plus every guard that was already there.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "check_pr_body.py")
TEMPLATE = os.path.join(ROOT, ".github", "pull_request_template.md")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "web-ci.yml")

FULL = """## Summary
Drivers and shops see no map change. Pull requests now need Summary, Evidence, and Merge danger before merge.

## Evidence
python -m unittest tests.test_pr_body -v
PASS

## Merge danger
No town, road, or page content changes, so this cannot show a road as legal when it is not. Revert the commit to roll back.
"""

NO_DANGER = """## Summary
Drivers and shops see no map change. Pull requests now need Summary, Evidence, and Merge danger before merge.

## Evidence
python -m unittest tests.test_pr_body -v
PASS
"""

URL_ONLY = """## Summary
Shop staff get the same map. This change only checks pull request text.

## Evidence
Preview https://golfcartmap.com/map/

## Merge danger
No road geometry changes. A wrong legal color cannot come from this diff. Revert the commit to roll back.
"""

COMMAND_NO_OUTPUT = """## Summary
Drivers and shops see no map change.

## Evidence
The commands you ran with their PASS output, live or preview URLs.
python -m unittest tests.test_pr_body -v

## Merge danger
No road is recolored. Revert the commit to roll back.
"""

EMPTY_DANGER = """## Summary
Drivers and shops see no map change. Pull requests now need a risk note.

## Evidence
python -m unittest tests.test_pr_body -v
PASS

## Merge danger

"""

# Guards already in web-ci.yml. Adding pr-body must not drop these.
FILE_KEPT = (
    "name: web-ci",
    "Never deploys anything.",
    "\n  push:\n",
    "\n  pull_request:\n",
)
DATA_KEPT = (
    "actions/checkout@v4",
    "python scripts/check_single_source.py",
    "python scripts/check_verified_wording.py",
    "node --test tests/analytics.test.mjs",
    "node --test tests/livedata.test.mjs",
    "actions/setup-python@v5",
    "python -m unittest discover -s tests -v",
    "node scripts/test_roadrule.js && node scripts/test_range.js",
    "python scripts/check_enforcement.py",
    "python scripts/validate_data.py",
)
BROWSER_KEPT = (
    "actions/checkout@v4",
    "actions/setup-python@v5",
    "pip install playwright && python -m playwright install --with-deps chromium webkit",
    "mkdir -p ci-shots",
    "python scripts/build_web.py",
    "python scripts/serve_dist.py",
    "python scripts/test_sw.py",
    "python -m unittest tests.test_search_keep_text -v",
    "python scripts/test_ui.py",
    "python scripts/test_verified.py",
    "python scripts/test_analytics.py",
    "python scripts/test_delmar_warning.py",
    "python scripts/test_safety_caution.py",
    "python scripts/test_islands_ui.py",
    "python scripts/test_city_chip.py",
    "python scripts/test_chips.py",
    "python scripts/test_layout.py",
    "python scripts/test_chip_overflow.py",
    "python scripts/test_vehicle.py",
    "python scripts/test_appstore.py",
    "python scripts/test_live_regions.py",
    "python scripts/test_sv_label.py",
    "python scripts/test_trusted_osm_ui.py",
    "python -m unittest tests.test_partner_brand_color -v",
    "python -m unittest tests.test_partner_experience_stops -v",
    "actions/upload-artifact@v4",
)


def job_blocks(text):
    try:
        after = text.split("\njobs:\n", 1)[1]
    except IndexError:
        return {}
    blocks = {}
    current = None
    buf = []
    for line in after.split("\n"):
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            if current is not None:
                blocks[current] = "\n".join(buf)
            current = match.group(1)
            buf = [line]
        elif current is not None:
            buf.append(line)
    if current is not None:
        blocks[current] = "\n".join(buf)
    return blocks


def check_guards(text):
    """Return (missing, report). Report lists every kept guard plus the added pr-body and agents-md steps."""
    blocks = job_blocks(text)
    lines = []
    missing = []
    for item in FILE_KEPT:
        if item in text:
            lines.append("kept file: %s" % item.strip())
        else:
            missing.append("file: %s" % item.strip())
            lines.append("REMOVED file: %s" % item.strip())
    for job, kept in (("data", DATA_KEPT), ("browser", BROWSER_KEPT)):
        block = blocks.get(job, "")
        if not block:
            missing.append("job %s" % job)
            lines.append("REMOVED job %s" % job)
            continue
        for item in kept:
            if item in block:
                lines.append("kept %s: %s" % (job, item))
            else:
                missing.append("%s: %s" % (job, item))
                lines.append("REMOVED %s: %s" % (job, item))
    pr = blocks.get("pr-body", "")
    step_ok = (
        "python scripts/check_pr_body.py" in pr
        and "github.event_name == 'pull_request'" in pr
        and "PR_BODY" in pr
    )
    sha_ok = "PR_HEAD_SHA" in pr and "github.event.pull_request.head.sha" in pr
    if step_ok and sha_ok:
        lines.append("added pr-body: python scripts/check_pr_body.py")
        lines.append("added pr-body: PR_HEAD_SHA from github.event.pull_request.head.sha")
    else:
        missing.append("pr-body")
        if not step_ok:
            lines.append("REMOVED pr-body: python scripts/check_pr_body.py")
        if not sha_ok:
            lines.append("REMOVED pr-body: PR_HEAD_SHA from github.event.pull_request.head.sha")
    data = blocks.get("data", "")
    if "python scripts/check_agents_md.py" in data and "fetch-depth: 0" in data:
        lines.append("added data: python scripts/check_agents_md.py")
    else:
        missing.append("agents-md")
        lines.append("REMOVED data: python scripts/check_agents_md.py")
    if not {"data", "browser", "pr-body"} <= set(blocks):
        missing.append("jobs %s" % sorted(blocks))
    kept_n = sum(1 for line in lines if line.startswith("kept "))
    if missing:
        header = "check_guards: FAIL %d removed" % len(missing)
    else:
        header = "check_guards: pr-body added, agents-md check added, %d existing guards kept" % kept_n
    return missing, "\n".join([header] + lines)


def _env(body=None, head_sha=None):
    env = os.environ.copy()
    env.pop("PR_BODY", None)
    env.pop("PR_HEAD_SHA", None)
    if body is not None:
        env["PR_BODY"] = body
    if head_sha is not None:
        env["PR_HEAD_SHA"] = head_sha
    return env


def run_file(body, head_sha=None):
    fd, path = tempfile.mkstemp(prefix="pr-body-", suffix=".md")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return subprocess.run(
            [sys.executable, SCRIPT, path],
            cwd=ROOT,
            env=_env(head_sha=head_sha),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
    finally:
        os.remove(path)


def run_env(body):
    return subprocess.run(
        [sys.executable, SCRIPT],
        cwd=ROOT,
        env=_env(body),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )


def run_stdin(body):
    return subprocess.run(
        [sys.executable, SCRIPT],
        cwd=ROOT,
        env=_env(),
        input=body,
        capture_output=True,
        text=True,
    )


def fail_lines(proc):
    return [line for line in proc.stdout.splitlines() if line.startswith("FAIL ")]


class PrBody(unittest.TestCase):
    def test_missing_merge_danger_fails(self):
        for label, proc in (("file", run_file(NO_DANGER)), ("env", run_env(NO_DANGER))):
            with self.subTest(label=label):
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(fail_lines(proc), ["FAIL Missing section: Merge danger"])

    def test_full_body_passes(self):
        for label, proc in (
            ("file", run_file(FULL)),
            ("env", run_env(FULL)),
            ("stdin", run_stdin(FULL)),
        ):
            with self.subTest(label=label):
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("RESULT ALL PASS", proc.stdout)
                self.assertNotIn("FAIL", proc.stdout)

    def test_bold_headings_and_fenced_example_pass(self):
        bold = """**Summary**
Drivers and shops see no map change.

**Evidence**
https://golfcartmap.com/map/

**Merge danger**
No road is recolored. Revert the commit to roll back.
"""
        fenced = """## Summary
Drivers and shops see no map change.

## Evidence
```
## Merge danger
placeholder only
```
python -m unittest tests.test_pr_body -v
PASS

## Merge danger
No road is recolored. Revert the commit to roll back.
"""
        for label, body in (("bold", bold), ("fenced", fenced)):
            with self.subTest(label=label):
                proc = run_file(body)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_url_only_passes(self):
        proc = run_file(URL_ONLY)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT ALL PASS", proc.stdout)

    def test_command_without_output_fails(self):
        proc = run_file(COMMAND_NO_OUTPUT)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(fail_lines(proc), ["FAIL Evidence has no command output or URL"])

    def test_empty_merge_danger_names_the_section(self):
        proc = run_file(EMPTY_DANGER)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(fail_lines(proc), ["FAIL Empty section: Merge danger"])

    def test_empty_body_names_every_section(self):
        proc = run_env("")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            fail_lines(proc),
            [
                "FAIL Missing section: Summary",
                "FAIL Missing section: Evidence",
                "FAIL Missing section: Merge danger",
            ],
        )

    def test_template_is_not_a_filled_body(self):
        with open(TEMPLATE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(
            re.findall(r"(?m)^#{1,6} .+$", text),
            ["## Summary", "## Evidence", "## Merge danger"],
        )
        proc = run_file(text)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(
            fail_lines(proc),
            [
                "FAIL Empty section: Summary",
                "FAIL Empty section: Evidence",
                "FAIL Empty section: Merge danger",
            ],
        )

    def test_check_guards_adds_pr_body_and_removes_nothing(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        missing, report = check_guards(text)
        print(report, file=sys.stderr, flush=True)
        self.assertEqual(missing, [], report)
        self.assertIn("added pr-body: python scripts/check_pr_body.py", report)
        self.assertIn(
            "added pr-body: PR_HEAD_SHA from github.event.pull_request.head.sha",
            report,
        )
        self.assertIn("added data: python scripts/check_agents_md.py", report)
        self.assertIn("agents-md check added", report)
        self.assertNotIn("REMOVED", report)

    def test_check_guards_flags_a_removed_step(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("python scripts/check_single_source.py", "python scripts/removed.py", 1)
        missing, report = check_guards(text)
        self.assertTrue(missing, report)
        self.assertIn("REMOVED data: python scripts/check_single_source.py", report)
        self.assertIn("added pr-body: python scripts/check_pr_body.py", report)
        self.assertIn(
            "added pr-body: PR_HEAD_SHA from github.event.pull_request.head.sha",
            report,
        )

    def test_check_guards_flags_missing_head_sha(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("github.event.pull_request.head.sha", "github.event.pull_request.title")
        missing, report = check_guards(text)
        self.assertTrue(missing, report)
        self.assertIn(
            "REMOVED pr-body: PR_HEAD_SHA from github.event.pull_request.head.sha",
            report,
        )


HEAD = "0123456789abcdef0123456789abcdef01234567"
OTHER = "fedcba9876543210fedcba9876543210fedcba98"
SHORT = HEAD[:12]
RERUN = "rerun scripts/evidence.sh on HEAD"
PRINT_ONLY_FAIL = "FAIL Evidence command only prints its own result: %s" % RERUN
STALE_FAIL = (
    "FAIL Evidence has no EVIDENCE stamp or GitHub Actions run URL matching HEAD %s: %s"
    % (HEAD, RERUN)
)


def body_with(evidence):
    return (
        "## Summary\n"
        "Drivers and shops see no map change. Evidence has to come from a real check on HEAD.\n"
        "\n"
        "## Evidence\n"
        "%s\n"
        "\n"
        "## Merge danger\n"
        "No town, road, or page content changes, so this cannot show a road as legal when it is not. "
        "Revert the commit to roll back.\n" % evidence.rstrip("\n")
    )


class EvidenceStamp(unittest.TestCase):
    def test_print_only_pass_fails(self):
        commands = (
            'python -c "print(\'PASS\')"',
            'python -c "print(\'...PASS\')"',
            "echo PASS",
            'echo "PASS"',
            "printf PASS",
            "printf '%s\\n' PASS",
            'echo "RESULT ALL PASS"',
            """python3 -c 'print("OK")'""",
            """node -e "console.log('PASS')" """,
            'bash -c "echo PASS"',
        )
        for cmd in commands:
            evidence = "EVIDENCE sha=%s exit=0 cmd=%s\n%s\nPASS\n" % (SHORT, cmd.strip(), cmd.strip())
            with self.subTest(cmd=cmd.strip()):
                proc = run_file(body_with(evidence), head_sha=HEAD)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(fail_lines(proc), [PRINT_ONLY_FAIL])
                self.assertIn(RERUN, proc.stdout)

    def test_stale_sha_fails(self):
        stamped = (
            "EVIDENCE sha=aaaaaaaaaaaa exit=0 cmd=python -m unittest tests.test_pr_body -v\n"
            "python -m unittest tests.test_pr_body -v\n"
            "OK\n"
        )
        stale_url = (
            "https://github.com/MaxGreenwald/golfcart-maps/commit/%s/checks\n" % OTHER
        )
        for label, evidence in (("stamp", stamped), ("actions url", stale_url)):
            with self.subTest(label=label):
                proc = run_file(body_with(evidence), head_sha=HEAD)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(fail_lines(proc), [STALE_FAIL])
                self.assertIn(RERUN, proc.stdout)

    def test_no_stamp_fails(self):
        command = "python -m unittest tests.test_pr_body -v\nPASS\n"
        bare_run = "https://github.com/MaxGreenwald/golfcart-maps/actions/runs/123456789\n"
        for label, evidence in (("command only", command), ("actions url without sha", bare_run)):
            with self.subTest(label=label):
                proc = run_file(body_with(evidence), head_sha=HEAD)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(fail_lines(proc), [STALE_FAIL])
                self.assertIn(RERUN, proc.stdout)

    def test_fresh_evidence_passes(self):
        stamped = (
            "EVIDENCE sha=%s exit=0 cmd=python -m unittest tests.test_pr_body -v\n"
            "test_fresh_evidence_passes (tests.test_pr_body.EvidenceStamp) ... ok\n"
            "OK\n" % SHORT
        )
        full_stamp = (
            "EVIDENCE sha=%s exit=0 cmd=python -m unittest tests.test_pr_body -v\n"
            "OK\n" % HEAD
        )
        checks = "https://github.com/MaxGreenwald/golfcart-maps/commit/%s/checks\n" % HEAD
        run_url = (
            "https://github.com/MaxGreenwald/golfcart-maps/actions/runs/99?sha=%s\n" % HEAD
        )
        for label, evidence in (
            ("12 char stamp", stamped),
            ("full stamp", full_stamp),
            ("commit checks url", checks),
            ("actions run url", run_url),
        ):
            with self.subTest(label=label):
                proc = run_file(body_with(evidence), head_sha=HEAD)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("RESULT ALL PASS", proc.stdout)
                self.assertNotIn("FAIL", proc.stdout)

    def test_evidence_sh_stamps_head_and_propagates_status(self):
        script = os.path.join(ROOT, "scripts", "evidence.sh")
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        short = head[:12]
        self.assertEqual(len(short), 12)
        self.assertEqual(len(head), 40)
        ok = subprocess.run(
            [script, sys.executable, "-c", "print('hello-evidence')"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        first, _, rest = ok.stdout.partition("\n")
        self.assertEqual(
            first,
            "EVIDENCE sha=%s exit=0 cmd=%s -c print('hello-evidence')"
            % (short, sys.executable),
        )
        self.assertIn("hello-evidence", rest)
        bad = subprocess.run(
            [
                script,
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('nope\\n'); sys.exit(3)",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(bad.returncode, 3, bad.stdout + bad.stderr)
        self.assertTrue(
            bad.stdout.startswith("EVIDENCE sha=%s exit=3 cmd=" % short),
            bad.stdout,
        )
        self.assertIn("nope", bad.stdout.split("\n", 1)[-1])
        usage = subprocess.run([script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(usage.returncode, 2, usage.stdout + usage.stderr)


if __name__ == "__main__":
    unittest.main()
