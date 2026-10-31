"""Live navigation: routes open as a preview with Start; pinch and drag in preview keep the user's view;
Start follows the blue dot (with a heading arrow), a drag pauses follow and shows Recenter, and staying
off the route for ~5 s reroutes from where you are. Covers the renter page and the city map.

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

from test_turn_by_turn import UNLOCK, START, PUB

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="livenav-")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if re.fullmatch(r"/p/[^/]+(?:/go)?/?", path):
            path = "/p.html"
        elif re.fullmatch(r"/map(/[^/]*)?/?", path):
            path = "/index.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def hav(a, b):
    import math
    k = math.pi / 180
    x = math.sin((b[0] - a[0]) * k / 2) ** 2 + math.cos(a[0] * k) * math.cos(b[0] * k) * math.sin((b[1] - a[1]) * k / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(x))


def touch(cdp, kind, pts):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})


def pinch_out(pg, cdp, cx, cy):
    touch(cdp, "touchStart", [(cx - 30, cy), (cx + 30, cy)])
    for k in range(1, 11):
        d = 30 + k * 9
        touch(cdp, "touchMove", [(cx - d, cy), (cx + d, cy)])
        pg.wait_for_timeout(20)
    touch(cdp, "touchEnd", [])
    pg.wait_for_timeout(600)


def drag(pg, cdp, x, y, dx, dy):
    touch(cdp, "touchStart", [(x, y)])
    for k in range(1, 11):
        touch(cdp, "touchMove", [(x + dx * k / 10, y + dy * k / 10)])
        pg.wait_for_timeout(20)
    touch(cdp, "touchEnd", [])
    pg.wait_for_timeout(600)


VIEW = "(() => { const m = window.__gcmMap; const c = m.getCenter(); return [c.lat, c.lng, m.getZoom()] })()"


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class LiveNav(unittest.TestCase):
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

    def ctx(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                                 geolocation=START, permissions=["geolocation"])
        # Expose the Leaflet map for view assertions (read-only).
        ctx.add_init_script("""(() => { let h; Object.defineProperty(window, 'L', { configurable: true,
          get() { return h; }, set(v) { h = v; if (v && v.Map && !v.__hooked) { v.__hooked = 1;
            v.Map.addInitHook(function () { window.__gcmMap = this; }); } } }); })()""")
        return ctx

    def assert_view_kept(self, pg, before, tag):
        pg.wait_for_timeout(2500)  # a snap back would land within this
        after = pg.evaluate(VIEW)
        self.assertNotEqual([round(v, 5) for v in before], [round(v, 5) for v in after], tag)
        return after

    def drive_checks(self, pg, ctx, cdp, pts, tag):
        # Start: follow mode, End and arrow.
        pg.click("#navStart")
        self.assertTrue(pg.is_visible("#navEnd"), tag)
        self.assertFalse(pg.is_visible("#navStart"), tag)
        i = len(pts) // 3
        a = pts[i]
        b = next((q for q in pts[i:] if hav(a, q) > 40), pts[-1])
        ctx.set_geolocation({"latitude": a[0], "longitude": a[1], "accuracy": 5})
        pg.wait_for_timeout(1200)
        # Headless Chromium mock has no course, so a second fix ahead gives the bearing.
        ctx.set_geolocation({"latitude": b[0], "longitude": b[1], "accuracy": 5})
        pg.wait_for_function("() => document.querySelector('.me-wrap.has-hd')", timeout=8000)
        c = pg.evaluate(VIEW)
        self.assertGreaterEqual(c[2], 17, tag)
        dot = pg.evaluate("(() => { const r = document.querySelector('.me-wrap').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        mb = pg.locator("#map").bounding_box()
        self.assertLess(abs(dot[0] - (mb["x"] + mb["width"] / 2)), 30, (tag, dot, mb))
        self.assertGreater(dot[1], mb["y"] + mb["height"] * 0.5, (tag, dot, mb))
        pg.screenshot(path=os.path.join(SHOTS, f"livenav-{tag}-follow.png"))
        # Panning pauses follow; Recenter brings it back.
        drag(pg, cdp, 200, 320, 0, -120)
        self.assertTrue(pg.is_visible("#navRecenter"), tag)
        pg.screenshot(path=os.path.join(SHOTS, f"livenav-{tag}-recenter.png"))
        pg.click("#navRecenter")
        self.assertFalse(pg.is_visible("#navRecenter"), tag)
        # Off route ~170 m and staying there: reroute after ~5 s, from here.
        off = {"latitude": b[0] + 0.0015, "longitude": b[1] + 0.0015, "accuracy": 5}
        ctx.set_geolocation(off)
        pg.wait_for_timeout(2500)
        self.assertEqual(pg.evaluate("window.__navReroutes || 0"), 0, tag + ": rerouted too soon")
        pg.wait_for_function("() => (window.__navReroutes || 0) >= 1", timeout=15000)
        pg.wait_for_timeout(2500)
        self.assertIn("Rerouting", pg.evaluate("window.__navSaid || []"), tag)
        pg.screenshot(path=os.path.join(SHOTS, f"livenav-{tag}-reroute.png"))
        return off

    def test_renter_preview_start_follow_reroute(self):
        ctx = self.ctx()
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(UNLOCK)))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector(".xcard")
        cdp = ctx.new_cdp_session(pg)
        pg.click(".goopen")
        pg.wait_for_timeout(1500)
        pg.fill("#goQ", "Crystal Pier")
        pg.wait_for_selector("#goSugg .sugg", timeout=15000)
        pg.click("#goSugg .sugg >> nth=0")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        # Preview: Start shown, no End, no voice yet.
        self.assertTrue(pg.is_visible("#navStart"))
        self.assertFalse(pg.is_visible("#navEnd"))
        self.assertEqual(pg.evaluate("(window.__navSaid||[]).length"), 0)
        pg.screenshot(path=os.path.join(SHOTS, "livenav-renter-preview.png"))
        cx, cy = 195, 300  # visible map above the dock
        v0 = pg.evaluate(VIEW)
        pinch_out(pg, cdp, cx, cy)
        v1 = self.assert_view_kept(pg, v0, "renter pinch")
        self.assertGreater(v1[2], v0[2], "pinch zooms in")
        drag(pg, cdp, cx, cy, 80, 60)
        self.assert_view_kept(pg, v1, "renter pan")
        # Steps list: tapping a step zooms to it, and the view stays.
        pg.click("#navListBtn")
        pg.click("#navSteps li >> nth=1")
        pg.wait_for_timeout(800)
        v2 = pg.evaluate(VIEW)
        self.assertEqual(v2[2], 18)
        pg.wait_for_timeout(2500)
        self.assertEqual([round(x, 5) for x in v2], [round(x, 5) for x in pg.evaluate(VIEW)])
        pg.screenshot(path=os.path.join(SHOTS, "livenav-renter-step.png"))
        pg.click("#navListBtn")
        pts = pg.evaluate("GCMNavDebug().pts")
        off = self.drive_checks(pg, ctx, cdp, pts, "renter")
        pg.wait_for_function("() => { const r = GCMNavDebug(); return r && Math.abs(r.pts[0][0] - %f) < 0.002 }" % off["latitude"], timeout=20000)
        self.assertTrue(pg.is_visible("#navEnd"), "still navigating after reroute")
        pg.click("#navEnd")
        self.assertTrue(pg.is_visible("#navStart"))
        ctx.close()

    def test_city_map_preview_start_follow_reroute(self):
        ctx = self.ctx()
        pg = ctx.new_page()
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim"), lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        cdp = ctx.new_cdp_session(pg)
        pg.evaluate("fakeLocate(%f,%f)" % (START["latitude"], START["longitude"]))
        pg.evaluate("window._pll = L.latLng(32.7966, -117.2545); popSet('to')")
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        self.assertTrue(pg.is_visible("#navStart"))
        pg.wait_for_timeout(1500)
        pg.screenshot(path=os.path.join(SHOTS, "livenav-map-preview.png"))
        v0 = pg.evaluate(VIEW)
        pinch_out(pg, cdp, 195, 300)
        v1 = self.assert_view_kept(pg, v0, "map pinch")
        self.assertGreater(v1[2], v0[2])
        drag(pg, cdp, 195, 300, 70, 50)
        self.assert_view_kept(pg, v1, "map pan")
        pts = pg.evaluate("window._liveNav.pts")
        off = self.drive_checks(pg, ctx, cdp, pts, "map")
        pg.wait_for_function("() => window._liveNav && Math.abs(window._liveNav.pts[0][0] - %f) < 0.002" % off["latitude"], timeout=30000)
        self.assertTrue(pg.is_visible("#mapNav"))
        ctx.close()


if __name__ == "__main__":
    unittest.main()
