"""Outside our mapped towns (Max t590u/t591u): a US spot with no town data still gets the map, search, location and a route,
with one warning that we have no golf cart/LSV speed data there. Mapped towns are unchanged (no warning, no general router).
The general router (Valhalla) is mocked with tests/fixtures/valhalla_boise.json, so CI never calls the public server."""
import json, os
from playwright.sync_api import sync_playwright
from _check import ck, fail, finish
URL = os.environ.get("URL", "http://localhost:8765/map/")
SHOTS_DIR = os.environ.get("SHOTS_DIR", "/tmp/")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
BOISE = open(os.path.join(ROOT, "tests/fixtures/valhalla_boise.json")).read()
MAP = URL.rstrip("/").rsplit("/map", 1)[0] + "/map/"
WARN = "We don\u2019t have golf cart and LSV speed data for this area yet, so this route isn\u2019t checked against local rules. Check posted speed limits and local laws."

def page(p, lat, lng, path="", down=False):
    b = p.chromium.launch()
    ctx = b.new_context(**p.devices["iPhone 13"], geolocation={"latitude": lat, "longitude": lng}, permissions=["geolocation"])
    calls = []
    def valhalla(route):
        calls.append(route.request.post_data)
        if state["down"]: route.abort()
        else: route.fulfill(status=200, content_type="application/json", body=BOISE, headers={"access-control-allow-origin": "*"})
    state = {"down": down}
    ctx.route("https://valhalla1.openstreetmap.de/**", valhalla)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: fail("js error " + str(e)))
    pg.goto(MAP + path)
    pg.wait_for_function("window.ready===true", timeout=120000)
    pg.wait_for_timeout(800)
    return b, pg, calls, state

def routed(pg, ms=15000):
    try: pg.wait_for_function("getState().routed===true", timeout=ms); return True
    except Exception: return False

T = lambda pg, sel: pg.inner_text(sel) if pg.locator(sel).count() else ""
with sync_playwright() as p:
    # 1. Boise: opens there (location already shared), GPS start, tap a destination -> route + warning
    b, pg, calls, _ = page(p, 43.6150, -116.2023)
    ck("boise: opens in the general area, not San Diego", pg.evaluate("REG.id") == "other", pg.evaluate("REG.id"))
    ck("boise: city chip says Other US area", T(pg, "#cityLbl") == "Other US area", T(pg, "#cityLbl"))
    ck("boise: banner says we have no speed data here", "speed data for this area yet" in T(pg, "#sub"), T(pg, "#sub"))
    ck("boise: Legal only / Risky chips hidden", not pg.is_visible("#cNorm") and not pg.is_visible("#cRisk"))
    pg.evaluate("setSnap('collapsed');0"); pg.click("#loc"); pg.wait_for_timeout(1500)
    ck("boise: GPS fills From", pg.evaluate("getState().from&&getState().from.me") is True)
    pg.evaluate("map.fire('click',{latlng:L.latLng(43.6080,-116.1930)});0")
    ck("boise: route returned", routed(pg))
    ck("boise: one general-router call", len(calls) == 1, len(calls))
    ck("boise: warning shown with the exact copy", T(pg, "#anyWarn") == "\u26a0\ufe0f " + WARN, T(pg, "#anyWarn"))
    ck("boise: route has distance and street steps", pg.evaluate("window.lastRoute.mi") > 0.3 and "West Main Street" in T(pg, "#steps"), T(pg, "#steps")[:120])
    ck("boise: no risky marks", pg.evaluate("window.lastRoute.risky.length") == 0)
    ck("boise: route line drawn", pg.evaluate("routeLines.length") == 3)
    ck("boise: turn-by-turn steps build", pg.evaluate("navStepsFor(window._lastDetail,'B').steps.length") >= 2)
    ck("boise: tips do not promise road speeds", "speed" not in T(pg, "#help"), T(pg, "#help"))
    pg.screenshot(path=SHOTS_DIR + "screenshot-anywhere-boise.png")
    # a non-US tap keeps a polite line and no route call
    pg.click("#reset"); pg.evaluate("map.fire('click',{latlng:L.latLng(43.65,-79.38)});0"); pg.wait_for_timeout(500)
    ck("toronto: polite US-only line, no pin", "covers the US only" in T(pg, "#help") and not pg.evaluate("getState().from"), T(pg, "#help"))
    # both ends inside a mapped town -> that town's legal-road router, no warning
    r = pg.evaluate("testRoute([32.8506,-117.2717],[32.8305,-117.2805])")
    ck("back in San Diego: town router, no warning", pg.evaluate("REG.id") == "sd" and r and not pg.locator("#anyWarn").count() and len(calls) == 1, str(r))
    ck("back in San Diego: Legal only chip back", pg.is_visible("#cNorm"))
    b.close()

    # 2. Austin deep link (Horseshoe Bay is the nearest town, 40 mi away): the linked spot, not Horseshoe Bay
    b, pg, calls, _ = page(p, 30.2672, -97.7431, "?lat=30.2672&lon=-97.7431&z=16")
    ck("austin link: general area at the linked spot", pg.evaluate("REG.id") == "other" and abs(pg.evaluate("map.getCenter().lat") - 30.2672) < 0.01, pg.evaluate("[REG.id,map.getCenter()]"))
    ck("austin link: no town slug in the address", "horseshoebay" not in pg.evaluate("location.pathname"), pg.evaluate("location.pathname"))
    b.close()

    # 3. General router unreachable -> clear message + Retry; Retry works once it is back
    b, pg, calls, state = page(p, 43.6150, -116.2023, down=True)
    pg.evaluate("setSnap('collapsed');0"); pg.click("#loc"); pg.wait_for_timeout(1500)
    pg.evaluate("map.fire('click',{latlng:L.latLng(43.6080,-116.1930)});0"); pg.wait_for_timeout(2500)
    ck("router down: says so, offers Retry", "Check your connection" in T(pg, "#sub") and pg.locator("#anyRetry").count() == 1, T(pg, "#sub"))
    state["down"] = False; pg.click("#anyRetry")
    ck("router down: Retry routes", routed(pg))
    b.close()

    # 4. Mapped town (San Diego): exactly as before. No general router, no warning
    b, pg, calls, _ = page(p, 32.8506, -117.2717)
    pg.evaluate("setSnap('collapsed');0"); pg.click("#loc"); pg.wait_for_timeout(1500)
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0")
    ck("sd: route returned", routed(pg, 60000))
    ck("sd: town router, no warning, no general call", pg.evaluate("REG.id") == "sd" and not pg.locator("#anyWarn").count() and not calls, T(pg, "#sub"))
    ck("sd: legal summary as before", T(pg, "#sub").startswith("All on roads") or "risky" in T(pg, "#sub").lower(), T(pg, "#sub"))
    ck("sd: Legal only / Risky chips shown", pg.is_visible("#cNorm") and pg.is_visible("#cRisk"))
    pg.screenshot(path=SHOTS_DIR + "screenshot-anywhere-sd.png")
    pg.click("#reset"); pg.evaluate("map.fire('click',{latlng:L.latLng(32.50,-117.03)});0"); pg.wait_for_timeout(500)
    ck("sd: Tijuana tap keeps the old outside-the-map line", T(pg, "#help").startswith("\u26a0\ufe0f That spot is outside the map") and not calls, T(pg, "#help"))
    b.close()
finish()
