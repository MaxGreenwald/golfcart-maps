#!/usr/bin/env python3
"""public/ is the only source of the web app. Fail if a committed copy of a public/ file lives anywhere else.

Generated copies (dist/, ios/App/App/public/, android/app/src/main/assets/public/) are build output:
they must be gitignored, never committed. A committed copy drifts: it is how the iPhone build once
shipped a web app 42 commits behind the site.

Checks every tracked file outside public/:
  1. path: nothing under dist/ or a Capacitor web bundle dir (ios/App/App/public/, android/.../assets/public/)
  2. content: no byte-identical copy of a public/ code/page file (.js .html .css .json .webmanifest .txt .xml)
     anywhere else, and no file named like a public/ entry point (app.js, sw.js, carplay.js, ...) outside public/.
Usage: check_single_source.py [--rev REV]   (default: the index/HEAD of this checkout)"""
import hashlib, os, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUNDLE_DIRS = ("dist/", "ios/App/App/public/", "android/app/src/main/assets/public/")
CODE_EXT = (".js", ".html", ".css", ".json", ".webmanifest", ".txt", ".xml")
# Files outside public/ that may legitimately share a basename with a public/ file.
ALLOW = {
    "package.json", "package-lock.json",          # npm, not the web app
    "lib/pay.js",                                 # server-side Stripe helpers for functions/api, not public/pay.js
}


def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, check=True).stdout


def tracked(rev):
    """[(path, blob_sha)] for every tracked file."""
    out = git("ls-tree", "-r", rev) if rev else git("ls-files", "-s")
    rows = []
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        parts = meta.split()
        sha = parts[2] if rev else parts[1]
        rows.append((path, sha))
    return rows


def problems(rows):
    pub = {p[len("public/"):]: s for p, s in rows if p.startswith("public/")}
    # entry points: top-level public/ code files (data tiles are excluded from the name check; their
    # content check still applies)
    names = {os.path.basename(p) for p in pub if "/" not in p and p.endswith(CODE_EXT)}
    pub_code_blobs = {s: p for p, s in pub.items() if p.endswith(CODE_EXT)}
    bad = []
    for path, sha in rows:
        if path.startswith("public/"):
            continue
        if path.startswith(BUNDLE_DIRS):
            bad.append(f"{path}: generated bundle dir is committed (gitignore it; it is built from public/)")
        elif sha in pub_code_blobs:
            bad.append(f"{path}: byte-identical copy of public/{pub_code_blobs[sha]}")
        elif os.path.basename(path) in names and os.path.basename(path) not in ALLOW and path not in ALLOW:
            bad.append(f"{path}: looks like a copy of public/{os.path.basename(path)} (edit public/ instead)")
    return bad


def main(a):
    rev = a[a.index("--rev") + 1] if "--rev" in a else None
    bad = problems(tracked(rev))
    for b in bad:
        print("FAIL", b)
    print("RESULT", "ALL PASS (public/ is the only copy of the web app)" if not bad else f"{len(bad)} FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
