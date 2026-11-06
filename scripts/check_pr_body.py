#!/usr/bin/env python3
"""Pull request bodies need Summary, Evidence, and Merge danger.

Evidence must contain an http(s) URL or command output: a command line
(python, node, bash, sh, npm, npx, pytest, curl, git, make, pip, a
scripts/ path, or a line starting with "$ ") plus an output line (PASS,
FAIL, OK, RESULT, "Ran N tests", "N passed", "exit code N", or unittest's
"... ok"). A line from scripts/evidence.sh counts as the command:

    EVIDENCE sha=<12 hex> exit=<code> cmd=<command>

When PR_HEAD_SHA is set (CI sets it to the pull request head), Evidence
must also contain an EVIDENCE stamp or a GitHub Actions run URL for that
commit. A stamp from an older push does not match. A command that only
prints its own result (python -c "print('PASS')", echo PASS, printf PASS,
and the same shape of one-liner) is not evidence.

Usage:
  python scripts/check_pr_body.py body.md
  PR_BODY=... PR_HEAD_SHA=<head sha> python scripts/check_pr_body.py
Exit 0 on PASS, 1 when a section is missing, empty, Evidence has neither
command output nor a URL, the stamp does not match PR_HEAD_SHA, or a
command only prints its own result. Each FAIL line names the section.
The stamp and print-only failures say: rerun scripts/evidence.sh on HEAD.
"""
import os
import re
import sys
from urllib.parse import unquote, urlparse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TEMPLATE = os.path.join(ROOT, ".github", "pull_request_template.md")
REQUIRED = ("Summary", "Evidence", "Merge danger")
RERUN = "rerun scripts/evidence.sh on HEAD"

HEADING = re.compile(
    r"(?i)^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?"
    r"(summary|evidence|merge[ \t]+danger)"
    r"(?:\*\*)?[ \t]*:?[ \t]*$"
)
URL = re.compile(r"https?://[^\s<>\]\)\"']+", re.I)
COMMAND = re.compile(
    r"(?i)^(?:\$\s+\S|(?:python3?|node|bash|sh|npm|npx|pytest|curl|git|make|pip3?)\b|"
    r"(?:\./|\.\./|scripts/)\S)"
)
OUTPUT_LINE = re.compile(
    r"(?i)^(?:"
    r"[ \t]*PASS\b.*|"
    r"[ \t]*FAIL(?:ED)?\b.*|"
    r"[ \t]*OK[ \t]*\.?[ \t]*|"
    r"[ \t]*RESULT\b.*|"
    r"[ \t]*Ran\s+\d+\s+tests\b.*|"
    r"[ \t]*\d+\s+(?:passed|failed)\b.*|"
    r"[ \t]*exit code\s*[:=]?\s*\d+[ \t]*|"
    r".*\.\.\.\s+(?:ok|FAIL|ERROR|skipped)[ \t]*"
    r")$"
)
STAMP_RE = re.compile(
    r"(?i)^[ \t]*EVIDENCE\s+sha=([0-9a-f]{12,64})\s+exit=(\d+)\s+cmd=(.*?)\s*$"
)
SHA_RE = re.compile(r"[0-9a-f]{12,64}")
RESULT_WORD = re.compile(r"(?i)\b(?:PASS|FAIL(?:ED)?|OK|RESULT)\b")
ECHO_LINE = re.compile(r"(?i)^(?:\$\s+)?(?:echo|printf)\b")
SHELL_C = re.compile(r"(?is)^(?:bash|sh)\s+-c\s+(.+)$")
PY_C = re.compile(r"(?i)(?:^|\s)-c(?:\s|$|['\"])")
NODE_E = re.compile(r"(?i)(?:^|\s)-[ep](?:\s|$|['\"])")
NODE_LOG = re.compile(r"(?i)console\.(?:log|info|error|warn)\s*\(")
PY_PRINT = re.compile(r"(?i)\bprint\s*\(")
ACTIONS_RUN = re.compile(r"(?i)/actions/runs/\d+")
ACTIONS_CHECKS = re.compile(r"(?i)/commit/[0-9a-f]{12,64}/checks(?:/|$)")


def canonical(raw):
    key = re.sub(r"\s+", " ", raw).strip().casefold()
    for name in REQUIRED:
        if name.casefold() == key:
            return name
    return None


def parse_sections(body):
    """Map each required heading to the text under it. Headings inside fences are ignored."""
    text = (body or "").replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.split("\n")
    found = []
    fence = False
    for i, line in enumerate(lines):
        if re.match(r"^[ \t]*```", line):
            fence = not fence
            continue
        if fence:
            continue
        match = HEADING.match(line)
        if not match:
            continue
        name = canonical(match.group(1))
        if name:
            found.append((i, name))
    sections = {}
    for idx, (line_i, name) in enumerate(found):
        end = found[idx + 1][0] if idx + 1 < len(found) else len(lines)
        chunk = "\n".join(lines[line_i + 1:end])
        sections[name] = sections[name] + "\n" + chunk if name in sections else chunk
    return sections


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip().casefold()


