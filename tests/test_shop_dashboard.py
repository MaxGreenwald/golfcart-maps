"""Partner admin shop activity card: unlocks per code, rides, and offer taps.

Run: python3 tests/test_shop_dashboard.py   (SHOTS_DIR=/tmp/x to save screenshots)
"""
import functools
import http.server
import json
import os
import re
import socketserver
import threading
import unittest
from urllib.parse import urlsplit, parse_qs

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR")

SHOP = {
    "id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd",
    "blurb": "", "logo_url": "", "color": "", "owner_email": "brian@gmail.com",
    "disabled": False, "vehicle": "lsv",
}
STATS = {
    "ready": True, "shop": "beachmode", "days": 30,
    "totals": {"unlocks": 4, "started": 3, "finished": 2, "affiliate_taps": 5},
    "daily": [
        {"day": "2026-11-09", "unlocks": 2, "started": 2, "finished": 1, "affiliate_taps": 3},
        {"day": "2026-11-08", "unlocks": 2, "started": 1, "finished": 1, "affiliate_taps": 2},
    ],
    "codes": [{"code": "ab12cd3", "unlocks": 3}, {"code": "zz99", "unlocks": 1}],
    "rides": [{"ride": "e1", "started": 3, "finished": 2}],
    "pins": [{"pin": "a1", "taps": 5}],
}
BUNDLE = {
    "shop": SHOP,
    "experiences": [{"id": "e1", "title": "Sunset loop", "description": "", "stops": [], "nearest_start": True}],
    "affiliates": [{"id": "a1", "name": "Taco Shack", "lat": 32.8, "lon": -117.25, "offer": "chips", "coupon": ""}],
    "places": [],
    "codes": [{"code": "AB12CD3", "uses": 3, "max_uses": 0, "multi_use": 1, "expires_at": None}],
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


def shot(page, name, locator=None):
    if not SHOTS:
        return
    os.makedirs(SHOTS, exist_ok=True)
    target = locator or page
    target.screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ShopDashboard(unittest.TestCase):
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

    def _admin(self, page, stats):
        seen = []

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "brian@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json=BUNDLE)
            if path == "/api/partner/shop/stats":
                qs = parse_qs(urlsplit(req.url).query)
                seen.append(qs.get("days", ["30"])[0])
                body = dict(stats)
                if seen[-1] == "7":
                    body = dict(stats, days=7,
                                totals={"unlocks": 1, "started": 1, "finished": 0, "affiliate_taps": 1},
                                daily=[{"day": "2026-11-09", "unlocks": 1, "started": 1, "finished": 0, "affiliate_taps": 1}],
                                codes=[{"code": "ab12cd3", "unlocks": 1}],
                                rides=[{"ride": "e1", "started": 1, "finished": 0}],
                                pins=[{"pin": "a1", "taps": 1}])
                return route.fulfill(json=body)
            route.fallback()

        page.route("**/api/partner/**", handle)
        page.route("**://photon.komoot.io/**", lambda r: r.abort())
        page.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        page.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        return seen

    def test_dashboard_labels_codes_rides_and_offers(self):
        pg = self.b.new_page(viewport={"width": 1100, "height": 1400})
        seen = self._admin(pg, STATS)
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#dashTotals")
            text = pg.inner_text("#shopDash")
            self.assertIn("Shop activity", text)
            self.assertIn("Test installs are left out.", text)
            self.assertIn("Unlocks", text)
            self.assertRegex(pg.inner_text("#dashTotals"), r"4")
            self.assertIn("AB12CD3", pg.inner_text("#dashCodes"))
            self.assertNotIn("ab12cd3", pg.inner_text("#dashCodes"))
            self.assertIn("ZZ99", pg.inner_text("#dashCodes"))
            self.assertIn("Sunset loop", pg.inner_text("#dashRides"))
            self.assertIn("Taco Shack", pg.inner_text("#dashPins"))
            self.assertIn("2026-11-09", pg.inner_text("#dashDays"))
            shot(pg, "shop-dashboard.png", pg.locator("#shopDash"))
            pg.set_viewport_size({"width": 390, "height": 844})
            shot(pg, "shop-dashboard-phone.png", pg.locator("#shopDash"))
            pg.set_viewport_size({"width": 1100, "height": 1400})
            pg.click("#dashRange [data-dash-days='7']")
            pg.wait_for_function("() => { const el = document.querySelector('#dashTotals'); return !!(el && el.innerText.includes('0')); }")
            self.assertIn("7", seen)
            self.assertIn("1", pg.inner_text("#dashCodes"))
            self.assertNotIn("ZZ99", pg.inner_text("#dashCodes"))
        finally:
            pg.close()

    def test_dashboard_says_when_analytics_is_not_connected(self):
        pg = self.b.new_page(viewport={"width": 1100, "height": 900})
        self._admin(pg, {"ready": False, "shop": "beachmode", "reason": "not_configured"})
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#dashEmpty")
            self.assertIn("after the analytics connection is set", pg.inner_text("#dashEmpty"))
            self.assertEqual(pg.locator("#dashTotals").count(), 0)
        finally:
            pg.close()

    def test_renter_unlock_records_a_shop_event(self):
        pg = self.b.new_page(viewport={"width": 1100, "height": 800})
        pg.add_init_script("window.__sent=[];window.GCM_TRACK_SINK=function(o){window.__sent.push(o)};try{Object.defineProperty(navigator,'webdriver',{configurable:true,get:()=>false})}catch(e){}")

        def handle(route):
            path = urlsplit(route.request.url).path
            if path.endswith("/unlock"):
                return route.fulfill(json={
                    "unlocked": True, "code": "AB12CD3", "grant": "g",
                    "shop": SHOP,
                    "experiences": [], "affiliates": [], "places": [],
                })
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/p/beachmode/go?code=AB12CD3", wait_until="domcontentloaded")
            pg.wait_for_function("window.__sent && window.__sent.some(function(o){return o.e==='partner_unlock'})", timeout=15000)
            ev = pg.evaluate("window.__sent.filter(function(o){return o.e==='partner_unlock'})")
            self.assertEqual(ev[0]["p"]["shop"], "beachmode")
            self.assertEqual(ev[0]["p"]["code"], "ab12cd3")
            self.assertEqual(ev[0]["t"], "sd")
            self.assertNotIn("internal", ev[0])
        finally:
            pg.close()
