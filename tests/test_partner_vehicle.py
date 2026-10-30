"""Per-shop rental vehicle: the admin saves it, and /p/<slug> draws roads with that shop's rules.

CA: golf cart roads up to 25 mph (CVC 21716), LSV roads up to 35 mph (CVC 21260).
Grand Ave in Pacific Beach is posted 35 mph: green for an LSV shop, red for a golf cart shop.
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
GREEN = "#12a150"
RED = "#e5484d"


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


def shop(**over):
    base = {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd",
            "blurb": "", "logo_url": "", "color": "", "owner_email": "owner@gmail.com", "disabled": False}
    base.update(over)
    return base


# Two stops on Grand Ave, Pacific Beach (Mission Blvd end to Ingraham St end).
EXP = {"id": "e1", "shop_id": "s1", "title": "Grand Ave run", "description": "",
       "stops": [{"name": "Grand & Mission", "lat": 32.7965, "lon": -117.2525},
                 {"name": "Grand & Ingraham", "lat": 32.7990, "lon": -117.2330}]}


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ShopVehicle(unittest.TestCase):
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

    def test_admin_shows_and_saves_vehicle(self):
        row = shop()  # no vehicle field: an older shop row
        saved = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json={"shop": row, "experiences": [], "affiliates": [], "codes": []})
            if path == "/api/partner/shop" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                row.update(body)
                saved.append(body)
                return route.fulfill(json={"shop": dict(row)})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#brandVehicle")
            self.assertIn("Your rental vehicles", pg.inner_text("label[for=brandVehicle]"))
            self.assertEqual(pg.input_value("#brandVehicle"), "golf_cart")
            opts = pg.locator("#brandVehicle option").all_inner_texts()
            self.assertIn("Street-legal LSV (roads up to 35 mph)", opts)
            self.assertIn("Golf cart (roads up to 25 mph)", opts)
            pg.select_option("#brandVehicle", "lsv")
            pg.click("#saveBrand")
            pg.wait_for_selector(".msg.ok")
            self.assertEqual(saved[-1]["vehicle"], "lsv")
            self.assertEqual(saved[-1]["name"], "Beach Mode Rentals")
            self.assertEqual(pg.input_value("#brandVehicle"), "lsv")
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "admin_vehicle.png"), full_page=True)
        finally:
            pg.close()

    def renter(self, vehicle):
        sh = shop(**({"vehicle": vehicle} if vehicle else {}))
        pg = self.b.new_page(viewport={"width": 1280, "height": 900})

        def handle(route):
            path = urlsplit(route.request.url).path
            if path.endswith("/unlock"):
                return route.fulfill(json={"unlocked": True, "shop": sh, "experiences": [EXP], "affiliates": [], "code": "TEST123"})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.goto(self.base + "/p/beachmode/go?code=TEST123", wait_until="domcontentloaded")
        pg.wait_for_function("typeof roadApi !== 'undefined' && roadApi && roadApi.segments().length > 0", timeout=60000)
        pg.wait_for_timeout(1500)
        # Posted-35 pieces of Grand Ave that sit between the two stops.
        st = pg.evaluate("""() => {
          const out = {veh: roadApi.veh, colors: {}};
          for (const s of roadApi.segments()) {
            if (s[2] !== 35 || !s[7]) continue;
            const ok = s[7].some(p => p[1] > 32.794 && p[1] < 32.802 && p[0] > -117.252 && p[0] < -117.234);
            if (!ok) continue;
            const c = roadApi.roadStyle(s).color;
            out.colors[c] = (out.colors[c] || 0) + 1;
          }
          return out;
        }""")
        return pg, st

    def test_lsv_shop_draws_35_mph_green(self):
        pg, st = self.renter("lsv")
        try:
            self.assertEqual(st["veh"], "lsv")
            self.assertGreater(st["colors"].get(GREEN, 0), 0, st)
            self.assertEqual(st["colors"].get(RED, 0), 0, st)
            self.assertIn("Street-legal LSV rules: roads up to 35 mph", pg.inner_text("#vehLegend"))
            self.assertIn("veh=lsv", pg.get_attribute("#fullMap", "href") or "")
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "beachmode_lsv.png"))
        finally:
            pg.close()

    def test_golf_cart_and_unset_shop_draw_35_mph_red(self):
        for v in ("golf_cart", None):
            pg, st = self.renter(v)
            try:
                self.assertEqual(st["veh"], "golf_cart")
                self.assertGreater(st["colors"].get(RED, 0), 0, st)
                self.assertEqual(st["colors"].get(GREEN, 0), 0, st)
                self.assertIn("Golf cart rules: roads up to 25 mph", pg.inner_text("#vehLegend"))
                if SHOTS and v:
                    pg.screenshot(path=os.path.join(SHOTS, "beachmode_golf_cart.png"))
            finally:
                pg.close()


if __name__ == "__main__":
    unittest.main()
