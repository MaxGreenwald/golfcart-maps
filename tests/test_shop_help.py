"""Help on the unlocked renter page and on the map the app loads.

Call and text use the shop phone. The text includes the renter's current location.
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
from urllib.parse import urlsplit, unquote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR") or tempfile.mkdtemp(prefix="help-")
START = {"latitude": 32.79801, "longitude": -117.24661}
PHONE = "8585550100"


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


def unlock():
    return {
        "code": "TEST123",
        "shop": {
            "id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd",
            "blurb": "", "logo_url": "", "color": "", "vehicle": "golf_cart", "phone": PHONE,
        },
        "experiences": [{
            "id": "e1", "title": "Pier loop", "stops": [
                {"label": "Crystal Pier Entrance", "lat": 32.7966, "lon": -117.2545, "note": ""},
            ],
        }],
        "affiliates": [],
    }


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ShopHelp(unittest.TestCase):
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

    def test_renter_help_text_includes_location(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        pg.route("**/api/partner/public/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(unlock())))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/p/beachmode/go?code=TEST123")
        pg.wait_for_selector("#shopHelp")
        pg.click("#shopHelp")
        pg.wait_for_selector("#shopHelpSheet:not([hidden])")
        pg.wait_for_function("() => document.getElementById('shopHelpText').href.indexOf('32.79801') >= 0", timeout=8000)
        href = pg.get_attribute("#shopHelpText", "href")
        self.assertIn("sms:+1" + PHONE, href)
        self.assertIn("32.79801", unquote(href))
        self.assertIn("-117.24661", unquote(href))
        self.assertTrue(pg.get_attribute("#shopHelpCall", "href").startswith("tel:+1" + PHONE))
        self.assertNotIn("\u2014", pg.inner_text("#shopHelpSheet"))
        _shot(pg, "renter-help.png")
        ctx.close()

    def test_map_help_button_when_a_rental_is_saved(self):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"])
        pg = ctx.new_page()
        access = {"slug": "beachmode", "code": "TEST123", "at": 9_000_000_000_000, "shop": {"name": "Beach Mode Rentals", "phone": PHONE}, "experiences": []}
        pg.add_init_script("localStorage.setItem('gcm_partner_access', %s)" % json.dumps(json.dumps(access)))
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        pg.goto(self.base + "/index.html", wait_until="domcontentloaded")
        pg.wait_for_selector("#shopHelp", timeout=20000)
        self.assertIn("floating", pg.get_attribute("#shopHelp", "class") or "")
        _shot(pg, "map-help.png")
        ctx.close()

    def test_admin_saves_shop_phone(self):
        saved = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": {"id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd", "blurb": "", "logo_url": "", "color": "", "vehicle": "golf_cart", "phone": ""}, "experiences": [], "affiliates": [], "places": [], "codes": []})
                return
            if path == "/api/partner/shop" and req.method == "PATCH":
                saved.append(json.loads(req.post_data or "{}"))
                route.fulfill(json={"shop": {"id": "s1", "name": "La Jolla Cart Co"}})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("#brandPhone")
        pg.fill("#brandPhone", "858-555-0100")
        pg.click("#saveBrand")
        pg.wait_for_function("() => document.body.innerText.includes('Brand saved')", timeout=8000)
        self.assertEqual(saved[-1]["phone"], "858-555-0100")
        pg.close()


if __name__ == "__main__":
    unittest.main()
