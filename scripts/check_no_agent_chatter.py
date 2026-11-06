#!/usr/bin/env python3
"""Fail when maintainer-facing code or a pull request body keeps conversation residue.

Scans .js, .ts, .py, and .swift. Skips research/, archive/, and build or
dependency trees (dist/, node_modules/, __pycache__/). Markdown and other
docs are outside that set. With --pr-body, scans the PR_BODY environment
variable (the open pull request description) and does not walk the tree
unless file paths are also passed.

The deny list is short. Each phrase is stored in pieces so this file does
not contain a full phrase and can scan itself.

Usage:
  python scripts/check_no_agent_chatter.py
  python scripts/check_no_agent_chatter.py path/to/file.py
  PR_BODY=... python scripts/check_no_agent_chatter.py --pr-body
Exit 0 when clean, 1 on any hit. A hit prints FAIL and a RESULT line.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EXTS = {".js", ".ts", ".py", ".swift"}
SKIP_DIRS = {"research", "archive", "dist", "node_modules", "__pycache__", ".git"}

# Joined at runtime. Keep the pieces split so a full phrase never appears here.
PIECES = (
    ("Used", " to ", "be"),
    ("as ", "discussed"),
    ("per ", "the ", "agent"),
    ("the ", "agent ", "said"),
    ("in ", "this ", "conversation"),
    ("TODO ", "from ", "chat"),
    ("after ", "Max ", "asked"),
    ("previously ", "this ", "was"),
)


def compile_patterns():
    compiled = []
    for index, parts in enumerate(PIECES, start=1):
        phrase = "".join(parts)
        compiled.append((index, re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)))
    return compiled


def iter_source_files(root):
    """Source files under root, skipping research/, archive/, and build trees."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIP_DIRS)
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in EXTS:
                found.append(os.path.join(dirpath, name))
    return found


def display_path(path, root=None):
    abs_path = os.path.abspath(path)
    if root is None:
        return abs_path
    abs_root = os.path.abspath(root)
    if abs_path == abs_root or abs_path.startswith(abs_root + os.sep):
        return os.path.relpath(abs_path, abs_root)
    return abs_path


def scan_text(label, text, patterns):
    hits = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for index, pattern in patterns:
            if pattern.search(line):
                hits.append(f"{label}:{line_no}: chat residue #{index}")
    return hits


def scan_path(path, patterns, root=None):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return scan_text(display_path(path, root), handle.read(), patterns)


def main(argv=None):
    args = []
    scan_body = False
    for arg in sys.argv[1:] if argv is None else argv:
        if arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        if arg == "--pr-body":
            scan_body = True
        else:
            args.append(arg)

    patterns = compile_patterns()
    hits = []
    described = []
    if args:
        for path in args:
            if not os.path.isfile(path):
                hits.append(f"{path}: not a file")
                continue
            root = ROOT if os.path.abspath(path).startswith(os.path.abspath(ROOT) + os.sep) else None
            hits.extend(scan_path(path, patterns, root=root))
        noun = "file" if len(args) == 1 else "files"
        described.append(f"{len(args)} {noun}")
    elif not scan_body:
        files = iter_source_files(ROOT)
        for path in files:
            hits.extend(scan_path(path, patterns, root=ROOT))
        described.append(f"{len(files)} files")
    if scan_body:
        hits.extend(scan_text("<pr-body>", os.environ.get("PR_BODY") or "", patterns))
        described.append("pr body")

    for hit in hits:
        print("FAIL", hit)
    if hits:
        print("RESULT", f"{len(hits)} FAIL")
        return 1
    print("RESULT", "ALL PASS (" + ", ".join(described) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
