"""Copy a ride or a whole page to another location the partner owns.

Run: python3 tests/test_partner_templates.py   (SHOTS_DIR=/tmp/x to save screenshots)
"""
import functools
import http.server
import json
import os
import re
import socketserver
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR")

SHOP = {
    "id": "s1", "slug": "beachmode", "name": "Beach Mode Sarasota", "region_id": "siesta",
    "blurb": "Sunset carts", "logo_url": "", "color": "", "owner_email": "brian@gmail.com",
    "disabled": False, "vehicle": "lsv", "page_template_id": "page1",
}
OTHER = {"id": "s2", "name": "Beach Mode Fort Myers", "slug": "beachmode-fm", "region_id": "fortmyers"}
RIDE = {
    "id": "e1", "title": "Sunset loop", "description": "West", "template_id": "t1",
    "nearest_start": True, "stops": [{"label": "Pier", "lat": 27.2, "lon": -82.5, "note": ""}],
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


def shot(page, name):
    if not SHOTS:
        return
    os.makedirs(SHOTS, exist_ok=True)
    page.locator("#copyCard").screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class PartnerTemplates(unittest.TestCase):
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

    def test_copy_a_ride_and_the_page(self):
        posts = []
        pg = self.b.new_page(viewport={"width": 1100, "height": 1400})

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            body = json.loads(req.post_data) if req.post_data else None
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "brian@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json={"shop": SHOP, "experiences": [RIDE], "affiliates": [], "places": [], "codes": []})
            if path == "/api/partner/shop/locations":
                return route.fulfill(json={"locations": [OTHER]})
            if path in ("/api/partner/shop/copy-experience", "/api/partner/shop/copy-page") and req.method == "POST":
                posts.append((path, body))
                if path.endswith("copy-page"):
                    return route.fulfill(json={"keep_pins": False, "synced": True, "copied": {"experiences": 1, "affiliates": 0, "places": 0}}, status=201)
                return route.fulfill(json={"experience": RIDE, "keep_pins": False, "synced": True}, status=201)
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#copyCard")
            text = pg.inner_text("#copyCard")
            self.assertIn("Beach Mode Fort Myers", text)
            self.assertIn("Linked to your other locations", pg.inner_text("body"))
            pg.click("[data-copy-ex='e1']")
            pg.wait_for_selector("#copyExBox:not(.hidden)")
            self.assertIn("Sunset loop", pg.inner_text("#copyExLabel"))
            shot(pg, "copy-locations.png")
            pg.set_viewport_size({"width": 390, "height": 844})
            shot(pg, "copy-locations-phone.png")
            pg.set_viewport_size({"width": 1100, "height": 1400})
            pg.click("#copyExGo")
            pg.wait_for_function("document.body.innerText.includes('Ride copied')")
            self.assertEqual(posts[0][1]["dest_shop_id"], "s2")
            self.assertEqual(posts[0][1]["experience_id"], "e1")
            self.assertEqual(posts[0][1]["sync"], True)
            self.assertNotIn("push_shop_ids", posts[0][1])
            pg.click("[data-edit-ex='e1']")
            self.assertFalse(pg.locator("#exPushRow").evaluate("el => el.classList.contains('hidden')"))
            pg.click("#copyPage")
            pg.wait_for_function("document.body.innerText.includes('Page copied')")
            self.assertTrue(posts[-1][0].endswith("copy-page"))
            self.assertEqual(posts[-1][1]["sync"], True)
            self.assertIn("drop new pins", pg.inner_text("body").lower())
        finally:
            pg.close()

    def test_one_location_explains_that_a_second_shop_is_required(self):
        pg = self.b.new_page(viewport={"width": 900, "height": 800})

        def handle(route):
            path = urlsplit(route.request.url).path
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "brian@gmail.com", "super": False}, "google": True})
            if path == "/api/partner/shop" and route.request.method == "GET":
                shop = dict(SHOP, page_template_id="")
                return route.fulfill(json={"shop": shop, "experiences": [], "affiliates": [], "places": [], "codes": []})
            if path == "/api/partner/shop/locations":
                return route.fulfill(json={"locations": []})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#copyCard")
            self.assertIn("one location", pg.inner_text("#copyCard"))
            self.assertEqual(pg.locator("#copyPage").count(), 0)
        finally:
            pg.close()
