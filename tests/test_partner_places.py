"""Places of interest: owner adds, edits, deletes them (no coupon) and the renter map shows them by category.

Run: python3 tests/test_partner_places.py   (SHOTS_DIR=/tmp/x to save screenshots)
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
except ImportError:  # unit-test CI job has no browser; the browser job runs this file
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR")


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


SHOP = {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd", "blurb": "", "logo_url": "",
        "color": "", "owner_email": "brian@gmail.com", "disabled": False}


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class Places(unittest.TestCase):
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

    def test_owner_crud_places_and_use_as_stop(self):
        places = [{"id": "p1", "shop_id": "s1", "name": "Old Pier", "category": "trivia", "lat": 32.85, "lon": -117.27,
                   "note": "Built in 1925", "link": ""}]
        posts = []
        pg = self.b.new_page(viewport={"width": 1100, "height": 1400})

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            body = json.loads(req.post_data) if req.post_data else None
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "brian@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json={"shop": SHOP, "experiences": [], "affiliates": [], "places": list(places), "codes": []})
            if path == "/api/partner/shop/places" and req.method == "POST":
                posts.append(body)
                row = dict(body, id="p%d" % (len(places) + 1), shop_id="s1")
                places.append(row)
                return route.fulfill(json={"place": row}, status=201)
            m = re.fullmatch(r"/api/partner/shop/places/(\w+)", path)
            if m:
                row = next(p for p in places if p["id"] == m.group(1))
                if req.method == "DELETE":
                    places.remove(row)
                    return route.fulfill(json={"ok": True})
                row.update(body)
                return route.fulfill(json={"place": row})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#placesCard")
            self.assertIn("Old Pier", pg.inner_text("#placesCard"))
            self.assertEqual(pg.locator("#placeRow .moveUp").is_visible(), False, "no reorder buttons on a place")
            # Add: category + name + pin (hidden lat/lon, as Search place / Drop pin would set) + note. No coupon field.
            self.assertEqual(pg.locator("#placesCard [id*=oupon]").count(), 0)
            pg.select_option("#placeCat", "restaurant")
            row = pg.locator("#placeRow .stop")
            row.locator("[data-k=name]").fill("Taco Shack")
            pg.evaluate("""() => { const r = document.querySelector('#placeRow .stop');
              r.querySelector('[data-k=lat]').value = '32.8401'; r.querySelector('[data-k=lon]').value = '-117.2741'; }""")
            row.locator("[data-k=note]").fill("Fish tacos")
            pg.fill("#placeLink", "https://example.com/tacos")
            if SHOTS:
                pg.locator("#placesCard").screenshot(path=os.path.join(SHOTS, "admin_places.png"))
            pg.click("#savePlace")
            pg.wait_for_function("document.querySelector('#placesCard').innerText.includes('Taco Shack')")
            self.assertEqual(posts[-1], {"name": "Taco Shack", "category": "restaurant", "lat": 32.8401, "lon": -117.2741,
                                         "note": "Fish tacos", "link": "https://example.com/tacos"})
            # Edit.
            pg.click("[data-edit-place='p1']")
            self.assertEqual(pg.input_value("#placeCat"), "trivia")
            self.assertEqual(pg.locator("#placeRow [data-k=name]").input_value(), "Old Pier")
            pg.select_option("#placeCat", "fun_fact")
            pg.locator("#placeRow [data-k=note]").fill("Rebuilt in 1987")
            pg.click("#savePlace")
            pg.wait_for_selector(".msg.ok")
            self.assertEqual((places[0]["category"], places[0]["note"], places[0]["lat"]), ("fun_fact", "Rebuilt in 1987", 32.85))
            # Use a place as an experience stop.
            pg.select_option("#addPlaceStop", "p2")
            first = pg.locator("#stopList .stop").first
            self.assertEqual(first.locator("[data-k=label]").input_value(), "Taco Shack")
            self.assertEqual(first.locator("[data-k=lat]").input_value(), "32.8401")
            # Delete.
            pg.once("dialog", lambda d: d.accept())
            pg.click("[data-del-place='p1']")
            pg.wait_for_function("!document.querySelector(\"[data-del-place='p1']\")")
            self.assertEqual([p["id"] for p in places], ["p2"])
        finally:
            pg.close()

    def test_renter_map_shows_places_with_icons_and_notes(self):
        places = [
            {"id": "p1", "name": "Taco Shack", "category": "restaurant", "lat": 32.84, "lon": -117.274, "note": "Fish tacos", "link": "https://example.com/t"},
            {"id": "p2", "name": "Cliff overlook", "category": "views", "lat": 32.845, "lon": -117.28, "note": "Best at sunset", "link": ""},
            {"id": "p3", "name": "Old Pier", "category": "trivia", "lat": 32.85, "lon": -117.27, "note": "Built in 1925", "link": "javascript:alert(1)"},
            {"id": "p4", "name": "Seal rock", "category": "fun_fact", "lat": 32.847, "lon": -117.278, "note": "Seals nap here", "link": ""},
            {"id": "p5", "name": "Mural", "category": "other", "lat": 32.843, "lon": -117.272, "note": "", "link": ""},
        ]
        pg = self.b.new_page(viewport={"width": 1200, "height": 900})

        def handle(route):
            path = urlsplit(route.request.url).path
            if path.startswith("/api/partner/public/beachmode/unlock"):
                return route.fulfill(json={"unlocked": True, "shop": SHOP, "experiences": [], "affiliates": [
                    {"id": "a1", "name": "Bar One", "lat": 32.841, "lon": -117.27, "offer": "10% off", "coupon": "BAR10"}],
                    "places": places, "code": "ABC123"})
            if path == "/api/partner/public/beachmode":
                return route.fulfill(json={"shop": SHOP, "unlocked": False, "experience_count": 0, "affiliate_count": 1})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/p/beachmode/go?code=ABC123", wait_until="domcontentloaded")
            pg.wait_for_selector(".pcard")
            pg.wait_for_function("document.querySelectorAll('.pin-place').length === 5")
            icons = pg.eval_on_selector_all(".pin-place", "els => els.map(e => e.dataset.cat + e.textContent)")
            self.assertEqual(sorted(icons), sorted(["restaurant🍽️", "views🌅", "trivia❓", "fun_fact💡", "other📍"]))
            self.assertEqual(pg.locator(".pin-aff").count(), 1, "affiliate offers keep their own pin")
            self.assertIn("BAR10", pg.inner_text("#panel") if pg.locator("#panel").count() else pg.inner_text("body"))
            pg.click(".pcard[data-place='p3']")
            pg.wait_for_selector(".leaflet-popup-content")
            pop = pg.inner_text(".leaflet-popup-content")
            self.assertIn("Old Pier", pop)
            self.assertIn("Trivia", pop)
            self.assertIn("Built in 1925", pop)
            self.assertEqual(pg.locator(".leaflet-popup-content a").count(), 0, "non-https link is not rendered")
            pg.click(".pcard[data-place='p1']")
            pg.wait_for_function("document.querySelector('.leaflet-popup-content').innerText.includes('Fish tacos')")
            self.assertEqual(pg.get_attribute(".leaflet-popup-content a", "href"), "https://example.com/t")
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "renter_places.png"))
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
