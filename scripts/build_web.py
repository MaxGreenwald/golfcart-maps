#!/usr/bin/env python3
"""Build the deployable web app: public/ -> dist/, with the service worker cache name stamped.

public/ is the only source of the web app. dist/ is generated (gitignored) and is what gets deployed
to Cloudflare Pages and bundled into the iOS/Android apps (capacitor webDir).

The cache name is 'gcm-' + a hash of every precached file (the PRE list in public/sw.js) plus
sw.js itself. Change any of them and the name changes, so phones always pick up the update.
There is no manual 'gcm-vNN' bump any more; public/sw.js keeps the placeholder below.

Usage:
  build_web.py                 build dist/ and print the cache name
  build_web.py --name          print the cache name for the working tree, build nothing
  build_web.py --name-at REV   print the cache name a git revision would have had (used to audit history)
"""
import hashlib, os, re, shutil, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PLACEHOLDER = "gcm-__CONTENT_HASH__"
NAME_RE = re.compile(r"const C='([^']*)'")
PRE_RE = re.compile(r"const PRE=\[([^\]]*)\]")


def _entry_path(url):
    """'./' and '' are the start page, which the server answers with index.html."""
    u = url[2:] if url.startswith("./") else url
    u = u.lstrip("/")
    return u or "index.html"


def cache_name(read):
    """read(relpath) -> bytes or None, relative to public/. Returns 'gcm-<12 hex>'."""
    sw = read("sw.js")
    if sw is None:
        raise SystemExit("public/sw.js missing")
    sw_txt = sw.decode("utf-8")
    m = PRE_RE.search(sw_txt)
    if not m:
        raise SystemExit("public/sw.js has no 'const PRE=[...]' precache list")
    urls = re.findall(r"'([^']*)'", m.group(1))
    h = hashlib.sha256()
    h.update(NAME_RE.sub("const C='%s'" % PLACEHOLDER, sw_txt, count=1).encode())
    for p in sorted({_entry_path(u) for u in urls}):
        body = read(p)
        h.update(b"\0" + p.encode() + b"\0" + (body if body is not None else b"<missing>"))
    return "gcm-" + h.hexdigest()[:12]


def read_dir(root):
    def read(p):
        f = os.path.join(root, p)
        return open(f, "rb").read() if os.path.isfile(f) else None
    return read


def read_rev(rev):
    def read(p):
        r = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:public/{p}"], capture_output=True)
        return r.stdout if r.returncode == 0 else None
    return read


def stamp(sw_txt, name):
    if PLACEHOLDER not in sw_txt:
        raise SystemExit(f"public/sw.js must contain const C='{PLACEHOLDER}' (no manual gcm-vNN bumps)")
    return sw_txt.replace(PLACEHOLDER, name, 1)


def build(src=os.path.join(ROOT, "public"), out=os.path.join(ROOT, "dist")):
    name = cache_name(read_dir(src))
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(src, out)
    swp = os.path.join(out, "sw.js")
    txt = open(swp, encoding="utf-8").read()
    open(swp, "w", encoding="utf-8").write(stamp(txt, name))
    import seo_compare
    seo_compare.build(out)   # static /compare page (not precached)
    return name


def main(a):
    if "--name-at" in a:
        print(cache_name(read_rev(a[a.index("--name-at") + 1])))
    elif "--name" in a:
        print(cache_name(read_dir(os.path.join(ROOT, "public"))))
    else:
        print("built dist/ cache", build())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
