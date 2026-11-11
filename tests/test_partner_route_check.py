"""While a shop adds stops, the editor shows miles, ride time, battery, and unreachable stops.

The numbers come from the same legal-road router as the renter page, for the shop's vehicle.
"""
import functools
import http.server
import os
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

SHOP = {
    "id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd",
    "blurb": "", "logo_url": "", "color": "", "owner_email": "owner@gmail.com",
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
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class RouteCheckSource(unittest.TestCase):
    def test_editor_asks_the_shared_router(self):
        with open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8") as f:
            admin = f.read()
        with open(os.path.join(PUB, "partner", "index.html"), encoding="utf-8") as f:
            page = f.read()
        for line in ("id=\"routeCheck\"", "GCMRouteCheck.check", "Checking legal roads...", "wireRouteCheck"):
            self.assertIn(line, admin)
            self.assertNotIn("\u2014", line)
        self.assertIn("/router.js", page)
        self.assertIn("/routecheck.js", page)
        self.assertIn("/roadrule.js", page)


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class RouteCheckEditor(unittest.TestCase):
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

    def open_admin(self):
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            if urlsplit(req.url).path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if urlsplit(req.url).path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": SHOP, "experiences": [], "affiliates": [], "places": [], "codes": []})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("#routeCheck")
        return pg

    def fill_stop(self, pg, i, label, lat, lon):
        row = pg.locator("#stopList .stop").nth(i)
        row.locator("[data-k=name]").fill(label)
        row.locator("[data-k=lat]").evaluate("(el, v) => { el.value = v; }", str(lat))
        row.locator("[data-k=lon]").evaluate("(el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); }", str(lon))

    def test_miles_time_battery_and_an_unreachable_stop(self):
        pg = self.open_admin()
        try:
            pg.wait_for_function("() => document.querySelector('#routeCheck').textContent.includes('Add two placed stops')")
            self.fill_stop(pg, 0, "South", 32.66683, -117.24285)
            pg.locator("#addStop").click()
            pg.wait_for_selector("#stopList .stop:nth-child(2)")
            self.fill_stop(pg, 1, "North", 32.67643, -117.24319)
            pg.wait_for_function(
                "() => /About \\d/.test(document.querySelector('#routeCheck').textContent) && document.querySelector('#routeCheck').textContent.includes('12 mph')",
                timeout=20000,
            )
            text = pg.locator("#routeCheck").inner_text()
            self.assertIn("30 mi charge", text)
            self.assertIn("golf cart", text)
            self.assertIn("Posted signs always take precedence.", text)
            self.assertNotIn("no legal", text)
            pg.select_option("#brandVehicle", "lsv")
            pg.wait_for_function(
                "() => document.querySelector('#routeCheck').textContent.includes('18 mph')",
                timeout=20000,
            )
            self.assertIn("street-legal LSV", pg.locator("#routeCheck").inner_text())
            pg.select_option("#brandVehicle", "golf_cart")
            pg.locator("#addStop").click()
            pg.wait_for_selector("#stopList .stop:nth-child(3)")
            self.fill_stop(pg, 2, "Offshore", 32.67, -117.55)
            pg.wait_for_function(
                "() => document.querySelector('#routeCheck').textContent.includes('Offshore')",
                timeout=20000,
            )
            flagged = pg.locator("#routeCheck").inner_text()
            self.assertIn("no legal golf cart route", flagged)
            self.assertIn("Offshore", flagged)
            for width in (1280, 375):
                pg.set_viewport_size({"width": width, "height": 900})
                spill = pg.evaluate(
                    """() => {
                      const vw = document.documentElement.clientWidth;
                      const el = document.querySelector('#routeCheck');
                      const r = el.getBoundingClientRect();
                      return Math.max(0, r.right - vw, -r.left);
                    }"""
                )
                self.assertLessEqual(spill, 1, "route check spills at %s" % width)
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.locator("#routeCheck").scroll_into_view_if_needed()
                pg.screenshot(path=os.path.join(SHOTS, "route-check.png"))
        finally:
            pg.close()
