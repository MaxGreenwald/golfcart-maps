"""Max t430u (TestFlight build 35): two bugs at the start of navigation.

1. Start must turn the map at once so the road ahead points up, even standing still, and a finger
   left flagged as down (tapping the map to pick the destination) must not pause follow at Start.
2. A photo picked in Settings > Your map icon during the session must show on the nav puck, on the
   city map and on the renter page.

Runs in Chromium and, when installed, WebKit (the iOS app is a WKWebView).
Screenshots go to $SHOTS_DIR (default: a temp dir), never the repo root.
"""
import functools
import json
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
    from test_live_nav import _S, _Quiet, START, PUB, UNLOCK
    from test_map_icon import big_png
except ImportError:
    from tests.test_live_nav import _S, _Quiet, START, PUB, UNLOCK
    from tests.test_map_icon import big_png

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="navstart-")
SOUTH_DEST = "32.7930, -117.2560"  # from START the route first heads south (about 167 deg)
NO_NET = re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim")


def angdiff(a, b):
    return abs(((a - b) % 360 + 540) % 360 - 180)


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class NavStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.pw = sync_playwright().start()
        cls.browsers = {"chromium": cls.pw.chromium.launch()}
        try:
            cls.browsers["webkit"] = cls.pw.webkit.launch()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls):
        for b in cls.browsers.values():
            b.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def ctx(self, name):
        kw = dict(viewport={"width": 390, "height": 844}, has_touch=True, device_scale_factor=2, geolocation=START)
        if name == "chromium":
            kw.update(is_mobile=True, permissions=["geolocation"])
        ctx = self.browsers[name].new_context(**kw)
        # Expose the Leaflet map (read-only), as test_live_nav does.
        ctx.add_init_script("""(() => { let h; Object.defineProperty(window, 'L', { configurable: true,
          get() { return h; }, set(v) { h = v; if (v && v.Map && !v.__hooked) { v.__hooked = 1;
            v.Map.addInitHook(function () { window.__gcmMap = this; }); } } }); })()""")
        return ctx

    def city_preview(self, ctx):
        pg = ctx.new_page()
        pg.route(NO_NET, lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        pg.evaluate("fakeLocate(%f,%f)" % (START["latitude"], START["longitude"]))
        pg.evaluate("window._pll = L.latLng(%s); popSet('to')" % SOUTH_DEST)
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        pg.wait_for_timeout(800)
        return pg

    def test_start_standing_still_turns_route_up(self):
        for name in self.browsers:
            with self.subTest(browser=name):
                ctx = self.ctx(name)
                pg = self.city_preview(ctx)
                rb = pg.evaluate("GCMFollow.routeBearing(window._liveNav, [%f, %f])" % (START["latitude"], START["longitude"]))
                self.assertIsNotNone(rb)
                self.assertLess(angdiff(rb, 180), 30, ("route heads south", rb))
                # A finger flagged as down on the map that never came back up (the touch ended on an element
                # that left the page), as when tapping the map to pick the destination on iPhone.
                pg.evaluate("document.getElementById('map').dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}))")
                pg.click("#navStart")
                pg.wait_for_timeout(2000)
                st = pg.evaluate("window.gcmFollowState()")
                self.assertTrue(st["following"], (name, "Start must not come up paused", st))
                self.assertFalse(pg.is_visible("#navRecenter"), name)
                self.assertTrue(st["headingUp"], (name, st))
                self.assertLess(angdiff(st["mapBearing"], rb), 10, (name, st, rb))
                # On screen, the route 60 m ahead is straight above the puck.
                xy = pg.evaluate("""(() => {
                  const r = window._liveNav;
                  const dot = document.querySelector('.me-wrap').getBoundingClientRect();
                  const p = GCMFollow.pointAt(r, Math.min(60, r.cum ? r.cum[r.cum.length - 1] : 60));
                  return { dot: [dot.x + dot.width / 2, dot.y + dot.height / 2], p };
                })()""")
                ahead = pg.evaluate("""(([lat, lng]) => {
                  const mk = L.marker([lat, lng], { icon: L.divIcon({ className: 'probe', iconSize: [2, 2] }) }).addTo(window.__gcmMap);
                  const r = mk.getElement().getBoundingClientRect(); mk.remove(); return [r.x + 1, r.y + 1]; })""" + "(%s)" % json.dumps(xy["p"]))
                dx, dy = ahead[0] - xy["dot"][0], ahead[1] - xy["dot"][1]
                self.assertLess(dy, -20, (name, "route ahead is above the puck", xy, ahead))
                self.assertLess(abs(math.degrees(math.atan2(dx, -dy))), 25, (name, xy, ahead))
                pg.screenshot(path=os.path.join(SHOTS, f"navstart-{name}-headingup.png"))
                ctx.close()

    def test_photo_picked_this_session_shows_in_nav(self):
        for name in self.browsers:
            with self.subTest(browser=name):
                ctx = self.ctx(name)
                pg = ctx.new_page()
                pg.route(NO_NET, lambda r: r.abort())
                pg.goto(self.base + "/map/pacific-beach")
                pg.wait_for_function("window.ready===true", timeout=120000)
                # Pick the photo before the location dot exists (the order Max used).
                pg.evaluate("setMenu(1)")
                pg.set_input_files("#iconFile", files=[{"name": "me.png", "mimeType": "image/png", "buffer": big_png()}])
                pg.wait_for_selector("#iconPrev img")
                url = pg.evaluate("localStorage.getItem('gcm_map_icon')")
                pg.evaluate("fakeLocate(%f,%f)" % (START["latitude"], START["longitude"]))
                pg.evaluate("window._pll = L.latLng(%s); popSet('to')" % SOUTH_DEST)
                pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
                pg.click("#navStart")
                pg.wait_for_timeout(1500)
                srcs = pg.evaluate("[...document.querySelectorAll('.me-cart .me-ico img')].filter(i => i.offsetParent).map(i => i.getAttribute('src'))")
                self.assertTrue(srcs and all(s == url for s in srcs), (name, len(srcs)))
                self.assertEqual(pg.evaluate("[...document.querySelectorAll('.me-cart .me-ico svg')].filter(i => i.offsetParent).length"), 0, name)
                pg.screenshot(path=os.path.join(SHOTS, f"navstart-{name}-photo-city.png"))
                # Renter page, same device: the saved photo is the puck there too.
                # Chromium only, like every other renter-page test (test_turn_by_turn,
                # test_live_nav, test_foldable): the /p/ page never loads its cards
                # in the CI WebKit harness. The city-page photo check above runs in both.
                if name != "chromium":
                    ctx.close()
                    continue
                # Fresh tab in the same context (same localStorage), so the city
                # page's live navigation can't leave WebKit's renter panel hidden.
                pg.close()
                pg = ctx.new_page()
                pg.route(NO_NET, lambda r: r.abort())
                pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(UNLOCK)))
                pg.goto(self.base + "/p/beachmode/go?code=TEST123")
                pg.wait_for_selector(".xcard", timeout=60000)
                pg.click(".goopen")
                pg.wait_for_timeout(1500)
                pg.fill("#goQ", "Crystal Pier")
                pg.wait_for_selector("#goSugg .sugg", timeout=15000)
                pg.click("#goSugg .sugg >> nth=0")
                pg.wait_for_selector("#navBanner.show", timeout=30000)
                pg.click("#navStart")
                pg.wait_for_timeout(1500)
                srcs = pg.evaluate("[...document.querySelectorAll('.me-cart .me-ico img')].filter(i => i.offsetParent).map(i => i.getAttribute('src'))")
                self.assertTrue(srcs and all(s == url for s in srcs), (name, "renter", len(srcs)))
                pg.screenshot(path=os.path.join(SHOTS, f"navstart-{name}-photo-renter.png"))
                ctx.close()


if __name__ == "__main__":
    unittest.main()
