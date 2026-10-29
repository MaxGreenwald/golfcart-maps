#!/usr/bin/env python3
"""Pull request bodies need Summary, Evidence, and Merge danger.

Evidence must contain an http(s) URL or command output: a command line
(python, node, bash, sh, npm, npx, pytest, curl, git, make, pip, a
scripts/ path, or a line starting with "$ ") plus an output line (PASS,
FAIL, OK, RESULT, "Ran N tests", "N passed", "exit code N", or unittest's
"... ok").

Text that still matches .github/pull_request_template.md counts as empty.

Usage:
  python scripts/check_pr_body.py body.md
  PR_BODY=... python scripts/check_pr_body.py
Exit 0 on PASS, 1 when a section is missing, empty, or Evidence has neither
command output nor a URL. Each FAIL line names the section.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TEMPLATE = os.path.join(ROOT, ".github", "pull_request_template.md")
REQUIRED = ("Summary", "Evidence", "Merge danger")

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


def evidence_satisfied(text):
    if URL.search(text or ""):
        return True
    lines = (text or "").split("\n")
    has_cmd = any(command_line(line) for line in lines)
    has_out = any(OUTPUT_LINE.match(line) for line in lines)
    return has_cmd and has_out


def problems(body, template=None):
    """Return FAIL reasons. Empty list means the body passes."""
    if template is None:
        template = load_template()
    got = parse_sections(body)
    base = parse_sections(template)
    errs = []
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
        if name == "Evidence" and not evidence_satisfied(content):
            errs.append("Evidence has no command output or URL")
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
    errs = problems(body)
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
