"""Arrival at an experience stop speaks the shop note after the callout, and the web page can play it again.

Mute (the banner speaker) blocks both the automatic story and Play story.
Screenshots go to $SHOTS_DIR when that is set.
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
SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="stories-")
NOTE = "Park by the blue umbrellas and watch the seals."
START = {"latitude": 32.7980, "longitude": -117.2466}
UNLOCK = {
    "code": "TEST123",
    "shop": {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd", "blurb": "", "logo_url": "", "color": ""},
    "experiences": [{
        "id": "e1", "title": "Pier loop", "description": "",
        "stops": [
            {"label": "Crystal Pier Entrance", "lat": 32.7966, "lon": -117.2545, "note": NOTE},
            {"label": "Tourmaline Surf Park", "lat": 32.8055, "lon": -117.2610, "note": ""},
        ],
    }],
    "affiliates": [],
}


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


def _shot(pg, name):
    os.makedirs(SHOTS, exist_ok=True)
    pg.screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class StopStories(unittest.TestCase):
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

    def page(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(UNLOCK)))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector("#startEx")
        return ctx, pg

    def arrive(self, ctx, pg):
        pg.click("#startEx")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        end = pg.evaluate("GCMNavDebug().pts.slice(-1)[0]")
        ctx.set_geolocation({"latitude": end[0], "longitude": end[1]})
        pg.wait_for_function("() => /arrived at Crystal Pier/.test(document.getElementById('navText').textContent)", timeout=15000)

    def test_story_follows_the_callout_and_can_be_replayed(self):
        ctx, pg = self.page()
        self.arrive(ctx, pg)
        pg.wait_for_function(
            "() => { const s = window.__navSaid || []; const i = s.findIndex(t => /arrived at Crystal Pier/.test(t));"
            " const j = s.findIndex(t => t.indexOf('blue umbrellas') >= 0); return i >= 0 && j > i; }",
            timeout=15000,
        )
        self.assertIn(NOTE, pg.inner_text("#navStoryText"))
        self.assertTrue(pg.is_visible("#navStory"))
        self.assertNotIn("\u2014", pg.inner_text("#navBanner"))
        before = pg.evaluate("() => (window.__navSaid || []).length")
        pg.click("#navStory")
        pg.wait_for_function("(n) => (window.__navSaid || []).length > n", arg=before, timeout=5000)
        _shot(pg, "stop-story-arrived.png")
        ctx.close()

    def test_mute_blocks_the_story_until_play_after_unmute(self):
        ctx, pg = self.page()
        pg.click("#startEx")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        pg.click("#navBanner #navMute")
        self.assertEqual(pg.get_attribute("#navBanner #navMute", "aria-pressed"), "true")
        end = pg.evaluate("GCMNavDebug().pts.slice(-1)[0]")
        ctx.set_geolocation({"latitude": end[0], "longitude": end[1]})
        pg.wait_for_function("() => /arrived at Crystal Pier/.test(document.getElementById('navText').textContent)", timeout=15000)
        said = pg.evaluate("() => window.__navSaid || []")
        self.assertFalse(any("blue umbrellas" in t for t in said), said)
        pg.click("#navStory")
        self.assertIn("Voice is muted", pg.inner_text("#navStoryText"))
        _shot(pg, "stop-story-muted.png")
        pg.click("#navBanner #navMute")
        pg.click("#navStory")
        pg.wait_for_function("() => (window.__navSaid || []).some(t => t.indexOf('blue umbrellas') >= 0)", timeout=5000)
        ctx.close()


if __name__ == "__main__":
    unittest.main()