def load_template():
    try:
        with open(TEMPLATE, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def command_line(line):
    return bool(COMMAND.match(line.strip()))


def _unwrap_shell(cmd):
    cmd = re.sub(r"^\$\s+", "", (cmd or "").strip())
    match = SHELL_C.match(cmd)
    if not match:
        return cmd, False
    inner = match.group(1).strip()
    if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in ("'", '"'):
        inner = inner[1:-1]
    return inner.strip(), True


def is_print_only(cmd, depth=0):
    """True when the command's only job is to print PASS/FAIL/OK/RESULT."""
    if depth > 3:
        return False
    inner, wrapped = _unwrap_shell(cmd)
    if wrapped:
        return is_print_only(inner, depth + 1)
    if re.match(r"(?i)^(?:echo|printf)\b", inner):
        return RESULT_WORD.search(inner) is not None
    if re.match(r"(?i)^python3?(?:\s|$)", inner) and PY_C.search(inner):
        return PY_PRINT.search(inner) is not None and RESULT_WORD.search(inner) is not None
    if re.match(r"(?i)^node(?:\s|$)", inner) and NODE_E.search(inner):
        return NODE_LOG.search(inner) is not None and RESULT_WORD.search(inner) is not None
    return False


def iter_commands(text):
    for line in (text or "").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        stamp = STAMP_RE.match(line)
        if stamp:
            cmd = stamp.group(3).strip()
            if cmd:
                yield cmd
            continue
        if command_line(stripped) or ECHO_LINE.match(stripped):
            yield re.sub(r"^\$\s+", "", stripped)


def print_only_commands(text):
    found = []
    seen = set()
    for cmd in iter_commands(text):
        key = cmd.strip()
        if key in seen:
            continue
        seen.add(key)
        if is_print_only(key):
            found.append(key)
    return found


def evidence_satisfied(text):
    if URL.search(text or ""):
        return True
    lines = (text or "").split("\n")
    has_cmd = any(command_line(line) for line in lines)
    if not has_cmd:
        for line in lines:
            stamp = STAMP_RE.match(line)
            if not stamp:
                continue
            cmd = stamp.group(3).strip()
            if cmd and (command_line(cmd) or not is_print_only(cmd)):
                has_cmd = True
                break
    has_out = any(OUTPUT_LINE.match(line) for line in lines)
    return has_cmd and has_out


def _sha_pair_matches(stamp, head):
    stamp = (stamp or "").strip().lower()
    head = (head or "").strip().lower()
    if SHA_RE.fullmatch(stamp) is None or SHA_RE.fullmatch(head) is None:
        return False
    return head.startswith(stamp) or stamp.startswith(head)


def stamp_shas(text):
    found = []
    for line in (text or "").split("\n"):
        match = STAMP_RE.match(line)
        if match:
            found.append(match.group(1).lower())
    return found


def is_actions_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    if host not in ("github.com", "www.github.com"):
        return False
    if ACTIONS_RUN.search(parsed.path):
        return True
    if ACTIONS_CHECKS.search(parsed.path):
        return True
    return False


def url_matches_head(url, head):
    blob = unquote(url or "").lower()
    head = (head or "").strip().lower()
    if SHA_RE.fullmatch(head) is None:
        return False
    if head in blob:
        return True
    short = head[:12]
    return re.search(r"(?<![0-9a-f])" + re.escape(short) + r"(?![0-9a-f])", blob) is not None


def evidence_matches_head(text, head):
    """True when some stamp or Actions URL is for this head. Empty head skips the check."""
    head = (head or "").strip().lower()
    if not head:
        return True
    if SHA_RE.fullmatch(head) is None:
        return False
    for stamp in stamp_shas(text):
        if _sha_pair_matches(stamp, head):
            return True
    for url in URL.findall(text or ""):
        if is_actions_url(url) and url_matches_head(url, head):
            return True
    return False


def freshness_error(head):
    shown = (head or "").strip()
    if SHA_RE.fullmatch(shown.lower() or ""):
        label = shown.lower()
    else:
        label = shown[:64] or "(empty)"
    return (
        "Evidence has no EVIDENCE stamp or GitHub Actions run URL matching HEAD %s: %s"
        % (label, RERUN)
    )


def problems(body, template=None, head_sha=""):
    """Return FAIL reasons. Empty list means the body passes."""
    if template is None:
        template = load_template()
    got = parse_sections(body)
    base = parse_sections(template)
    errs = []
    head = (head_sha or "").strip()
    for name in REQUIRED:
        if name not in got:
            errs.append("Missing section: %s" % name)
            continue
        content = got[name]
        placeholder = base.get(name, "")
        placeholder_norm = norm(placeholder)
        if norm(content) == "" or (placeholder_norm and norm(content) == placeholder_norm):
            errs.append("Empty section: %s" % name)
            continue
        if name != "Evidence":
            continue
        if print_only_commands(content):
            errs.append("Evidence command only prints its own result: %s" % RERUN)
        elif not evidence_satisfied(content):
            errs.append("Evidence has no command output or URL")
        if head and not evidence_matches_head(content, head):
            errs.append(freshness_error(head))
    return errs


def load_body(argv, env, stdin):
    if len(argv) > 2:
        print("usage: check_pr_body.py [body.md]", file=sys.stderr)
        return None
    if len(argv) == 2:
        with open(argv[1], encoding="utf-8") as handle:
            return handle.read()
    if "PR_BODY" in env:
        return env.get("PR_BODY") or ""
    if stdin.isatty():
        print("usage: check_pr_body.py [body.md]   or set PR_BODY", file=sys.stderr)
        return None
    return stdin.read()


def main(argv=None, env=None, stdin=None):
    argv = list(sys.argv if argv is None else argv)
    env = os.environ if env is None else env
    stdin = sys.stdin if stdin is None else stdin
    body = load_body(argv, env, stdin)
    if body is None:
        return 2
    errs = problems(body, head_sha=env.get("PR_HEAD_SHA") or "")
    if errs:
        for err in errs:
            print("FAIL %s" % err)
        print("RESULT %d FAIL" % len(errs))
        return 1
    print("PASS")
    print("RESULT ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
