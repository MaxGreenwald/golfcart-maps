"""Partner stop editor: Google Places proxy suggestions, then Photon / Nominatim fallback.

Run: python3 tests/test_partner_places_autocomplete.py
"""
import functools
import http.server
import json
import os
import socketserver
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # unit-test CI job has no browser; the browser job runs this file
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR")

SHOP = {
    "id": "s1",
    "slug": "lajollacartco",
    "name": "La Jolla Cart Co",
    "region_id": "sd",
    "blurb": "",
    "logo_url": "",
    "color": "",
    "owner_email": "owner@gmail.com",
    "disabled": False,
}


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.rstrip("/") == "/partner":
            path = "/partner/index.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class PlacesAutocomplete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _S(("127.0.0.1", 0), functools.partial(_Quiet, directory=PUB))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.pw = sync_playwright().start()
        kw = {}
        if os.environ.get("PW_CHANNEL"):
            kw["channel"] = os.environ["PW_CHANNEL"]
        cls.b = cls.pw.chromium.launch(**kw)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def _open(self, handle):
        pg = self.b.new_page(viewport={"width": 1100, "height": 1400})
        pg.route("**/api/partner/**", handle)
        pg.goto(self.base + "/partner/", wait_until="domcontentloaded")
        pg.wait_for_selector("#stopList .stop [data-k=q]")
        return pg

    def _shop_handle(self, extra):
        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            body = json.loads(req.post_data) if req.post_data else None
            if path == "/api/partner/auth/me" and req.method == "GET":
                return route.fulfill(json={
                    "user": {"email": "owner@gmail.com", "super": False},
                    "dev_auth": False,
                    "google": True,
                })
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json={
                    "shop": SHOP,
                    "experiences": [],
                    "affiliates": [],
                    "places": [],
                    "codes": [],
                })
            if extra(route, req, path, body):
                return
            return route.fulfill(json={"error": "unexpected " + path}, status=500)
        return handle

    def test_google_suggestions_then_details_fill_the_pin(self):
        posts = []

        def extra(route, req, path, body):
            if path == "/api/partner/places/autocomplete" and req.method == "POST":
                posts.append(("autocomplete", body))
                route.fulfill(json={
                    "fallback": False,
                    "suggestions": [{
                        "name": "La Jolla Cove",
                        "sub": "Coast Walk, San Diego, CA",
                        "place_id": "ChIJTestCove",
                    }],
                })
                return True
            if path == "/api/partner/places/details" and req.method == "POST":
                posts.append(("details", body))
                route.fulfill(json={
                    "name": "La Jolla Cove",
                    "address": "1100 Coast Blvd, La Jolla, CA 92037, USA",
                    "lat": 32.85012,
                    "lon": -117.27234,
                })
                return True
            return False

        pg = self._open(self._shop_handle(extra))
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        q = pg.locator("#stopList .stop [data-k=q]").first
        q.fill("cove")
        pg.wait_for_selector("#stopList .stop [data-k=sugg] b")
        self.assertIn("La Jolla Cove", pg.locator("#stopList .stop [data-k=sugg]").inner_text())
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            pg.screenshot(path=os.path.join(SHOTS, "partner-places-autocomplete.png"), full_page=True)
        pg.locator("#stopList .stop [data-k=sugg] div").first.click()
        pg.wait_for_function(
            """() => {
              const row = document.querySelector('#stopList .stop');
              return row && row.querySelector('[data-k=lat]').value === '32.85012'
                && row.querySelector('[data-k=lon]').value === '-117.27234';
            }"""
        )
        kinds = [k for k, _ in posts]
        self.assertIn("autocomplete", kinds)
        self.assertIn("details", kinds)
        auto = next(b for k, b in posts if k == "autocomplete")
        det = next(b for k, b in posts if k == "details")
        self.assertEqual(auto["q"], "cove")
        self.assertTrue(auto.get("sessionToken"))
        self.assertEqual(auto["bbox"][0], 32.53)
        self.assertEqual(det["placeId"], "ChIJTestCove")
        self.assertEqual(det["sessionToken"], auto["sessionToken"])
        self.assertNotIn("GOOGLE_PLACES_API_KEY", json.dumps(posts))
        picked = pg.locator("#stopList .stop [data-k=picked]").inner_text()
        self.assertIn("La Jolla Cove", picked)
        self.assertIn("32.85012", picked)
        pg.close()

    def test_fallback_to_photon_when_proxy_asks(self):
        def extra(route, req, path, body):
            if path == "/api/partner/places/autocomplete" and req.method == "POST":
                route.fulfill(json={"fallback": True, "reason": "not_configured", "suggestions": []})
                return True
            if path == "/api/partner/places/details":
                route.fulfill(json={"error": "not used"}, status=500)
                return True
            return False

        photon = {
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-117.26, 32.85]},
                "properties": {"name": "La Jolla Seals", "city": "San Diego", "osm_value": "attraction"},
            }],
        }
        pg = self.b.new_page(viewport={"width": 1100, "height": 1400})
        pg.route("**/api/partner/**", self._shop_handle(extra))
        pg.route("**://photon.komoot.io/**", lambda r: r.fulfill(json=photon))
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.goto(self.base + "/partner/", wait_until="domcontentloaded")
        pg.wait_for_selector("#stopList .stop [data-k=q]")
        pg.locator("#stopList .stop [data-k=q]").first.fill("seals")
        pg.wait_for_selector("#stopList .stop [data-k=sugg] b")
        self.assertIn("La Jolla Seals", pg.locator("#stopList .stop [data-k=sugg]").inner_text())
        pg.locator("#stopList .stop [data-k=sugg] div").first.click()
        pg.wait_for_function(
            """() => {
              const row = document.querySelector('#stopList .stop');
              return row && row.querySelector('[data-k=lat]').value === '32.85'
                && row.querySelector('[data-k=lon]').value === '-117.26';
            }"""
        )
        pg.close()


if __name__ == "__main__":
    unittest.main()
