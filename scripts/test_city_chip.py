"""City picker is a chip in the top chip row (first chip), A-Z, San Diego default, picking a city loads + re-centers.
Settings has no City row and the sheet header has no city label. URL/saved-choice/back-forward behavior unchanged.
Run: URL=http://localhost:8765/ python3 scripts/test_city_chip.py   (exit 1 on failure)
On a deployed URL (pages.dev / golfcartmap.com) it also checks /sandiego, /tybee and an unknown path (/carlsbad -> San Diego).
SHOTS: if set, a folder for city-chip-main.png (no screenshot otherwise)."""
import os, sys
from playwright.sync_api import sync_playwright
U = os.environ.get("URL", "http://localhost:8765/").rstrip("/"); OUT = os.environ.get("SHOTS", "")
LOCAL = "localhost" in U or "127.0.0.1" in U
# verify_live map suites set URL=.../map; don't prefix /map again
IS_MAP_URL = U.endswith("/map")
fails = []
def ck(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
READY = "window.ready===true&&window.REG"
def map_path(path):
    if LOCAL:
        return path
    if IS_MAP_URL:
        if path.startswith("/map/") or path == "/map":
            return path[4:] or "/"
        if path.startswith("/?"):
            return "/" + path  # /?r=x -> /?r=x under .../map
        return path
    if path.startswith("/map"):
        return path
    if path.startswith("/?"):
        return "/map" + path
    if path == "/":
        return "/map"
    return "/map" + path
def go(pg, path):
    pg.goto(U + map_path(path)); pg.wait_for_function(READY, timeout=120000); pg.wait_for_timeout(800)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(**p.devices["iPhone 13"]); pg = ctx.new_page()
    pg.on("pageerror", lambda e: fails.append("js error " + str(e)))
    go(pg, "/")
    ck("no path, nothing saved: default is San Diego", pg.evaluate("REG.id") == "sd", pg.evaluate("REG.id"))
    ids = pg.evaluate("[...document.querySelectorAll('#chips>*')].map(e=>e.id||e.className).join()")
    ck("city chip is first in the top chip row", ids == "chip city,cNorm,cRisk,useme,reset", ids)
    ck("picker select lives in the city chip", pg.evaluate("!!document.querySelector('#chips .chip.city select#city')"))
    ck("Settings has no City row", pg.evaluate("!document.querySelector('#setPanel #city,#setPanel .crow')"))
    ck("no city label in the sheet header", pg.evaluate("!document.querySelector('#cityNow,#shead #cityLbl')"))
    ck("chip shows San Diego", pg.inner_text("#cityLbl") == "San Diego" and pg.evaluate("$('city').value") == "sd", pg.inner_text("#cityLbl"))
    names = pg.eval_on_selector_all("#city option", "o=>o.map(x=>x.text.replace(/ \\(beta\\)$/,''))")
    ck("options are A-Z", names == sorted(names, key=str.casefold) and len(names) > 10, names[:6])
    r = pg.evaluate("(()=>{const ch=[...document.querySelectorAll('#chips>*')].filter(e=>e.offsetParent);const R=ch.map(e=>e.getBoundingClientRect());return {right:Math.max(...R.map(x=>x.right)),rows:new Set(R.map(x=>Math.round(x.top))).size,vw:innerWidth}})()")
    ck("chip row fits on one row at phone width", r["right"] <= r["vw"] - 8 and r["rows"] == 1, r)
    if OUT:
        pg.evaluate("setSnap('collapsed');0"); pg.wait_for_timeout(500); pg.screenshot(path=os.path.join(OUT, "city-chip-main.png"))
    pg.select_option("#city", "tybee"); pg.wait_for_function("window.ready===true&&REG.id==='tybee'", timeout=120000); pg.wait_for_timeout(800)
    c = pg.evaluate("(()=>{const c=map.getCenter(),b=REG.bbox;return [c.lat,c.lng,c.lat>=b[0]&&c.lat<=b[2]&&c.lng>=b[1]&&c.lng<=b[3]]})()")
    ck("chip pick loads Tybee and re-centers the map", c[2], c)
    ck("chip label follows", pg.inner_text("#cityLbl") == "Tybee Island", pg.inner_text("#cityLbl"))
    ck("URL is /tybee and the pick is saved", pg.evaluate("location.pathname") in ("/tybee", "/map/tybee") and pg.evaluate("localStorage.getItem('gcm-region')") == "tybee")
    pg.go_back(); pg.wait_for_function("window.ready===true&&REG.id==='sd'", timeout=120000)
    ck("back button returns to San Diego", pg.evaluate("REG.id") == "sd" and pg.evaluate("$('city').value") == "sd")
    pg.go_forward(); pg.wait_for_function("window.ready===true&&REG.id==='tybee'", timeout=120000)
    ck("forward button returns to Tybee", pg.evaluate("REG.id") == "tybee")
    go(pg, "/")
    ck("saved city restores on a bare visit", pg.evaluate("REG.id") == "tybee", pg.evaluate("REG.id"))
    go(pg, "/?r=naples")
    ck("?r= link still wins", pg.evaluate("REG.id") == "naples")
    if not LOCAL:   # region paths need Cloudflare _redirects
        go(pg, "/map/sandiego"); ck("/map/sandiego opens San Diego", pg.evaluate("REG.id") == "sd")
        go(pg, "/map/tybee"); ck("/map/tybee opens Tybee", pg.evaluate("REG.id") == "tybee")
        r = pg.goto(U + map_path("/map/carlsbad"))
        if r and r.ok:
            pg.wait_for_function(READY, timeout=120000); ck("/carlsbad (unknown path) falls back to San Diego", pg.evaluate("REG.id") == "sd", pg.evaluate("REG.id"))
        else: print("INFO /carlsbad not served:", r and r.status)
    ctx.close(); b.close()
print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
