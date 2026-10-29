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
    return "index.html" if u in ("", "map") else u   # public/index.html is the map; dist serves it at /map


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


INTERNAL_TOKEN = "__GCM_ANALYTICS_INTERNAL__"
# Empty string = a normal production build. sim/tf are for simulator CI and an internal TestFlight, never the public app.
INTERNAL_OK = {"", "sim", "tf", "e2e", "ci", "test", "playwright", "internal", "debug", "notrack"}


def analytics_internal_channel(argv=None):
    a = sys.argv if argv is None else argv
    ch = os.environ.get("GCM_ANALYTICS_INTERNAL", "")
    if "--internal" in a:
        i = a.index("--internal")
        if i + 1 >= len(a):
            raise SystemExit("--internal needs a channel (sim, tf, e2e, ...)")
        ch = a[i + 1]
    if ch not in INTERNAL_OK:
        raise SystemExit("GCM_ANALYTICS_INTERNAL must be empty or one of: " + ", ".join(sorted(INTERNAL_OK - {""})))
    return ch


def stamp_analytics_internal(out, channel=None):
    """Write the internal-analytics channel into dist/track.js. Source public/track.js keeps the token."""
    if channel is None:
        channel = analytics_internal_channel()
    p = os.path.join(out, "track.js")
    with open(p, encoding="utf-8") as f:
        txt = f.read()
    if INTERNAL_TOKEN not in txt:
        raise SystemExit("public/track.js is missing __GCM_ANALYTICS_INTERNAL__")
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt.replace(INTERNAL_TOKEN, channel, 1))


def build(src=os.path.join(ROOT, "public"), out=os.path.join(ROOT, "dist"), native=None):
    """Web: dist/index.html = landing page, dist/map.html = the map (served at /map).
    Native (--native or GCM_NATIVE=1, for the Capacitor iOS/Android webDir): dist/index.html stays the map, no landing page."""
    if native is None: native = os.environ.get("GCM_NATIVE") == "1"
    name = cache_name(read_dir(src))
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(src, out)
    swp = os.path.join(out, "sw.js")
    txt = open(swp, encoding="utf-8").read()
    open(swp, "w", encoding="utf-8").write(stamp(txt, name))
    if not native:
        shutil.copyfile(os.path.join(out, "index.html"), os.path.join(out, "map.html"))
        import seo_landing
        open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(seo_landing.render())
        import seo_pages
        seo_pages.build(out)   # static /<slug> region pages (not precached)
        import seo_towns
        seo_towns.build(out)   # static /<region>/<town> pages from content/towns/ (not precached)
        import seo_compare
        seo_compare.build(out)   # static /compare page (not precached)
        import seo_hubs
        seo_hubs.build(out)   # /golf-cart-maps and /lsv (not precached)
    stamp_analytics_internal(out)
    return name


def main(a):
    if "--name-at" in a:
        print(cache_name(read_rev(a[a.index("--name-at") + 1])))
    elif "--name" in a:
        print(cache_name(read_dir(os.path.join(ROOT, "public"))))
    else:
        print("built dist/ cache", build(native=True if "--native" in a else None), "(native: map is index.html)" if "--native" in a or os.environ.get("GCM_NATIVE") == "1" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
