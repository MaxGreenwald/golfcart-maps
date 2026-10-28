"""Open every visible region's map page (/map/<slug>) and confirm it loads the right REG.

Not named test_town_pages.py: `python -m unittest discover -s tests` imports by
basename, and earlier tests put scripts/ at the front of sys.path. That name
loaded this file instead of tests/test_town_pages.py and failed the unit job
on `import playwright` (Playwright is only installed in the browser job).

Usage: URL=https://golfcartmap.com/map/ python3 scripts/test_town_map_pages.py
"""
from playwright.sync_api import sync_playwright
import json, os, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BASE = os.environ.get("URL", "http://localhost:8765/map/").rstrip("/") + "/"
regs = [r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json"))) if not r.get("hidden")]
fails = []


def ck(n, c, x=""):
    print(("PASS " if c else "FAIL ") + n, x)
    if not c:
        fails.append(n)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: fails.append("js " + str(e)[:120]))
    for r in regs:
        slug, rid = r["slug"], r["id"]
        url = BASE + slug
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_function("window.ready===true && window.REG", timeout=120000)
            got = pg.evaluate("REG.id")
            ck(f"map/{slug} -> {rid}", got == rid, f"got={got}")
            # city chip present (map shell, not SEO landing)
            ck(f"map/{slug} has city chip", pg.locator("#city").count() == 1)
        except Exception as e:
            ck(f"map/{slug} loads", False, str(e)[:160])
    b.close()

print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails[:8]}{'...' if len(fails)>8 else ''}")
sys.exit(1 if fails else 0)
