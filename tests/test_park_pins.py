"""Parking pins: the shop marks where to park, and the route ends there.

Screenshots go to $SHOTS_DIR when set.
"""
import functools
import http.server
import json
import math
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
SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="park-")
START = {"latitude": 32.7980, "longitude": -117.2466}
ADDR = (32.7966, -117.2545)
# About 40 m south of the pier entrance, still on the same streets.
PARK = (32.79625, -117.2545)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.rstrip("/") == "/partner":
            path = "/partner/index.html"
        elif re.fullmatch(r"/p/[^/]+(?:/go)?/?", path):
            path = "/p.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def _shot(pg, name):
    os.makedirs(SHOTS, exist_ok=True)
    pg.screenshot(path=os.path.join(SHOTS, name))


def meters(a, b):
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ParkPins(unittest.TestCase):
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

    def test_route_ends_at_the_parking_pin(self):
        unlock = {
            "code": "TEST123",
            "shop": {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd", "blurb": "", "logo_url": "", "color": "", "vehicle": "golf_cart"},
            "experiences": [{
                "id": "e1", "title": "Pier loop", "stops": [{
                    "label": "Crystal Pier Entrance", "lat": ADDR[0], "lon": ADDR[1],
                    "park_lat": PARK[0], "park_lon": PARK[1], "note": "",
                }],
            }],
            "affiliates": [],
        }
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(unlock)))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.click("#startEx")
        pg.wait_for_selector("#navBanner.show", timeout=30000)
        end = pg.evaluate("GCMNavDebug().pts.slice(-1)[0]")
        self.assertLess(meters(end, PARK), meters(end, ADDR))
        self.assertLess(meters(end, PARK), 80)
        self.assertTrue(pg.evaluate("() => [...document.querySelectorAll('.leaflet-marker-icon')].some(el => (el.textContent || '').trim() === 'P')"))
        _shot(pg, "park-route.png")
        ctx.close()

    def test_admin_saves_a_parking_pin(self):
        saved = []
        shop = {"id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd", "blurb": "", "logo_url": "", "color": "", "vehicle": "golf_cart", "owner_email": "owner@gmail.com", "disabled": False}
        ex = {"id": "ex1", "title": "Pier", "description": "", "stops": [{"label": "Seals", "lat": 32.85, "lon": -117.26, "note": "Morning"}]}
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": shop, "experiences": [ex], "affiliates": [], "places": [], "codes": []})
                return
            if path == "/api/partner/shop/experiences/ex1" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                saved.append(body)
                route.fulfill(json={"experience": {**ex, **body}})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route(re.compile(r"tile\.openstreetmap|photon|nominatim"), lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.click("[data-edit-ex='ex1']")
        pg.wait_for_selector(".parkDrop")
        self.assertIn("No parking pin", pg.inner_text("[data-k=parkpicked]"))
        pg.evaluate("""() => {
          const row = document.querySelector('#stopList .stop');
          row.querySelector('[data-k=park_lat]').value = '32.85030';
          row.querySelector('[data-k=park_lon]').value = '-117.26010';
        }""")
        pg.click("#addEx")
        pg.wait_for_timeout(500)
        self.assertTrue(saved, "save did not post")
        stop = saved[-1]["stops"][0]
        self.assertAlmostEqual(stop["park_lat"], 32.8503)
        self.assertAlmostEqual(stop["park_lon"], -117.2601)
        self.assertEqual(stop["label"], "Seals")
        self.assertNotIn("\u2014", pg.inner_text("#stopList"))
        _shot(pg, "park-admin.png")
        pg.close()


if __name__ == "__main__":
    unittest.main()
