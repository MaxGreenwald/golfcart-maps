"""Sales mode end to end on the real partner Worker and real Pacific Beach roads.

A dealer turns on its sales page, sets the buy card, and makes a link for a buyer's address.
The buyer's page shows the legal roads in reach, which of the shop's places are in reach, and the
buy card. A wider reach brings La Jolla Cove in. A shop with sales off has no page.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_dev_server import PartnerDev, node_ok, sign_in

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
HOME = (32.7965, -117.2540)
SEED = {"slug": "beachmode", "name": "Beach Mode Carts", "owner": "owner@example.com", "region_id": "sd",
        "shop": {"color": "#14b8c4", "vehicle": "golf_cart", "phone": "619-555-0142"},
        "places": [{"name": "Crystal Pier", "category": "views", "lat": 32.7950, "lon": -117.2560},
                   {"name": "La Jolla Cove", "category": "views", "lat": 32.8475, "lon": -117.2742}]}
PHOTON = {"features": [{"geometry": {"coordinates": [HOME[1], HOME[0]]},
                        "properties": {"name": "4500 Ocean Blvd", "street": "Ocean Blvd", "housenumber": "4500", "city": "San Diego", "state": "California"}}]}


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


def geocoder(page):
    page.route("**/photon.komoot.io/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(PHOTON)))
    page.route("**/nominatim.openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    page.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class SalesMode(unittest.TestCase):
    def test_dealer_link_shows_reachable_roads_and_buy_card(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            # Off by default: no page.
            bp = b.new_page(viewport={"width": 1280, "height": 900})
            geocoder(bp)
            bp.goto(dev.url + "/s/beachmode", wait_until="domcontentloaded")
            bp.wait_for_selector(".msg")
            self.assertIn("no sales page", bp.inner_text(".msg"))

            ap = b.new_page(viewport={"width": 1000, "height": 1400})
            geocoder(ap)
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#salesCard")
            ap.check("#salesOn")
            ap.fill("#salesHeadline", "Your new neighborhood, by cart")
            ap.fill("#salesUrl", "http://beachmode.example/carts")
            ap.click("#saveSales")
            ap.wait_for_function("() => document.body.innerText.includes('must start with https://')")
            self.assertTrue(ap.is_checked("#salesOn"), "a failed save keeps the edits")
            self.assertEqual(ap.input_value("#salesHeadline"), "Your new neighborhood, by cart")
            ap.fill("#salesUrl", "https://beachmode.example/carts")
            ap.fill("#salesCta", "Shop carts at Beach Mode")
            ap.select_option("#salesReach", "3")
            with ap.expect_response(lambda r: r.url.endswith("/api/partner/shop") and r.request.method == "PATCH") as resp:
                ap.click("#saveSales")
            self.assertEqual(resp.value.status, 200, resp.value.text())
            ap.wait_for_selector("#salesCard")
            ap.fill("#salesAddr", "4500 Ocean")
            ap.wait_for_selector("#salesSugg div")
            ap.locator("#salesSugg div").first.dispatch_event("mousedown")
            ap.wait_for_selector("#salesLinkRow:not(.hidden)")
            link = ap.input_value("#salesLink")
            self.assertIn("/s/beachmode?at=32.7965%2C-117.254&home=4500+Ocean+Blvd", link)
            ap.locator("#salesCard").scroll_into_view_if_needed()
            shot(ap.locator("#salesCard"), "sales-admin.png")

            # Buyer opens the link.
            bp.goto(link, wait_until="domcontentloaded")
            bp.wait_for_selector("#stats:not([hidden])", timeout=60000)
            self.assertIn("4500 Ocean Blvd", bp.inner_text("#headline"))
            self.assertGreater(int(bp.inner_text("#roadMi")), 10)
            places = bp.inner_text("#places")
            self.assertRegex(places, r"Crystal Pier\s+0\.\d mi")
            self.assertRegex(places, r"La Jolla Cove\s+Not in reach")
            self.assertIn("within 3 miles", bp.inner_text("#ruleLine"))
            buy = bp.inner_text("#buyCard")
            self.assertIn("Your new neighborhood, by cart", buy)
            self.assertEqual(bp.get_attribute("#buyLink", "href"), "https://beachmode.example/carts")
            self.assertIn("Shop carts at Beach Mode", buy)
            self.assertEqual(bp.get_attribute("#buyCall", "href"), "tel:6195550142")
            self.assertIn("Call (619) 555-0142", buy)
            self.assertGreater(bp.evaluate("() => document.querySelectorAll('#map canvas').length"), 0, "reachable roads drawn")
            shot(bp, "sales-buyer-3mi.png")
            bp.click("#reachBtns button[data-mi='5']")
            bp.wait_for_function("() => /La Jolla Cove\\s+4\\.\\d mi/.test(document.getElementById('places').innerText)", timeout=60000)
            self.assertIn("within 5 miles", bp.inner_text("#ruleLine"))
            shot(bp, "sales-buyer-5mi.png")

            # Phone size.
            pp = b.new_page(viewport={"width": 390, "height": 1700})
            geocoder(pp)
            pp.goto(link, wait_until="domcontentloaded")
            pp.wait_for_selector("#stats:not([hidden])", timeout=60000)
            shot(pp, "sales-buyer-phone.png")
            b.close()


if __name__ == "__main__":
    unittest.main()
