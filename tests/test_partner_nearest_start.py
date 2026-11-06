"""Nearest-stop start on the renter page (Max, Oct 31 2026, t441u).

A Beach Mode-like test ride (six stops from Crystal Pier north toward La Jolla), with the rider
parked near stop 4. With the setting on, Start begins at stop 4 and the pins renumber to the visit
order; "Use shop order" goes back to 1..6. With the setting off the shop order is kept.
The admin experience editor shows the checkbox on by default and saves it off.
"""
import functools
import json
import os
import threading
import unittest
from urllib.parse import urlsplit

from test_partner_vehicle import _Quiet, _S, shop, PUB, SHOTS

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

STOPS = [("Crystal Pier", 32.7963, -117.2559), ("Law Street Beach", 32.8005, -117.2558),
         ("Tourmaline Surf Park", 32.8053, -117.2622), ("Bird Rock Coffee", 32.8130, -117.2700),
         ("Windansea Beach", 32.8302, -117.2810), ("La Jolla Cove", 32.8504, -117.2717)]
RIDER = {"latitude": 32.8135, "longitude": -117.2690}  # north of stop 1, next to stop 4


def exp(nearest=None):
    e = {"id": "e1", "shop_id": "s1", "title": "PB to La Jolla test ride", "description": "",
         "stops": [{"label": n, "lat": la, "lon": lo} for n, la, lo in STOPS]}
    if nearest is not None:
        e["nearest_start"] = nearest
    return e


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class NearestStart(unittest.TestCase):
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

    def renter(self, ex):
        ctx = self.b.new_context(viewport={"width": 390, "height": 844}, geolocation=RIDER, permissions=["geolocation"])
        pg = ctx.new_page()

        def handle(route):
            if urlsplit(route.request.url).path.endswith("/unlock"):
                return route.fulfill(json={"unlocked": True, "shop": shop(vehicle="lsv"), "experiences": [ex], "affiliates": [], "code": "TEST123"})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.goto(self.base + "/p/beachmode/go?code=TEST123", wait_until="domcontentloaded")
        pg.wait_for_selector("#startEx", timeout=60000)
        pg.wait_for_function("typeof roadApi !== 'undefined' && roadApi && roadApi.segments().length > 0", timeout=60000)
        return ctx, pg

    def pins(self, pg):
        # Pin number -> stop at that pin, read from the popup text of each numbered marker.
        return pg.evaluate("""() => { const out = {}; pins.eachLayer(m => { const p = m.getPopup && m.getPopup();
          const t = p && String(p.getContent()); const g = t && t.match(/^<b>(\\d+)\\. ([^<]+)<\\/b>/); if (g) out[g[1]] = g[2]; }); return out; }""")

    def start(self, pg):
        pg.click("#startEx")
        pg.wait_for_function("document.getElementById('startEx').textContent === 'Start experience'", timeout=60000)
        pg.wait_for_timeout(1200)

    def test_on_starts_at_nearest_and_renumbers(self):
        ctx, pg = self.renter(exp())  # no field: older row reads as on
        try:
            self.start(pg)
            self.assertIn("Starting at your nearest stop", pg.inner_text("#navOrder"))
            got = self.pins(pg)
            self.assertEqual(got["1"], "Bird Rock Coffee")
            self.assertEqual(sorted(got.values()), sorted(n for n, _, _ in STOPS))
            self.assertIn("Bird Rock Coffee", pg.inner_text("#nextLabel"))
            self.assertIn("Stop 1/6", pg.inner_text("#nextLabel"))
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "nearest_on.png"))
                pg.set_viewport_size({"width": 1280, "height": 900})
                pg.wait_for_timeout(800)
                pg.evaluate("() => { if (follow) follow.pause(); map.fitBounds(L.latLngBounds(activeEx.stops.map(s => [s.lat, s.lon])).extend([%f, %f]), {padding: [30, 30], animate: false}); }" % (RIDER["latitude"], RIDER["longitude"]))
                pg.wait_for_timeout(1500)
                pg.screenshot(path=os.path.join(SHOTS, "nearest_pins.png"))
            pg.click("#navOrder .order-toggle")
            pg.wait_for_function("document.getElementById('navOrder').textContent.includes('shop’s order')", timeout=60000)
            pg.wait_for_timeout(1200)
            got = self.pins(pg)
            self.assertEqual([got[str(i + 1)] for i in range(6)], [n for n, _, _ in STOPS])
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "nearest_shop_order.png"))
        finally:
            ctx.close()

    def test_off_keeps_shop_order(self):
        ctx, pg = self.renter(exp(False))
        try:
            self.start(pg)
            self.assertTrue(pg.locator("#orderNote").is_hidden())
            got = self.pins(pg)
            self.assertEqual([got[str(i + 1)] for i in range(6)], [n for n, _, _ in STOPS])
            self.assertIn("Crystal Pier", pg.inner_text("#nextLabel"))
        finally:
            ctx.close()

    def test_admin_checkbox_default_on_and_saves_off(self):
        row = shop()
        bundle = {"shop": row, "experiences": [], "affiliates": [], "codes": []}
        posted = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
            if path == "/api/partner/shop" and req.method == "GET":
                return route.fulfill(json=bundle)
            if path == "/api/partner/shop/experiences" and req.method == "POST":
                body = json.loads(req.post_data or "{}")
                posted.append(body)
                bundle["experiences"] = [dict(body, id="e9", shop_id="s1")]
                return route.fulfill(json={"experience": bundle["experiences"][0]}, status=201)
            route.fallback()

        pg.route("**/api/partner/**", handle)
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#exNearest")
            self.assertTrue(pg.is_checked("#exNearest"))
            self.assertIn("Start riders at their nearest stop", pg.inner_text("label.ns-row"))
            self.assertEqual(pg.inner_text("#exNearestHelp"), "Off: riders follow your exact order")
            pg.fill("#exTitle", "Test ride")
            self._fill_stop(pg)
            pg.uncheck("#exNearest")
            pg.click("#addEx")
            pg.wait_for_function("document.querySelector('.ex-order') !== null", timeout=15000)
            self.assertIs(posted[-1]["nearest_start"], False)
            self.assertIn("Riders follow your exact order", pg.inner_text(".ex-order"))
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "admin_nearest.png"), full_page=True)
        finally:
            pg.close()

    def _fill_stop(self, pg):
        # Same hidden fields the pin picker writes.
        pg.evaluate("""() => { const r = document.querySelector('#stopList .stop');
          const set = (sel, v) => { const el = r.querySelector(sel); if (el) el.value = v; };
          set('[data-k=name]', 'Crystal Pier'); set('[data-k=lat]', '32.7963'); set('[data-k=lon]', '-117.2559'); }""")
