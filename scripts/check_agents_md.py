#!/usr/bin/env python3
"""Fail when AGENTS.md is out of date or too long.

Checks the file (default: AGENTS.md at the repo root):

  1. A repo path cited in the file is not in this checkout. Paths are
     scripts/, tests/, public/, research/, lib/, functions/, ios/, and
     .github/. Globs (`scripts/test_*.py`) and placeholders
     (`public/data/<id>/`) are skipped.
  2. A "branch <name>" note names a branch that is already merged into
     master, or that does not exist. A name counts when it contains a
     hyphen, a slash, or a digit, or is master/main. Git decides: the
     branch tip must resolve (origin/<name> or <name>) and must not be an
     ancestor of origin/master (or master). CI needs every branch tip, so
     the web-ci checkout uses fetch-depth 0.
  3. A line contains a phrase from STALE_PHRASES. The list starts with
     "says beta" (outbound copy is live, not beta).
  4. The file exceeds 16 KiB (16384 bytes).

Each problem line says how to fix it.

Usage:
  python scripts/check_agents_md.py
  python scripts/check_agents_md.py path/to/AGENTS.md
  python scripts/check_agents_md.py --root /repo path/to/AGENTS.md
Exit 0 on PASS, 1 when any check fails, 2 on usage errors.
"""
import os
import re
import subprocess
import sys

LIMIT = 16 * 1024
# Stale wording. Keep "says beta" first. Outbound copy is live, not beta,
# and may say free until after the design-partner period (gtm/rulings.md).
STALE_PHRASES = (
    "says beta",
    'never says "free"',
)
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?:scripts|tests|public|research|lib|functions|ios|\.github)"
    r"/[A-Za-z0-9_./-]*"
)
BRANCH_RE = re.compile(r"\bbranch\s+([A-Za-z0-9][A-Za-z0-9._/-]*)")
TRUNK = {"master", "main"}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_AGENTS = os.path.join(DEFAULT_ROOT, "AGENTS.md")


def git(root, args):
    return subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True,
        text=True,
    )


def resolve_ref(root, name):
    for cand in ("origin/%s" % name, name):
        proc = git(root, ["rev-parse", "--verify", "--quiet", cand])
        if proc.returncode == 0 and proc.stdout.strip():
            return cand
    return None


def master_ref(root):
    for cand in ("origin/master", "master"):
        proc = git(root, ["rev-parse", "--verify", "--quiet", cand])
        if proc.returncode == 0 and proc.stdout.strip():
            return cand
    return None


def branch_state(root, name):
    """Return 'missing', 'merged', 'open', or 'no-master'."""
    ref = resolve_ref(root, name)
    if ref is None:
        return "missing"
    trunk = master_ref(root)
    if trunk is None:
        return "no-master"
    proc = git(root, ["merge-base", "--is-ancestor", ref, trunk])
    if proc.returncode == 0:
        return "merged"
    if proc.returncode == 1:
        return "open"
    return "no-master"


def _in_backticks(text, start):
    return text[:start].count("`") % 2 == 1


def cited_paths(text):
    """Repo-relative files, in order, skipping globs and placeholders.

    A match counts when it sits in backticks, or when the last segment has
    a suffix (public/nav.js). A bare directory phrase such as ios/android/dist
    is not a file citation.
    """
    found = []
    seen = set()
    for match in PATH_RE.finditer(text):
        raw = match.group(0)
        nxt = text[match.end():match.end() + 1]
        if nxt in "*?<":
            continue
        if raw.endswith("/"):
            continue
        path = raw.rstrip(".")
        if not path or any(part == ".." for part in path.split("/")):
            continue
        last = path.rsplit("/", 1)[-1]
        if "." not in last and not _in_backticks(text, match.start()):
            continue
        if path in seen:
            continue
        seen.add(path)
        found.append(path)
    return found


