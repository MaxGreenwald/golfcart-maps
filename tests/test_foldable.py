"""Foldable iPhone (iPhone Duo): the city map and renter page adapt when the phone folds or unfolds.

Sizes are CSS points derived from Apple's published pixels (https://support.apple.com/en-us/148588)
at an assumed 3x scale: outer ~466x678, inner ~626x890. Apple has not published point sizes.
Checks: no horizontal overflow, wide near-square screens get the side panel, the map fills the
viewport after each resize, and a resize in the middle of navigation keeps the route, follow mode
and the blue dot in view. Screenshots go to $SHOTS_DIR (default: a temp dir), never the repo.
"""
import functools
import json
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
    from test_live_nav import _Quiet, _S, hav
    from test_turn_by_turn import UNLOCK, START, PUB
except ImportError:
    from tests.test_live_nav import _Quiet, _S, hav
    from tests.test_turn_by_turn import UNLOCK, START, PUB

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="foldable-")
FOLDED = {"width": 466, "height": 678}
UNFOLDED = {"width": 626, "height": 890}
IPHONE = {"width": 390, "height": 844}
TILES = re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim")
HOOK = """(() => { let h; Object.defineProperty(window, 'L', { configurable: true,
  get() { return h; }, set(v) { h = v; if (v && v.Map && !v.__hooked) { v.__hooked = 1;
    v.Map.addInitHook(function () { window.__gcmMap = this; }); } } }); })()"""
GEOM = """(() => { const r = s => { const e = document.querySelector(s); if (!e) return null;
  const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height] };
  const m = window.__gcmMap, z = m ? m.getSize() : null;
  return { sw: document.documentElement.scrollWidth, iw: innerWidth, ih: innerHeight,
    map: r('#map'), sheet: r('#sheet'), top: r('#top'), mapSize: z ? [z.x, z.y] : null } })()"""


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class Foldable(unittest.TestCase):
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

    def ctx(self, vp):
        c = self.b.new_context(viewport=vp, has_touch=True, is_mobile=True,
                               geolocation=START, permissions=["geolocation"])
        c.add_init_script(HOOK)
        return c

    def fits(self, pg, tag, wide):
        pg.wait_for_timeout(700)
        g = pg.evaluate(GEOM)
        self.assertLessEqual(g["sw"], g["iw"], (tag, "horizontal overflow", g))
        self.assertEqual(g["mapSize"], [g["iw"], g["ih"]], (tag, "map not resized", g))
        sh = g["sheet"]
        self.assertLessEqual(sh[0] + sh[2], g["iw"] + 1, (tag, g))
        if wide:  # side panel: leaves at least 40% of the width for the map
            self.assertLess(sh[2], g["iw"] * 0.6, (tag, "no side panel", g))
        else:
            self.assertGreaterEqual(sh[2], g["iw"] - 1, (tag, "bottom sheet expected", g))
        return g

    def test_city_map_sizes(self):
        for name, vp, wide in [("iphone", IPHONE, False), ("folded", FOLDED, False),
                               ("unfolded", UNFOLDED, True), ("unfolded-land", {"width": 890, "height": 626}, True)]:
            c = self.ctx(vp)
            pg = c.new_page()
            pg.route(TILES, lambda r: r.abort())
            pg.goto(self.base + "/map/pacific-beach")
            pg.wait_for_function("window.ready===true", timeout=120000)
            self.fits(pg, name, wide)
            pg.screenshot(path=os.path.join(SHOTS, f"fold-map-{name}.png"))
            c.close()

    def follow_ok(self, pg, ctx, pts, i, tag):
        q = pts[i]
        ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
        pg.wait_for_timeout(900)
        self.assertTrue(pg.is_visible("#navEnd"), (tag, "navigation ended"))
        self.assertFalse(pg.is_visible("#navRecenter"), (tag, "follow paused by resize"))
        r = pg.evaluate("(() => { const r = document.querySelector('.me-wrap').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        mb = pg.locator("#map").bounding_box()
        self.assertTrue(mb["x"] < r[0] < mb["x"] + mb["width"] and mb["y"] < r[1] < mb["y"] + mb["height"], (tag, r, mb))

    def test_city_map_fold_unfold_mid_navigation(self):
        ctx = self.ctx(FOLDED)
        pg = ctx.new_page()
        pg.route(TILES, lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        pg.evaluate("fakeLocate(%f,%f)" % (START["latitude"], START["longitude"]))
        pg.evaluate("window._pll = L.latLng(32.7966, -117.2545); popSet('to')")
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        pg.click("#navStart")
        pts = pg.evaluate("window._liveNav.pts")
        n0 = len(pts)
        self.follow_ok(pg, ctx, pts, len(pts) // 4, "folded")
        pg.screenshot(path=os.path.join(SHOTS, "fold-nav-1-folded.png"))
        for k, (vp, name, wide) in enumerate([(UNFOLDED, "unfolded", True), (FOLDED, "refolded", False)]):
            pg.set_viewport_size(vp)
            self.fits(pg, name, wide)
            self.assertEqual(len(pg.evaluate("window._liveNav.pts")), n0, (name, "route lost or rerouted"))
            self.assertEqual(pg.evaluate("window.__navReroutes || 0"), 0, name)
            self.follow_ok(pg, ctx, pts, len(pts) * (k + 2) // 4, name)
            pg.screenshot(path=os.path.join(SHOTS, f"fold-nav-{k + 2}-{name}.png"))
        ctx.close()

    def test_renter_page_fold_unfold_mid_navigation(self):
        ctx = self.ctx(FOLDED)
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(UNLOCK)))
        pg.route(TILES, lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector(".xcard")
        pg.click(".goopen")
        pg.wait_for_timeout(1500)
        pg.fill("#goQ", "Crystal Pier")
        pg.wait_for_selector("#goSugg .sugg", timeout=15000)
        pg.click("#goSugg .sugg >> nth=0")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        pg.click("#navStart")
        pts = pg.evaluate("GCMNavDebug().pts")
        n0 = len(pts)
        self.follow_ok(pg, ctx, pts, len(pts) // 4, "renter-folded")
        pg.screenshot(path=os.path.join(SHOTS, "fold-renter-1-folded.png"))
        for k, (vp, name) in enumerate([(UNFOLDED, "renter-unfolded"), (FOLDED, "renter-refolded")]):
            pg.set_viewport_size(vp)
            pg.wait_for_timeout(700)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), vp["width"], name)
            z = pg.evaluate("(() => { const s = window.__gcmMap.getSize(), r = document.getElementById(window.__gcmMap.getContainer().id).getBoundingClientRect(); return [s.x, s.y, Math.round(r.width), Math.round(r.height)] })()")
            self.assertEqual(z[:2], z[2:], (name, "map not resized to its box"))
            self.assertEqual(len(pg.evaluate("GCMNavDebug().pts")), n0, (name, "route lost or rerouted"))
            self.follow_ok(pg, ctx, pts, len(pts) * (k + 2) // 4, name)
            pg.screenshot(path=os.path.join(SHOTS, f"fold-{k + 2}-{name}.png"))
        ctx.close()


if __name__ == "__main__":
    unittest.main()
