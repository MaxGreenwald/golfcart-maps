"""PR bodies need Summary, Evidence, and Merge danger (scripts/check_pr_body.py).

Must-fail: a body with no Merge danger section exits 1 and names that section.
Must-pass: a body with all three sections, and Evidence that has command output
or a URL, exits 0. check_guards reads .github/workflows/web-ci.yml and shows
the new pr-body step plus every guard that was already there.
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
    "python scripts/test_sv_label.py",
    "python scripts/test_trusted_osm_ui.py",
    "python -m unittest tests.test_partner_brand_color -v",
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
    """Return (missing, report). Report lists every kept guard and the added pr-body step."""
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
    pr_ok = (
        "python scripts/check_pr_body.py" in pr
        and "github.event_name == 'pull_request'" in pr
        and "PR_BODY" in pr
    )
    if pr_ok:
        lines.append("added pr-body: python scripts/check_pr_body.py")
    else:
        missing.append("pr-body")
        lines.append("REMOVED pr-body: python scripts/check_pr_body.py")
    if not {"data", "browser", "pr-body"} <= set(blocks):
        missing.append("jobs %s" % sorted(blocks))
    kept_n = sum(1 for line in lines if line.startswith("kept "))
    if missing:
        header = "check_guards: FAIL %d removed" % len(missing)
    else:
        header = "check_guards: pr-body added, %d existing guards kept" % kept_n
    return missing, "\n".join([header] + lines)


def _env(body=None):
    env = os.environ.copy()
    env.pop("PR_BODY", None)
    if body is not None:
        env["PR_BODY"] = body
    return env


def run_file(body):
    fd, path = tempfile.mkstemp(prefix="pr-body-", suffix=".md")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return subprocess.run(
            [sys.executable, SCRIPT, path],
            cwd=ROOT,
            env=_env(),
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
        self.assertNotIn("REMOVED", report)

    def test_check_guards_flags_a_removed_step(self):
        with open(WORKFLOW, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("python scripts/check_single_source.py", "python scripts/removed.py", 1)
        missing, report = check_guards(text)
        self.assertTrue(missing, report)
        self.assertIn("REMOVED data: python scripts/check_single_source.py", report)
        self.assertIn("added pr-body: python scripts/check_pr_body.py", report)


if __name__ == "__main__":
    unittest.main()
