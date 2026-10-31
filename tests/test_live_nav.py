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

try:
    from test_turn_by_turn import UNLOCK, START, PUB
except ImportError:
    from tests.test_turn_by_turn import UNLOCK, START, PUB

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
    CLUTTER = {"map": ["#top", "#chips", "#city", "#cNorm", "#cRisk", "#loc"],
               "renter": [".sheet", "header.top", "#goQ"]}

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
        # Max t417u: no town picker, chips, Reset or search while driving.
        for sel in self.CLUTTER[tag]:
            self.assertFalse(pg.is_visible(sel), (tag, sel, "visible during navigation"))
        self.drive_along(pg, ctx, pts, tag)
        i = len(pts) // 3
        a = pts[i]
        b = next((q for q in pts[i:] if hav(a, q) > 40), pts[-1])
        ctx.set_geolocation({"latitude": a[0], "longitude": a[1], "accuracy": 5})
        pg.wait_for_timeout(1200)
        # Headless Chromium mock has no course, so a second fix ahead gives the bearing.
        ctx.set_geolocation({"latitude": b[0], "longitude": b[1], "accuracy": 5})
        pg.wait_for_function("() => document.querySelector('.me-wrap.has-hd')", timeout=8000)
        pg.wait_for_timeout(1200)  # let this fix land (the arrow class may already be on from drive_along)
        c = pg.evaluate(VIEW)
        self.assertGreaterEqual(c[2], 17, tag)
        dot = pg.evaluate("(() => { const r = document.querySelector('.me-wrap').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        mb = pg.locator("#map").bounding_box()
        self.assertLess(abs(dot[0] - (mb["x"] + mb["width"] / 2)), 30, (tag, dot, mb))
        self.assertGreater(dot[1], mb["y"] + mb["height"] * 0.5, (tag, dot, mb))
        pg.screenshot(path=os.path.join(SHOTS, f"livenav-{tag}-follow.png"))
        # Heading-up (Max t412u): the map turned so the road ahead points up; the arrow points straight up.
        st = pg.evaluate("window.gcmFollowState()")
        self.assertTrue(st["headingUp"], (tag, st))
        rb = pg.evaluate("(([a, b]) => GCMFollow.routeBearing(window.gcmFollowRoute(), [a, b]))(%s)" % json.dumps(list(b)))
        if rb is not None:
            d = abs(((st["mapBearing"] - rb) % 360 + 540) % 360 - 180)
            self.assertLess(d, 10, (tag, st, rb))
        self.assertIn("rotate(", pg.evaluate("document.querySelector('.gcm-rot').style.transform"), tag)
        # The arrow's on-screen angle (its --hd minus the map turn) is straight up.
        hd = float(pg.evaluate("getComputedStyle(document.querySelector('.me-wrap')).getPropertyValue('--hd').trim()").replace("deg", ""))
        self.assertLess(abs(((hd - st["mapBearing"]) % 360 + 540) % 360 - 180), 1.5, (tag, hd, st))
        self.assertTrue(pg.is_visible("#navNorth"), tag)
        # Panning pauses follow and goes back to north-up; Recenter brings it back.
        drag(pg, cdp, 200, 320, 0, -120)
        self.assertTrue(pg.is_visible("#navRecenter"), tag)
        pg.wait_for_timeout(300)
        self.assertEqual(pg.evaluate("window.gcmFollowState().mapBearing"), 0, tag)
        self.assertEqual(pg.evaluate("document.querySelector('.gcm-rot').style.transform"), "", tag)
        pg.screenshot(path=os.path.join(SHOTS, f"livenav-{tag}-recenter.png"))
        pg.click("#navRecenter")
        self.assertFalse(pg.is_visible("#navRecenter"), tag)
        pg.wait_for_timeout(300)
        self.assertTrue(pg.evaluate("window.gcmFollowState().headingUp"), tag + ": recenter resumes heading-up")
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

    def dot_xy(self, pg):
        return pg.evaluate("(() => { const r = document.querySelector('.me-wrap').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")

    def drive_along(self, pg, ctx, pts, tag):
        # Max t409u: the dot drove off screen. Drive 30+ fixes along the route; the dot must stay in the
        # central area every time, and follow must never pause on its own.
        mb = pg.locator("#map").bounding_box()
        n = min(36, len(pts))
        step = max(1, len(pts) // n)
        seen = 0
        # An app-driven animated move (route framing, popup autopan) must not count as a user pan.
        pg.evaluate("(() => { const m = window.__gcmMap; m.flyTo(m.getCenter(), m.getZoom() - 2, { duration: 0.6 }); })()")
        for q in pts[: step * n : step][:n]:
            ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
            pg.wait_for_timeout(450)
            x, y = self.dot_xy(pg)
            self.assertFalse(pg.is_visible("#navRecenter"), (tag, "follow paused by itself", seen))
            self.assertTrue(mb["x"] + mb["width"] * 0.25 < x < mb["x"] + mb["width"] * 0.75, (tag, seen, x, y, mb))
            self.assertTrue(mb["y"] + mb["height"] * 0.3 < y < mb["y"] + mb["height"] * 0.9, (tag, seen, x, y, mb))
            seen += 1
        self.assertGreaterEqual(seen, min(30, len(pts)), tag)

    def test_compass_off_when_not_navigating_and_typing_is_cheap(self):
        # Oct 31 2026 lag: the compass listener stayed on after End and repainted the dot ~60x/s.
        ctx = self.ctx()
        pg = ctx.new_page()
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim"), lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        r = pg.evaluate("""async () => {
          DeviceOrientationEvent.requestPermission = () => Promise.resolve('granted');
          const F = GCMFollow.controller({ map: null }); F.start(); await new Promise(r => setTimeout(r, 50));
          const on = F.state().compassOn; F.end();
          window.__navHeadingPaints = 0;
          for (let i = 0; i < 120; i++) dispatchEvent(Object.assign(new Event('deviceorientation'), { webkitCompassHeading: i * 3 }));
          await new Promise(r => setTimeout(r, 100));
          const lt = []; new PerformanceObserver(l => l.getEntries().forEach(e => lt.push(e.duration))).observe({ type: 'longtask' });
          const q = document.getElementById('q'); q.focus();
          for (const ch of 'la jolla shores drive') { q.value += ch; q.dispatchEvent(new Event('input')); await new Promise(r => setTimeout(r, 30)); }
          await new Promise(r => setTimeout(r, 300));
          return { on, offAfterEnd: !F.state().compassOn, paints: window.__navHeadingPaints, maxLong: Math.max(0, ...lt) };
        }""")
        self.assertTrue(r["on"], r)
        self.assertTrue(r["offAfterEnd"], r)
        self.assertEqual(r["paints"], 0, r)
        self.assertLess(r["maxLong"], 50, r)
        ctx.close()

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
        pg.wait_for_timeout(300)
        self.assertEqual(pg.evaluate("window.gcmFollowState().mapBearing"), 0, "End goes back to north-up")
        self.assertFalse(pg.is_visible("#navNorth"))
        self.assertTrue(pg.is_visible(".sheet") and pg.is_visible("#goQ"), "renter controls back after End")
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
        pg.click("#navEnd")
        pg.wait_for_timeout(300)
        for sel in ["#top", "#chips", "#cNorm", "#cRisk", "#loc"]:
            self.assertTrue(pg.is_visible(sel), (sel, "back after End"))
        ctx.close()


if __name__ == "__main__":
    unittest.main()
