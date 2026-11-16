"""Return reminders: the shop sets a return-by time, a range, and a return spot.

The renter page shows 'Head back in N minutes' from that clock and the ride home.
Screenshots go to $SHOTS_DIR when set.
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
from datetime import datetime, timedelta
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="nudge-")
START = {"latitude": 32.7980, "longitude": -117.2466}


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


def shop():
    return {
        "id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd",
        "blurb": "", "logo_url": "", "color": "", "owner_email": "owner@gmail.com", "disabled": False,
        "vehicle": "golf_cart", "return_by": "17:00", "range_mi": 25,
        "return_lat": 32.85, "return_lon": -117.26,
    }


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ReturnReminders(unittest.TestCase):
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

    def test_admin_saves_return_fields(self):
        saved = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": shop(), "experiences": [], "affiliates": [], "places": [], "codes": []})
                return
            if path == "/api/partner/shop" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                saved.append(body)
                route.fulfill(json={"shop": {**shop(), **body}})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route(re.compile(r"tile\.openstreetmap|photon|nominatim"), lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("#rentReturnBy")
        self.assertEqual(pg.input_value("#rentReturnBy"), "17:00")
        self.assertEqual(pg.input_value("#rentRange"), "25")
        pg.fill("#rentReturnBy", "16:30")
        pg.fill("#rentRange", "18")
        pg.evaluate("() => { document.getElementById('rentReturnLat').value = '32.80000'; document.getElementById('rentReturnLon').value = '-117.25000'; }")
        pg.click("#saveReminders")
        pg.wait_for_function("() => document.body.innerText.includes('Reminders saved')", timeout=8000)
        self.assertEqual(saved[-1]["return_by"], "16:30")
        self.assertEqual(saved[-1]["range_mi"], "18")
        self.assertEqual(saved[-1]["return_lat"], "32.80000")
        self.assertNotIn("\u2014", pg.inner_text("#rentalCard"))
        _shot(pg, "return-reminders-admin.png")
        pg.close()

    def test_renter_sees_head_back_nudge(self):
        due = datetime.now() + timedelta(minutes=10)

        def unlock():
            return {
                "code": "TEST123",
                "shop": {
                    "id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd",
                    "blurb": "", "logo_url": "", "color": "", "vehicle": "golf_cart",
                    "return_by": due.strftime("%H:%M"), "range_mi": 30,
                    "return_lat": START["latitude"], "return_lon": START["longitude"],
                },
                "experiences": [{
                    "id": "e1", "title": "Pier loop", "stops": [
                        {"label": "Crystal Pier Entrance", "lat": 32.7966, "lon": -117.2545, "note": ""},
                    ],
                }],
                "affiliates": [],
            }

        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(unlock())))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector("#nudgeBar:not([hidden])", timeout=25000)
        text = pg.inner_text("#nudgeBar")
        self.assertRegex(text, r"Head back in \d+ minute")
        self.assertNotIn("\u2014", text)
        _shot(pg, "return-nudge.png")
        ctx.close()


if __name__ == "__main__":
    unittest.main()
