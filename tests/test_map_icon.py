"""Settings > Your map icon (Max t427u/t428u): the playful cart is the default; a photo picked from the
device becomes a round ~128 px icon kept only in localStorage (never uploaded), used as the 48 px
navigation puck, and Reset brings the cart back. Big photos get downscaled; unreadable files get a message.

Screenshots go to $SHOTS_DIR (default: a temp dir), never the repo root.
"""
import functools
import io
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
    from test_live_nav import _S, _Quiet, START, PUB
except ImportError:
    from tests.test_live_nav import _S, _Quiet, START, PUB

SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="mapicon-")


def big_png():
    """A 3000x2000 test photo: sky, sand, a red sun. Made here, nothing copyrighted."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (3000, 2000), "#7cc8f0")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 1200, 3000, 2000], fill="#f2d59b")
    d.ellipse([1150, 650, 1850, 1350], fill="#e5484d")
    d.rectangle([1400, 900, 1600, 1100], fill="#ffffff")
    b = io.BytesIO(); im.save(b, "PNG")
    return b.getvalue()


@unittest.skipIf(sync_playwright is None, "playwright not installed")
class MapIcon(unittest.TestCase):
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

    def open(self, ctx):
        pg = ctx.new_page()
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap|photon|nominatim"), lambda r: r.abort())
        pg.goto(self.base + "/map/pacific-beach")
        pg.wait_for_function("window.ready===true", timeout=120000)
        return pg

    def open_settings(self, pg):
        if not pg.is_visible("#iconRow"):
            pg.evaluate("setMenu(1)")  # the gear in the sheet opens Settings
        pg.wait_for_selector("#iconRow", state="visible")
        pg.locator("#iconRow").scroll_into_view_if_needed()

    def test_upload_persists_used_in_nav_and_reset(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True,
                                 device_scale_factor=2, geolocation=START, permissions=["geolocation"])
        pg = self.open(ctx)
        self.open_settings(pg)
        self.assertTrue(pg.is_visible("#iconPrev svg"), "default cart preview")
        self.assertFalse(pg.is_visible("#iconReset"), "nothing to reset yet")
        pg.screenshot(path=os.path.join(SHOTS, "mapicon-picker-default.png"))
        # Not a picture: a friendly message, nothing saved.
        pg.set_input_files("#iconFile", files=[{"name": "notes.heic", "mimeType": "image/heic", "buffer": b"not really a photo"}])
        pg.wait_for_selector("#iconSub.err")
        self.assertIn("HEIC", pg.inner_text("#iconSub"))
        self.assertIsNone(pg.evaluate("localStorage.getItem('gcm_map_icon')"))
        # A big photo: downscaled to a small round PNG under 50 KB.
        pg.set_input_files("#iconFile", files=[{"name": "beach.png", "mimeType": "image/png", "buffer": big_png()}])
        pg.wait_for_selector("#iconPrev img")
        url = pg.evaluate("localStorage.getItem('gcm_map_icon')")
        self.assertTrue(url.startswith("data:image/png;base64,"))
        self.assertLess(len(url), 50000)
        wh = pg.evaluate("(() => { const i = document.querySelector('#iconPrev img'); return [i.naturalWidth, i.naturalHeight]; })()")
        self.assertTrue(wh[0] == wh[1] and 48 <= wh[0] <= 128, wh)
        self.assertTrue(pg.is_visible("#iconReset"))
        pg.screenshot(path=os.path.join(SHOTS, "mapicon-picker-custom.png"))
        # Persists across a reload, and the navigation puck uses it, upright at ~48 px.
        pg.close()
        pg = self.open(ctx)
        self.assertEqual(pg.evaluate("localStorage.getItem('gcm_map_icon')"), url)
        pg.evaluate("fakeLocate(%f,%f)" % (START["latitude"], START["longitude"]))
        pg.evaluate("window._pll = L.latLng(32.7966, -117.2545); popSet('to')")
        pg.wait_for_function("() => window._liveNav && window._liveNav.pts.length > 1", timeout=60000)
        pg.click("#navStart")
        pts = pg.evaluate("window._liveNav.pts")
        for q in pts[1:6]:
            ctx.set_geolocation({"latitude": q[0], "longitude": q[1], "accuracy": 5})
            pg.wait_for_timeout(500)
        pg.wait_for_timeout(1500)
        self.assertEqual(pg.evaluate("document.querySelector('.me-cart .me-ico img').getAttribute('src')"), url)
        cb = pg.locator(".me-cart").bounding_box()
        self.assertTrue(cb and 40 <= cb["width"] <= 60, cb)
        self.assertTrue(pg.is_visible(".me-chev"), "heading chevron shown with a custom icon")
        self.assertEqual(pg.evaluate("getComputedStyle(document.querySelector('.me-ico img')).transform"), "none", "a photo is never mirrored")
        pg.screenshot(path=os.path.join(SHOTS, "mapicon-nav-custom.png"))
        pg.click("#navEnd")
        # Reset returns to the default cart, in Settings and on the puck.
        self.open_settings(pg)
        pg.click("#iconReset")
        self.assertIsNone(pg.evaluate("localStorage.getItem('gcm_map_icon')"))
        self.assertTrue(pg.is_visible("#iconPrev svg"))
        self.assertEqual(pg.evaluate("document.querySelectorAll('.me-ico img').length"), 0)
        self.assertGreater(pg.evaluate("document.querySelectorAll('.me-ico svg').length"), 0)
        ctx.close()


if __name__ == "__main__":
    unittest.main()
