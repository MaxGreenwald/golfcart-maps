"""Rental info: the shop saves pickup, return, phone, rules, and a dead-cart note.

Renters see it on the unlocked /p/<slug> page. The locked page does not show the phone.
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
SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
PHONE = "619-555-0142"

SHOP = {
    "id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd",
    "blurb": "Coastal loops", "logo_url": "", "color": "", "owner_email": "owner@gmail.com",
    "disabled": False, "vehicle": "golf_cart",
}


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


def rental():
    return {
        "pickup": "Blue umbrellas by the shop",
        "return_spot": "Same spot",
        "return_by": "5:00 pm",
        "phone": PHONE,
        "rules": "Seat belts on. Charge in the side lot.",
        "if_cart_dies": "Call the shop and stay with the cart.",
    }


class RentalInfoSource(unittest.TestCase):
    def test_admin_and_renter_copy_has_no_em_dash(self):
        with open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8") as f:
            admin = f.read()
        for line in ("Save rental info", "If the cart dies", "Pickup spot", "rentalPickup", "id=\"rentalForm\""):
            self.assertIn(line, admin)
            self.assertNotIn("\u2014", line)


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class RentalInfoUI(unittest.TestCase):
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

    def test_admin_saves_and_renter_sees_the_card_only_when_unlocked(self):
        saved = {}
        shop = dict(SHOP)
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": shop, "experiences": [], "affiliates": [], "places": [], "codes": []})
                return
            if path == "/api/partner/shop" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                saved["body"] = body
                shop["rental"] = body.get("rental") or {}
                route.fulfill(json={"shop": shop})
                return
            if path == "/api/partner/public/lajollacartco" and req.method == "GET":
                # A buggy teaser that includes rental must still not paint the phone.
                leaked = dict(shop)
                leaked["rental"] = rental()
                route.fulfill(json={"shop": leaked, "unlocked": False, "experience_count": 1, "affiliate_count": 0})
                return
            if path.startswith("/api/partner/public/lajollacartco/unlock"):
                route.fulfill(json={
                    "unlocked": True, "code": "DESKCODE",
                    "shop": {**shop, "rental": rental()},
                    "experiences": [], "affiliates": [], "places": [], "grant": "g",
                })
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#rentalForm")
            info = rental()
            pg.fill("#rentalPickup", info["pickup"])
            pg.fill("#rentalReturn", info["return_spot"])
            pg.fill("#rentalBy", info["return_by"])
            pg.fill("#rentalPhone", info["phone"])
            pg.fill("#rentalRules", info["rules"])
            pg.fill("#rentalDies", info["if_cart_dies"])
            for width in (1280, 375):
                pg.set_viewport_size({"width": width, "height": 900})
                spill = pg.evaluate(
                    """() => {
                      const vw = document.documentElement.clientWidth;
                      const els = [...document.querySelectorAll('#rentalForm input, #rentalForm textarea, #saveRental')];
                      let worst = 0;
                      for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width <= 0) return 999;
                        worst = Math.max(worst, r.right - vw, -r.left);
                      }
                      return worst;
                    }"""
                )
                self.assertLessEqual(spill, 1, "rental form spills at %s" % width)
            pg.set_viewport_size({"width": 900, "height": 900})
            pg.locator("#saveRental").click()
            pg.wait_for_function("() => document.body.innerText.includes('Rental info saved')")
            self.assertEqual(saved["body"]["rental"]["phone"], PHONE)
            self.assertEqual(saved["body"]["rental"]["if_cart_dies"], info["if_cart_dies"])
            self.assertNotIn("name", saved["body"])
            self.assertEqual(pg.input_value("#rentalBy"), "5:00 pm")
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.locator("#rentalForm").scroll_into_view_if_needed()
                pg.screenshot(path=os.path.join(SHOTS, "rental-admin.png"))

            locked = self.b.new_page()
            locked.route("**/api/partner/**", handle)
            locked.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
            locked.goto(self.base + "/p/lajollacartco", wait_until="domcontentloaded")
            locked.wait_for_selector("#unlockForm")
            self.assertEqual(locked.locator("#rentalCard").count(), 0)
            self.assertNotIn(PHONE, locked.inner_text("body"))
            locked.close()

            openp = self.b.new_page()
            openp.route("**/api/partner/**", handle)
            openp.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
            openp.goto(self.base + "/p/lajollacartco/go?code=DESKCODE", wait_until="domcontentloaded")
            openp.wait_for_selector("#rentalCard")
            card = openp.locator("#rentalCard").inner_text()
            self.assertIn("Your rental", openp.locator("#rentalCard").inner_html())
            self.assertIn("Blue umbrellas by the shop", card)
            self.assertIn("5:00 pm", card)
            self.assertIn(PHONE, card)
            self.assertIn("Seat belts on.", card)
            self.assertIn("stay with the cart", card)
            self.assertEqual(openp.locator("#rentalCard a").get_attribute("href"), "tel:6195550142")
            self.assertNotIn("\u2014", card)
            if SHOTS:
                openp.screenshot(path=os.path.join(SHOTS, "rental-renter.png"))
            openp.close()
        finally:
            pg.close()
