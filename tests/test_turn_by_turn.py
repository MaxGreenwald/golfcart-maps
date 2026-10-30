"""Renter turn-by-turn: Start experience shows a maneuver banner that updates with GPS,
an expandable step list, a mute toggle, reroute when off route, and arrival with a next-stop offer.
Picking a ride folds the other rides away until 'All experiences'.

Screenshots go to $SHOTS_DIR (default: a temp dir), never the repo root.
"""
import functools
import http.server
import json
import os
import re
import socketserver
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="tbt-")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if re.fullmatch(r"/p/[^/]+(?:/go)?/?", path):
            path = "/p.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


START = {"latitude": 32.7980, "longitude": -117.2466}  # Garnet Ave, Pacific Beach
UNLOCK = {
    "code": "TEST123",
    "shop": {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd", "blurb": "", "logo_url": "", "color": ""},
    "experiences": [
        {"id": "e1", "title": "Sunset Run to Windansea", "description": "Pier to cove", "stops": [
            {"label": "Crystal Pier Entrance", "lat": 32.7966, "lon": -117.2545, "note": ""},
            {"label": "Tourmaline Surf Park", "lat": 32.8055, "lon": -117.2610, "note": ""},
            {"label": "Windansea Beach", "lat": 32.8306, "lon": -117.2810, "note": ""}]},
        {"id": "e2", "title": "Bay Loop", "description": "Mission Bay", "stops": [
            {"label": "Fanuel Park", "lat": 32.7905, "lon": -117.2435, "note": ""}]},
    ],
    "affiliates": [],
}


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class TurnByTurn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.pw = sync_playwright().start()
        cls.b = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def page(self, w=390, h=844):
        ctx = self.b.new_context(viewport={"width": w, "height": h}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(UNLOCK)))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector(".xcard")
        return ctx, pg

    def test_focus_one_experience(self):
        for w, h, tag in ((390, 844, "mobile"), (1280, 800, "desktop")):
            ctx, pg = self.page(w, h)
            pg.click(".xcard[data-ex='e1']")
            self.assertTrue(pg.is_visible(".xcard[data-ex='e1']"))
            self.assertFalse(pg.is_visible(".xcard[data-ex='e2']"), tag)
            self.assertTrue(pg.is_visible("#allEx"), tag)
            pg.screenshot(path=os.path.join(SHOTS, f"tbt-focus-{tag}.png"))
            pg.click("#allEx")
            self.assertTrue(pg.is_visible(".xcard[data-ex='e2']"), tag)
            self.assertFalse(pg.is_visible("#allEx"), tag)
            ctx.close()

    def test_simulated_drive(self):
        ctx, pg = self.page()
        pg.click(".xcard[data-ex='e1']")
        pg.click("#startEx")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        route = pg.evaluate("GCMNavDebug()")
        self.assertIsNotNone(route)
        steps = route["steps"]
        self.assertGreaterEqual(len(steps), 3, steps)
        self.assertEqual(steps[-1]["text"], "Arrive at Crystal Pier Entrance")
        self.assertTrue(any(s["kind"] == "turn" and s["name"] for s in steps), [s["text"] for s in steps])
        pts = route["pts"]
        # Banner leads with an "In N ft, ..." maneuver at the start.
        seen = []
        n = len(pts)
        for k, i in enumerate((0, n // 4, n // 2, 3 * n // 4)):
            lat, lon = pts[i]
            ctx.set_geolocation({"latitude": lat, "longitude": lon})
            pg.wait_for_timeout(1500)
            t = pg.inner_text("#navText")
            seen.append(t)
            pg.screenshot(path=os.path.join(SHOTS, f"tbt-drive-{k}.png"))
        self.assertTrue(any(re.match(r"^In [\d.]+ (ft|mi), ", t) for t in seen), seen)
        self.assertGreater(len(set(seen)), 1, seen)
        # Step list expands.
        pg.click("#navListBtn")
        self.assertTrue(pg.is_visible("#navSteps"))
        self.assertEqual(pg.locator("#navSteps li").count(), len(steps))
        pg.screenshot(path=os.path.join(SHOTS, "tbt-steps.png"))
        pg.click("#navListBtn")
        # Mute toggles.
        pg.click("#navMute")
        self.assertEqual(pg.get_attribute("#navMute", "aria-pressed"), "true")
        pg.click("#navMute")
        # Off route twice in a row reroutes on legal roads (new route from the off point).
        before = len(pts)
        off = {"latitude": pts[n // 2][0] + 0.0015, "longitude": pts[n // 2][1] + 0.0015}
        for _ in range(2):
            ctx.set_geolocation(off)
            pg.wait_for_timeout(1500)
        pg.wait_for_function("() => { const r = GCMNavDebug(); return r && Math.abs(r.pts[0][0] - %f) < 0.002 }" % off["latitude"], timeout=20000)
        pg.screenshot(path=os.path.join(SHOTS, "tbt-reroute.png"))
        # Arrive at stop 1, then offer stop 2.
        end = pg.evaluate("GCMNavDebug().pts.slice(-1)[0]")
        ctx.set_geolocation({"latitude": end[0], "longitude": end[1]})
        pg.wait_for_function("() => /arrived at Crystal Pier/.test(document.getElementById('navText').textContent)", timeout=10000)
        self.assertTrue(pg.is_visible("#navGo"))
        self.assertIn("stop 2", pg.inner_text("#navGo"))
        pg.screenshot(path=os.path.join(SHOTS, "tbt-arrived.png"))
        pg.click("#navGo")
        pg.wait_for_function("() => { const r = GCMNavDebug(); return r && r.stop === 1 }", timeout=20000)
        self.assertIn("Stop 2/3", pg.inner_text("#nextLabel"))
        self.assertTrue(pg.evaluate("(window.__navSaid||[]).length") > 0)
        ctx.close()

    def test_navigate_somewhere_else(self):
        for w, h, tag in ((390, 844, "mobile"), (1280, 800, "desktop")):
            ctx, pg = self.page(w, h)
            pg.route("https://photon.komoot.io/**", lambda r: r.abort())
            self.assertFalse(pg.is_visible("#fullMap"), tag)
            self.assertTrue(pg.is_visible("#goTop") or pg.is_visible(".goopen"), tag)
            pg.click(".goopen")
            self.assertTrue(pg.is_visible("#goQ"), tag)
            self.assertFalse(pg.is_visible(".xcard"), tag)
            self.assertFalse(pg.is_visible("#startEx"), tag)
            # Search a street from the loaded SD road data, pick it, get a legal route + banner.
            pg.wait_for_timeout(1500)
            pg.fill("#goQ", "Crystal Pier")
            pg.wait_for_selector("#goSugg .sugg", timeout=15000)
            pg.click("#goSugg .sugg >> nth=0")
            pg.wait_for_selector("#navBanner.show", timeout=30000)
            self.assertRegex(pg.inner_text("#goNote"), r"mi (on legal golf cart roads|· ⚠️)")
            route = pg.evaluate("GCMNavDebug()")
            self.assertEqual(route["stop"], -1)
            self.assertTrue(route["steps"][-1]["text"].startswith("Arrive at "), route["steps"][-1])
            pg.screenshot(path=os.path.join(SHOTS, f"tbt-free-{tag}.png"))
            # Risky toggle reroutes; Legal only is the default.
            self.assertEqual(pg.get_attribute("#goMode [data-mode=legal]", "aria-pressed"), "true")
            pg.click("#goMode [data-mode=risky]")
            self.assertEqual(pg.get_attribute("#goMode [data-mode=risky]", "aria-pressed"), "true")
            pg.wait_for_timeout(1500)
            # Drop a pin by tapping the map routes there instead.
            pg.click("#goMode [data-mode=legal]")
            box = pg.locator("#map").bounding_box()
            pg.mouse.click(box["x"] + box["width"] * 0.75, box["y"] + box["height"] * 0.4)
            pg.wait_for_function("() => /Dropped pin/.test(document.getElementById('goQ').value)", timeout=10000)
            # Arrive.
            pg.wait_for_function("() => { const r = GCMNavDebug(); return r && r.steps.slice(-1)[0].text === 'Arrive at Dropped pin' }", timeout=30000)
            end = pg.evaluate("GCMNavDebug().pts.slice(-1)[0]")
            ctx.set_geolocation({"latitude": end[0], "longitude": end[1]})
            pg.wait_for_function("() => /arrived at Dropped pin/.test(document.getElementById('navText').textContent)", timeout=10000)
            # Back to experiences.
            pg.click("#goBack")
            self.assertTrue(pg.is_visible(".xcard[data-ex='e1']"), tag)
            self.assertFalse(pg.is_visible("#navBanner"), tag)
            ctx.close()


if __name__ == "__main__":
    unittest.main()
