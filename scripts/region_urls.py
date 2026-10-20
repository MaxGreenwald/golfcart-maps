#!/usr/bin/env python3
"""City URLs come from one place: the "slug" of each region in public/data/regions.json.
This writes everything derived from it: public/_redirects (Cloudflare rewrites /<slug> to the app),
the city entries of public/sitemap.xml, and the SLUG map in public/app.js.
(Peachtree City and Hilton Head were in the picker without a URL, so their links 404'd on reload.)

  region_urls.py           rewrite the three files from regions.json
  region_urls.py --check   exit 1 if any of them is out of date (run by tests/test_region_urls.py in CI)"""
import json, os, re, sys, time
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
P = lambda *a: os.path.join(ROOT, "public", *a)
SITE = "https://golfcartmap.com"
SLUG_RE = re.compile(r"^[a-z0-9]+$")
APP_SLUG = re.compile(r"const SLUG=\{[^}]*\};")


def regions():
    rs = json.load(open(P("data", "regions.json"), encoding="utf-8"))
    bad = [r["id"] for r in rs if not SLUG_RE.match(r.get("slug", ""))]
    if bad: raise SystemExit(f"regions without a valid slug (lowercase letters/digits): {bad}")
    seen = {}
    for r in rs:
        if r["slug"] in seen: raise SystemExit(f"duplicate slug {r['slug']}: {seen[r['slug']]} and {r['id']}")
        seen[r["slug"]] = r["id"]
    return rs


def want(rs, cur):
    red = "".join(f"/{r['slug']} / 200\n/{r['slug']}/ / 200\n" for r in rs)
    sm = cur["sitemap"]
    old = dict(re.findall(r"<loc>" + re.escape(SITE) + r"/([a-z0-9]+)</loc><lastmod>([^<]*)</lastmod>", sm))
    today = time.strftime("%Y-%m-%d")
    head = sm[:sm.index("<urlset")]
    keep = [u for u in re.findall(r"<url>.*?</url>", sm) if re.search(r"<loc>" + re.escape(SITE) + r"/(privacy|compare)?</loc>", u)]
    city = [f"<url><loc>{SITE}/{r['slug']}</loc><lastmod>{old.get(r['slug'], today)}</lastmod><changefreq>weekly</changefreq></url>" for r in rs]
    sm2 = head + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(keep + city) + "</urlset>\n"
    app = cur["app"]
    slug = "const SLUG={" + ",".join(f"'{r['id']}':'{r['slug']}'" for r in rs) + "};"
    if not APP_SLUG.search(app): raise SystemExit("public/app.js has no 'const SLUG={...};' line")
    return {"redirects": red, "sitemap": sm2, "app": APP_SLUG.sub(lambda _: slug, app, count=1)}


FILES = {"redirects": P("_redirects"), "sitemap": P("sitemap.xml"), "app": P("app.js")}


def main(a):
    cur = {k: open(f, encoding="utf-8").read() for k, f in FILES.items()}
    new = want(regions(), cur)
    stale = [k for k in FILES if new[k] != cur[k]]
    if "--check" in a:
        for k in stale: print("STALE", os.path.relpath(FILES[k], ROOT), "- run scripts/region_urls.py")
        print("RESULT", "ALL PASS (city URLs match regions.json)" if not stale else f"{len(stale)} STALE")
        return 1 if stale else 0
    for k in stale: open(FILES[k], "w", encoding="utf-8").write(new[k]); print("wrote", os.path.relpath(FILES[k], ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
