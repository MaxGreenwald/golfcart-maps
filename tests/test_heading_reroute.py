"""Max t433u: driving away from the route (the opposite way) must reroute once, from where you are and
the way you are going: "Continue on <street>", then the turns, never "turn around" right away, and no
new reroute every fix while you follow the fresh route. Standing still keeps any-direction rerouting
(covered by test_live_nav's reroute check).

Screenshots go to $SHOTS_DIR (default: a temp dir), never the repo root.
"""
import functools
import math
import os
import re
import tempfile
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from test_live_nav import _S, _Quiet, PUB
except ImportError:
    from tests.test_live_nav import _S, _Quiet, PUB

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="hdreroute-")
ME = (32.7973, -117.24764)   # mid-block on Hornblend Street; the route to DEST heads west along it
DEST = "32.7930, -117.2560"
NO_NET = re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim")


def brg(a, b):
    k = math.pi / 180
    y = math.sin((b[1] - a[1]) * k) * math.cos(b[0] * k)
    x = math.cos(a[0] * k) * math.sin(b[0] * k) - math.sin(a[0] * k) * math.cos(b[0] * k) * math.cos((b[1] - a[1]) * k)
    return (math.atan2(y, x) / k + 360) % 360


def diff(a, b):
    return abs(((a - b) % 360 + 540) % 360 - 180)


def hav(a, b):
    k = math.pi / 180
    x = math.sin((b[0] - a[0]) * k / 2) ** 2 + math.cos(a[0] * k) * math.cos(b[0] * k) * math.sin((b[1] - a[1]) * k / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(x))


def along(path, step):
    """Points every `step` metres along a polyline."""
    out = [path[0]]
    for a, b in zip(path, path[1:]):
        d = hav(a, b)
        n = max(1, int(d // step))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class HeadingReroute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = os.environ.get("GCM_BASE") or "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.pw = sync_playwright().start()
        cls.b = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def test_wrong_way_reroutes_once_forward(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=2,
                                 geolocation={"latitude": ME[0], "longitude": ME[1], "accuracy": 5}, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route(NO_NET, lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        pg.evaluate("fakeLocate(%f,%f)" % ME)
        pg.evaluate("window._pll = L.latLng(%s); popSet('to')" % DEST)
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        pts0 = pg.evaluate("window._liveNav.pts")
        b_route = brg(pts0[0], pts0[min(3, len(pts0) - 1)])
        pg.click("#navStart")
        pg.wait_for_timeout(800)
        # Hornblend Street east of here, in order (the wrong way).
        east = pg.evaluate("""(() => { const out = [];
          for (const s of D.segs) { if ((D.names[s[0]] || '') !== 'Hornblend Street') continue;
            for (const p of s[7]) if (p[0] > %f && p[0] < %f && Math.abs(p[1] - %f) < 0.002) out.push([p[1], p[0]]); }
          out.sort((a, b) => a[1] - b[1]); return out; })()""" % (ME[1] - 0.00001, ME[1] + 0.006, ME[0]))
        self.assertGreater(len(east), 2, east)
        self.assertGreater(diff(brg(ME, east[-1]), b_route), 120, "test drives against the route")
        drive = along([ME] + [tuple(p) for p in east], 9)
        reroutes0 = pg.evaluate("window.__navReroutes || 0")
        k = 0
        # Drive the wrong way, about 9 m per 0.6 s (~15 m/s cap is fine for the logic), until a reroute lands.
        while k < len(drive) and pg.evaluate("window.__navReroutes || 0") == reroutes0:
            ctx.set_geolocation({"latitude": drive[k][0], "longitude": drive[k][1], "accuracy": 5})
            pg.wait_for_timeout(600)
            k += 1
        self.assertEqual(pg.evaluate("window.__navReroutes || 0"), reroutes0 + 1, "a reroute happened while driving away")
        pg.wait_for_function("() => !window._navRerouting && window._liveNav", timeout=30000)
        pg.wait_for_timeout(800)
        course = pg.evaluate("window._navRerouteCourse")
        self.assertIsNotNone(course, "reroute knew the course")
        self.assertLess(diff(course, brg(ME, east[-1])), 40, course)
        nav = pg.evaluate("window._liveNav")
        here = drive[k - 1]
        first = nav["steps"][0]["text"]
        self.assertTrue(first.startswith("Continue on Hornblend") or first.startswith("Continue"), first)
        self.assertLess(diff(brg(nav["pts"][0], nav["pts"][1]), course), 45, "new route starts the way you drive")
        self.assertLess(hav(tuple(nav["pts"][0]), here), 25, "new route starts where you are")
        pg.screenshot(path=os.path.join(SHOTS, "reroute-wrong-way.png"))
        # Keep driving on the new route: no more reroutes.
        r1 = pg.evaluate("window.__navReroutes || 0")
        follow = along([tuple(p) for p in nav["pts"]], 9)[:14]
        for q in follow:
            ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(1500)
        self.assertEqual(pg.evaluate("window.__navReroutes || 0"), r1, "no reroute while following the fresh route")
        pg.screenshot(path=os.path.join(SHOTS, "reroute-wrong-way-following.png"))
        # CarPlay plans through testRoute on the same page: a heading makes it start ahead too.
        fwd = pg.evaluate("(async () => { await testRoute([%f,%f],[%s],false,105); return {ahead: !!window._lastDetail.ahead, road: D.names[window._lastDetail.legs[0].s[0]]}; })()" % (ME[0], ME[1], DEST))
        self.assertEqual(fwd, {"ahead": True, "road": "Hornblend Street"})
        still = pg.evaluate("(async () => { await testRoute([%f,%f],[%s]); return !!window._lastDetail.ahead; })()" % (ME[0], ME[1], DEST))
        self.assertFalse(still, "no heading: any direction")
        ctx.close()


if __name__ == "__main__":
    unittest.main()