def branch_notes(text):
    """(line, name) for each branch note, first time the name appears."""
    found = []
    seen = set()
    for lineno, line in enumerate(text.splitlines(), 1):
        for match in BRANCH_RE.finditer(line):
            name = match.group(1)
            if name in seen:
                continue
            looks = bool(re.search(r"[-/0-9]", name)) or name.lower() in TRUNK
            if not looks:
                continue
            seen.add(name)
            found.append((lineno, name))
    return found


def stale_hits(text):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        folded = line.casefold()
        for phrase in STALE_PHRASES:
            if phrase.casefold() in folded:
                hits.append((lineno, phrase))
    return hits


def problems(text, root):
    """Return human-readable problems. Empty means the file passes."""
    errs = []
    size = len(text.encode("utf-8"))
    if size > LIMIT:
        errs.append(
            "AGENTS.md is %d bytes, over the %d byte (16 KiB) limit. "
            "Fix: cut lines that duplicate other lines until the file is %d bytes or smaller."
            % (size, LIMIT, LIMIT)
        )
    root_abs = os.path.abspath(root)
    for path in cited_paths(text):
        full = os.path.normpath(os.path.join(root_abs, path))
        inside = full == root_abs or full.startswith(root_abs + os.sep)
        if not inside or not os.path.exists(full):
            errs.append(
                "cited path `%s` is not in this checkout. "
                "Fix: add `%s`, or change the rules table so it names a file that is in the tree."
                % (path, path)
            )
    if branch_notes(text) and git(root, ["rev-parse", "--is-inside-work-tree"]).returncode != 0:
        errs.append(
            "branch notes need a git checkout. "
            "Fix: run this check from the repo. CI must use actions/checkout with fetch-depth: 0 "
            "so every branch tip is present."
        )
    else:
        for lineno, name in branch_notes(text):
            state = branch_state(root, name)
            if state == "merged":
                errs.append(
                    "line %d: branch note '%s' is already merged into master. "
                    "Fix: drop 'branch %s' and say where that check runs on master."
                    % (lineno, name, name)
                )
            elif state == "missing":
                errs.append(
                    "line %d: branch note '%s' does not exist. "
                    "Fix: name a branch that exists and is not merged into master, or drop the note. "
                    "CI must fetch every branch tip (actions/checkout fetch-depth: 0)."
                    % (lineno, name)
                )
            elif state == "no-master":
                errs.append(
                    "line %d: branch note '%s' cannot be checked because this checkout has no master ref. "
                    "Fix: fetch origin with full history (actions/checkout fetch-depth: 0) so merged "
                    "branches can be judged."
                    % (lineno, name)
                )
    for lineno, phrase in stale_hits(text):
        errs.append(
            "line %d: stale phrase %r. "
            "Fix: remove %r. Outbound copy is live, not beta, and may say free until after "
            "the design-partner period."
            % (lineno, phrase, phrase)
        )
    return errs


def checkout_root(agents_path):
    start = os.path.dirname(os.path.abspath(agents_path))
    proc = git(start, ["rev-parse", "--show-toplevel"])
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return start


def parse_args(argv):
    root = None
    path = None
    i = 0
    args = argv[1:]
    while i < len(args):
        if args[i] == "--root":
            if i + 1 >= len(args):
                return None, None, "usage: check_agents_md.py [--root DIR] [AGENTS.md]"
            root = args[i + 1]
            i += 2
            continue
        if args[i].startswith("-"):
            return None, None, "usage: check_agents_md.py [--root DIR] [AGENTS.md]"
        if path is not None:
            return None, None, "usage: check_agents_md.py [--root DIR] [AGENTS.md]"
        path = args[i]
        i += 1
    if path is None:
        path = DEFAULT_AGENTS
    if root is None:
        root = checkout_root(path)
    return path, root, None


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    path, root, err = parse_args(argv)
    if err:
        print(err, file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(
            "FAIL cannot read %s (%s). Fix: pass the path to AGENTS.md in this checkout."
            % (path, exc)
        )
        print("RESULT 1 FAIL")
        return 1
    errs = problems(text, root)
    if errs:
        for item in errs:
            print("FAIL %s" % item)
        print("RESULT %d FAIL" % len(errs))
        return 1
    print("PASS")
    print("RESULT ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
