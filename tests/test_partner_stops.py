"""Partner stops with referral counts: a renter opens a partner offer or a place to see and taps
"Take me there" (a legal route through the shared free-route nav); the shop dashboard shows
opens and navigations per partner stop. Events carry ids only."""
import os
import sys
import unittest
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_shop_dashboard as D

PLACE = {"id": "p1", "name": "Pier Overlook", "category": "view", "lat": 32.8, "lon": -117.258, "note": "", "link": ""}
AFF = {"id": "a1", "name": "Taco Shack", "lat": 32.7975, "lon": -117.2525, "offer": "Free chips", "coupon": "CART"}


@unittest.skipIf(D.sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class PartnerStops(D.ShopDashboard):
    # Reuse the server and browser setup only; the dashboard tests run from their own module.
    test_dashboard_labels_codes_rides_and_offers = None
    test_dashboard_says_when_analytics_is_not_connected = None
    test_renter_unlock_records_a_shop_event = None
    test_renter_open_ride_and_stop_record_shop_events = None

    def test_dashboard_lists_partner_stops_with_opens_and_navigations(self):
        stats = dict(D.STATS, totals=dict(D.STATS["totals"], partner_navs=4, place_opens=3),
                     partner_stops=[{"pin": "a1", "opens": 5, "navs": 3}, {"pin": "p1", "opens": 3, "navs": 1}])
        old = (D.BUNDLE["places"], D.BUNDLE["affiliates"])
        D.BUNDLE["places"] = [PLACE]
        D.BUNDLE["affiliates"] = [dict(D.BUNDLE["affiliates"][0], coupon="CART")]
        pg = self.b.new_page(viewport={"width": 1100, "height": 1600})
        self._admin(pg, stats)
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#dashPins tbody tr td")
            pg.wait_for_function("() => /Pier Overlook/.test(document.getElementById('dashPins').innerText)")
            t = pg.inner_text("#dashPins")
            self.assertIn("Partner stop", t)
            self.assertIn("Take me there", t)
            self.assertIn("Taco Shack", t)
            self.assertIn("Offer (coupon CART)", t)
            self.assertIn("Place to see", t)
            rows = pg.locator("#dashPins tbody tr")
            self.assertEqual(rows.nth(0).locator("td").nth(1).inner_text(), "5")
            self.assertEqual(rows.nth(0).locator("td").nth(2).inner_text(), "3")
            self.assertIn("Partner navigations", pg.inner_text("#dashTotals2"))
            self.assertNotIn("\u2014", pg.inner_text("#shopDash"))
            D.shot(pg, "partner-stops-dashboard.png", pg.locator("#dashPins"))
        finally:
            D.BUNDLE["places"], D.BUNDLE["affiliates"] = old
            pg.close()

    def test_renter_open_and_take_me_there_record_ids_only(self):
        pg = self.b.new_page(viewport={"width": 1100, "height": 800})
        pg.add_init_script("window.__sent=[];window.GCM_TRACK_SINK=function(o){window.__sent.push(o)};try{Object.defineProperty(navigator,'webdriver',{configurable:true,get:()=>false})}catch(e){}")

        def handle(route):
            if urlsplit(route.request.url).path.endswith("/unlock"):
                return route.fulfill(json={"unlocked": True, "code": "AB12CD3", "grant": "g", "shop": D.SHOP,
                                           "experiences": [], "affiliates": [AFF], "places": [PLACE]})
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/p/beachmode/go?code=AB12CD3", wait_until="domcontentloaded")
            pg.wait_for_selector(".ocard[data-place='p1']")
            pg.click(".ocard[data-place='p1']")
            pg.wait_for_function("window.__sent.some(function(o){return o.e==='place_opened'})")
            ev = pg.evaluate("window.__sent.filter(function(o){return o.e==='place_opened'})")
            self.assertEqual(ev[-1]["p"], {"shop": "beachmode", "pin": "p1"})
            pg.click(".ocard[data-af='a1']")
            pg.wait_for_selector(".leaflet-popup [data-go-pin='a1']")
            D.shot(pg, "partner-stops-popup.png")
            pg.click(".leaflet-popup [data-go-pin='a1']")
            pg.wait_for_function("window.__sent.some(function(o){return o.e==='partner_nav'})")
            nav = pg.evaluate("window.__sent.filter(function(o){return o.e==='partner_nav'})")
            self.assertEqual(nav[-1]["p"], {"shop": "beachmode", "pin": "a1"})
            pg.wait_for_selector("#goPane:not([hidden])")
            self.assertEqual(pg.input_value("#goQ"), "Taco Shack")
            self.assertEqual(pg.get_attribute("#goMode [data-mode='legal']", "aria-pressed"), "true")
            for o in pg.evaluate("window.__sent"):
                self.assertNotIn("lat", o.get("p", {}))
                self.assertNotIn("name", o.get("p", {}))
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
