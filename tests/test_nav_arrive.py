"""Max t446u: during navigation a checkered finish flag marks the end, the blue line behind the rider
goes away as they drive, and arriving shows the unicorn celebration once (not again on the next fix).

Screenshots and a frame sequence of the animation go to $SHOTS_DIR (default: a temp dir), never the repo.
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

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="navarrive-")
ME = (32.7973, -117.24764)
DEST = "32.7955, -117.2510"
NO_NET = re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim")


def hav(a, b):
    k = math.pi / 180
    x = math.sin((b[0] - a[0]) * k / 2) ** 2 + math.cos(a[0] * k) * math.cos(b[0] * k) * math.sin((b[1] - a[1]) * k / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(x))


def along(path, step):
    out = [tuple(path[0])]
    for a, b in zip(path, path[1:]):
        n = max(1, int(hav(a, b) // step))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


LINE_M = "(() => { const p = routeLines[2].getLatLngs(); let d = 0; for (let i = 1; i < p.length; i++) d += p[i-1].distanceTo(p[i]); return d; })()"


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class NavArrive(unittest.TestCase):
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

    def ctx(self, reduced=False):
        return self.b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=2,
                                  geolocation={"latitude": ME[0], "longitude": ME[1], "accuracy": 5}, permissions=["geolocation"],
                                  reduced_motion="reduce" if reduced else "no-preference")

    def start(self, ctx):
        pg = ctx.new_page()
        pg.route(NO_NET, lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        pg.evaluate("fakeLocate(%f,%f)" % ME)
        pg.evaluate("window._pll = L.latLng(%s); popSet('to')" % DEST)
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        pg.click("#navStart")
        pg.wait_for_timeout(800)
        return pg

    def test_flag_trim_and_one_celebration(self):
        ctx = self.ctx()
        pg = self.start(ctx)
        self.assertEqual(pg.locator(".gcm-flag").count(), 1, "finish flag while navigating")
        self.assertFalse(pg.locator(".gcm-to-pin").first.is_visible(), "plain pin hidden under the flag")
        pg.screenshot(path=os.path.join(SHOTS, "arrive-flag-start.png"))
        pts = pg.evaluate("window._liveNav.pts")
        drive = along(pts, 15)
        drive = [q for q in drive[:-1] if hav(q, drive[-1]) > 40] + [drive[-1]]  # arrival is 25 m out
        lens = [pg.evaluate(LINE_M)]
        for i, q in enumerate(drive[1:-1], 1):
            ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
            pg.wait_for_timeout(250)
            if i % 4 == 0:
                lens.append(pg.evaluate(LINE_M))
            if i == len(drive) // 2:
                pg.screenshot(path=os.path.join(SHOTS, "arrive-trimmed-midway.png"))
        self.assertGreater(len(lens), 3)
        self.assertTrue(all(b < a + 1 for a, b in zip(lens, lens[1:])), lens)
        self.assertLess(lens[-1], lens[0] * 0.5, lens)
        self.assertEqual(pg.evaluate("window.__gcmArrivals || 0"), 0)
        end = drive[-1]
        ctx.set_geolocation({"latitude": end[0], "longitude": end[1], "accuracy": 5})
        pg.wait_for_selector("#gcmArrive", timeout=5000)
        self.assertIn("You have Arrived!", pg.inner_text("#gcmArrive"))
        self.assertIn("Have a wonderful life you LEGEND", pg.inner_text("#gcmArrive"))
        self.assertEqual(pg.locator("#gcmArrive .u").count(), 8, "eight unicorns (t451u, was three)")
        self.assertGreaterEqual(pg.locator("#gcmArrive .cf").count(), 30, "confetti")
        self.assertEqual(pg.locator("#gcmArrive .arc").count(), 1, "rainbow")
        for f in range(8):
            pg.screenshot(path=os.path.join(SHOTS, "arrive-unicorns-%02d.png" % f))
            pg.wait_for_timeout(400)
        for q in [end, (end[0] + 0.00003, end[1])]:
            ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
            pg.wait_for_timeout(500)
        self.assertEqual(pg.evaluate("window.__gcmArrivals"), 1, "celebrates once, not every fix")
        # guard-change: was "gone by ~4.8 s" for the 3.8 s parade; Max t451u asked for 15 s, so it must still be up at ~8 s and gone by ~16 s.
        pg.wait_for_timeout(3000)
        self.assertEqual(pg.locator("#gcmArrive").count(), 1, "still celebrating at ~8 s (15 s parade)")
        pg.screenshot(path=os.path.join(SHOTS, "arrive-unicorns-8s.png"))
        pg.wait_for_timeout(8500)
        self.assertEqual(pg.locator("#gcmArrive").count(), 0, "goes away by itself (~15 s)")
        pg.click("#navEnd")
        pg.wait_for_timeout(300)
        self.assertEqual(pg.locator(".gcm-flag").count(), 0, "flag gone after End")
        ctx.close()

    def test_tap_dismiss_and_reduced_motion_card(self):
        ctx = self.ctx(reduced=True)
        pg = self.start(ctx)
        pg.evaluate("GCMNavFx.arrive('t', {place: 'Crystal Pier'})")
        self.assertEqual(pg.locator("#gcmArrive.calm .card").count(), 1, "still card, no parade")
        self.assertEqual(pg.locator("#gcmArrive .u").count(), 0)
        pg.screenshot(path=os.path.join(SHOTS, "arrive-reduced-motion.png"))
        pg.click("#gcmArrive")
        self.assertEqual(pg.locator("#gcmArrive").count(), 0, "tap dismisses")
        ctx.close()


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class ArriveBannerFits(unittest.TestCase):
    """Max t454u: the banner is two lines and never clipped, at CarPlay-like widths and phone portrait/landscape."""
    SIZES = [(800, 480), (1280, 480), (390, 844), (844, 390), (375, 667), (667, 375)]

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

    def test_two_lines_fit(self):
        for w, h in self.SIZES:
            for calm in (False, True):
                with self.subTest(size="%dx%d" % (w, h), calm=calm):
                    ctx = self.b.new_context(viewport={"width": w, "height": h})
                    pg = ctx.new_page()
                    pg.route(NO_NET, lambda r: r.abort())
                    pg.goto(self.base + "/")
                    pg.wait_for_function("window.GCMNavFx", timeout=60000)
                    pg.evaluate("GCMNavFx.celebrate({place: 'Destiny Coast', calm: %s})" % ("true" if calm else "false"))
                    pg.wait_for_timeout(1300)  # pop-in done
                    r = pg.evaluate("""() => { const a = document.querySelector('#gcmArrive .msg, #gcmArrive .card');
                      const box = s => { const e = a.querySelector(s), b = e.getBoundingClientRect(), g = document.createRange();
                        g.selectNodeContents(e); const t = g.getBoundingClientRect(); return {l: t.left, r: t.right, top: b.top, bot: b.bottom, sw: e.scrollWidth, cw: e.clientWidth, lines: Math.round(b.height / parseFloat(getComputedStyle(e).lineHeight))}; };
                      return {l1: box('.l1'), l2: box('.l2'), vw: innerWidth, vh: innerHeight}; }""")
                    pg.screenshot(path=os.path.join(SHOTS, "arrive-banner-%dx%d%s.png" % (w, h, "-calm" if calm else "")))
                    for k in ("l1", "l2"):
                        b = r[k]
                        self.assertGreaterEqual(b["l"], 8, (k, b))
                        self.assertLessEqual(b["r"], r["vw"] - 8, (k, b))
                        self.assertGreaterEqual(b["top"], 0, (k, b))
                        self.assertLessEqual(b["bot"], r["vh"], (k, b))
                        self.assertLessEqual(b["sw"], b["cw"] + 1, (k, b))
                    self.assertLess(r["l1"]["bot"], r["l2"]["top"] + 1, "line 2 under line 1")
                    if w > h:
                        self.assertEqual(r["l2"]["lines"], 1, "LEGEND line stays on one line on wide screens")
                    mid = (r["l2"]["l"] + r["l2"]["r"]) / 2
                    self.assertLess(abs(mid - r["vw"] / 2), 3, "centered")
                    ctx.close()
