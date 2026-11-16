"""Ready-made rides: a shop sees legal loops for its town and vehicle, and can add one to edit.

Run: python3 tests/test_starter_experiences.py   (SHOTS_DIR=/tmp/x to save screenshots)
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
    "id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "30a",
    "blurb": "", "logo_url": "", "color": "", "owner_email": "brian@gmail.com",
    "disabled": False, "vehicle": "lsv",
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
    page.locator("#starterCard").screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class StarterExperiences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PUB, "data", "30a", "starters.json"), encoding="utf-8") as f:
            cls.starters = json.load(f)
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

    def test_add_a_ready_made_ride_and_edit_it(self):
        rides = self.starters["vehicles"]["lsv"]
        self.assertGreaterEqual(len(rides), 1)
        experiences = []
        posts = []
        pg = self.b.new_page(viewport={"width": 1100, "height": 1200})

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            body = json.loads(req.post_data) if req.post_data else None
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "brian@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json={"shop": SHOP, "experiences": list(experiences), "affiliates": [], "places": [], "codes": []})
            if path == "/api/partner/shop/experiences" and req.method == "POST":
                posts.append(body)
                row = dict(body, id="e-new", shop_id="s1", nearest_start=True)
                experiences.append(row)
                return route.fulfill(json={"experience": row}, status=201)
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#starterList .starter-ride")
            text = pg.inner_text("#starterCard")
            self.assertIn("street-legal LSV", text)
            self.assertIn("30A", text)
            for ride in rides:
                self.assertIn(ride["title"], text)
                self.assertIn(ride["stops"][0]["label"], text)
            shot(pg, "starter-rides.png")
            pg.set_viewport_size({"width": 390, "height": 844})
            shot(pg, "starter-rides-phone.png")
            pg.set_viewport_size({"width": 1100, "height": 1200})
            pg.click("#starterList .starter-ride button")
            pg.wait_for_function("document.querySelector('#exTitle') && document.querySelector('#exTitle').value.length > 0")
            self.assertEqual(posts[0]["title"], rides[0]["title"])
            self.assertEqual(len(posts[0]["stops"]), 3)
            self.assertTrue(all(s.get("label") and isinstance(s.get("lat"), (int, float)) for s in posts[0]["stops"]))
            self.assertEqual(pg.input_value("#exTitle"), rides[0]["title"])
            self.assertIn(rides[0]["stops"][0]["label"], pg.input_value("#stopList [data-k=name]"))
            # Golf cart list can differ. Switching the vehicle reloads the card.
            pg.select_option("#brandVehicle", "golf_cart")
            pg.wait_for_function("document.querySelector('#starterHint').innerText.includes('golf cart')")
            cart = self.starters["vehicles"]["golf_cart"]
            hint = pg.inner_text("#starterHint")
            if cart:
                self.assertIn(cart[0]["title"], pg.inner_text("#starterList"))
            else:
                self.assertIn("No ready-made rides", hint)
        finally:
            pg.close()

    def test_admin_offers_starters_when_the_town_changes(self):
        src = open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8").read()
        self.assertIn("starters.json", src)
        self.assertIn("data-starter", src)
        self.assertIn("nearest_start: true", src)
        self.assertNotIn("—", src[src.find("function starterBlock"):src.find("function shopView")])
