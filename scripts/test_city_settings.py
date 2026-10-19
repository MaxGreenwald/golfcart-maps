"""City picker lives in Settings (not the top bar), A-Z, San Diego default, switching city in Settings loads + re-centers.
Run: URL=http://localhost:8765/ python3 scripts/test_city_settings.py   (exit 1 on failure)
On a deployed URL (pages.dev / golfcartmap.com) it also checks /sandiego, /tybee and an unknown path (/carlsbad -> San Diego).
SHOTS: folder for city-settings-main.png / city-settings-settings.png (default /tmp/)."""
import os, re, sys
from playwright.sync_api import sync_playwright
U = os.environ.get("URL", "http://localhost:8765/").rstrip("/"); OUT = os.environ.get("SHOTS", "/tmp/")
LOCAL = "localhost" in U or "127.0.0.1" in U
fails = []
def ck(n, c, x=""): print(("PASS " if c else "FAIL ") + n, x); c or fails.append(n)
READY = "window.ready===true&&window.REG"
def go(pg, path):
    pg.goto(U + path); pg.wait_for_function(READY, timeout=120000); pg.wait_for_timeout(800)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(**p.devices["iPhone 13"]); pg = ctx.new_page()
    pg.on("pageerror", lambda e: fails.append("js error " + str(e)))
    go(pg, "/")
    ck("no path, nothing saved: default is San Diego", pg.evaluate("REG.id") == "sd", pg.evaluate("REG.id"))
    ck("top bar has no city picker", pg.evaluate("!document.querySelector('#top #city,#chips select,#chips .city')"))
    ck("chip row is just the mode chips", pg.evaluate("[...document.querySelectorAll('#chips>*')].map(e=>e.id).join()") == "cNorm,cRisk,useme,reset")
    ck("picker is in Settings", pg.evaluate("!!document.querySelector('#setPanel select#city')"))
    ck("current city shown in the sheet header", pg.is_visible("#cityNow") and pg.inner_text("#cityLbl") == "San Diego", pg.inner_text("#cityNow"))
    names = pg.eval_on_selector_all("#city option", "o=>o.map(x=>x.text.replace(/ \\(beta\\)$/,''))")
    ck("options are A-Z", names == sorted(names, key=str.casefold) and len(names) > 10, names[:6])
    ck("San Diego selected", pg.evaluate("$('city').value") == "sd")
    pg.evaluate("setSnap('collapsed');0"); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT + "city-settings-main.png")
    pg.click("#cityNow"); pg.wait_for_timeout(800)
    ck("tapping the header city opens Settings", pg.evaluate("getSnap()") == "full" and pg.evaluate("(()=>{const r=$('city').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()"))
    sel_w = pg.evaluate("(()=>{const e=$('city'),cs=getComputedStyle(e),cx=document.createElement('canvas').getContext('2d');cx.font=cs.font;return Math.max(...[...e.options].map(o=>cx.measureText(o.text).width))+parseFloat(cs.paddingLeft)+parseFloat(cs.paddingRight)-e.clientWidth})()")
    ck("longest city name fits the Settings select", sel_w <= 0.5, f"overflow {sel_w:.1f}px")
    pg.screenshot(path=OUT + "city-settings-settings.png")
    # pick a city in Settings
    pg.select_option("#city", "tybee"); pg.wait_for_function("window.ready===true&&REG.id==='tybee'", timeout=120000); pg.wait_for_timeout(800)
    c = pg.evaluate("(()=>{const c=map.getCenter(),b=REG.bbox;return [c.lat,c.lng,c.lat>=b[0]&&c.lat<=b[2]&&c.lng>=b[1]&&c.lng<=b[3]]})()")
    ck("Settings pick loads Tybee and re-centers the map", c[2], c)
    ck("header city follows", pg.inner_text("#cityLbl") == "Tybee Island", pg.inner_text("#cityLbl"))
    ck("URL is /tybee and the pick is saved", pg.evaluate("location.pathname") == "/tybee" and pg.evaluate("localStorage.getItem('gcm-region')") == "tybee")
    ck("sheet tucks away to show the new map", pg.evaluate("getSnap()") == "collapsed")
    go(pg, "/")
    ck("saved city restores on a bare visit", pg.evaluate("REG.id") == "tybee", pg.evaluate("REG.id"))
    go(pg, "/?r=naples")
    ck("?r= link still wins", pg.evaluate("REG.id") == "naples")
    if not LOCAL:   # region paths need Cloudflare _redirects
        go(pg, "/sandiego"); ck("/sandiego opens San Diego", pg.evaluate("REG.id") == "sd")
        go(pg, "/tybee"); ck("/tybee opens Tybee", pg.evaluate("REG.id") == "tybee")
        r = pg.goto(U + "/carlsbad")
        if r and r.ok:
            pg.wait_for_function(READY, timeout=120000); ck("/carlsbad (unknown path) falls back to San Diego", pg.evaluate("REG.id") == "sd", pg.evaluate("REG.id"))
        else: print("INFO /carlsbad not served:", r and r.status)
    ctx.close(); b.close()
print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
