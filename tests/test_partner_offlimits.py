"""Off-limits zones end to end on the real partner Worker and real Pacific Beach roads.

The shop draws an area and saves it. A renter's ride goes around it. When the shop marks the
block around a stop, the renter is told before the ride, and the banner and voice warn on approach.
"""
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
A = (32.7965, -117.2540)
B = (32.8010, -117.2430)
MID = (32.79849, -117.24901)  # the middle of the plain A to B route (Cass / Garnet area)
SEED = {"slug": "beachmode", "name": "Beach Mode Rentals", "owner": "owner@example.com", "region_id": "sd",
        "shop": {"color": "#14b8c4", "vehicle": "golf_cart"},
        "codes": [{"code": "CART7", "multi_use": True}],
        "experiences": [{"title": "PB loop", "nearest_start": False, "stops": [
            {"label": "Crystal Pier side", "lat": A[0], "lon": A[1]},
            {"label": "Garnet tacos", "lat": B[0], "lon": B[1]}]}]}


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


def square(c, d):
    return [(c[0] - d, c[1] - d), (c[0] - d, c[1] + d), (c[0] + d, c[1] + d), (c[0] + d, c[1] - d)]


def draw(ap, kind, pts, name, note=""):
    ap.click("#offArea" if kind == "area" else "#offLine")
    for lat, lon in pts:
        p = ap.evaluate("([lat, lon]) => { const m = GCMOffAdmin.map(); const pt = m.latLngToContainerPoint([lat, lon]); const r = m.getContainer().getBoundingClientRect(); return [r.left + pt.x, r.top + pt.y]; }", [lat, lon])
        ap.mouse.click(p[0], p[1])
    ap.fill("#offName", name)
    ap.fill("#offNote", note)


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class OffLimits(unittest.TestCase):
    def renter(self, b, at):
        ctx = b.new_context(viewport={"width": 390, "height": 900}, geolocation={"latitude": at[0], "longitude": at[1]},
                            permissions=["geolocation"], timezone_id="America/Los_Angeles")
        rp = ctx.new_page()
        rp.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        return ctx, rp

    def route_hits(self, rp):
        return rp.evaluate("() => { const r = GCMNavDebug(); return r ? GCMOffLimits.routeHits(r.pts, window.__zones) : null; }")

    def test_shop_draws_a_zone_and_renter_routes_around_it(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            ap = b.new_page(viewport={"width": 1000, "height": 1400}, timezone_id="America/Los_Angeles")
            ap.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#offMap .leaflet-container, #offMap.leaflet-container")
            ap.evaluate("([lat, lon]) => GCMOffAdmin.map().setView([lat, lon], 16, {animate: false})", list(MID))
            ap.locator("#offCard").scroll_into_view_if_needed()
            draw(ap, "area", square(MID, 0.0007), "Block party", "Street closed for the block party.")
            self.assertIn("4 corners", ap.inner_text("#offHint"))
            shot(ap.locator("#offCard"), "offlimits-admin-draw.png")
            with ap.expect_response(lambda r: r.url.endswith("/shop/offlimits") and r.request.method == "POST") as resp:
                ap.click("#offSave")
            self.assertEqual(resp.value.status, 201, resp.value.text())
            ap.wait_for_function("() => document.body.innerText.includes('Area: Block party')")

            # Renter: the ride goes around the block. Nothing to warn about.
            ctx, rp = self.renter(b, A)
            rp.goto(dev.url + "/p/beachmode/go?code=CART7", wait_until="domcontentloaded")
            rp.wait_for_selector(".xcard")
            self.assertIn("off limits", rp.inner_text("#panel"))
            rp.click(".xcard")
            rp.wait_for_function("() => /legal|hop/.test((document.getElementById('routeNote')||{}).textContent || '')", timeout=60000)
            self.assertNotIn("\u26d4", rp.inner_text("#routeNote"))
            self.assertGreaterEqual(rp.locator("path.leaflet-interactive[fill='#e5484d']").count(), 1, "zone shaded on the map")
            shot(rp, "offlimits-renter-map.png")
            rp.evaluate("() => { window.__zones = []; }")
            rp.click("#startEx")
            rp.wait_for_selector("#navBanner.show", timeout=60000)
            zones = rp.evaluate("async () => (await (await fetch('/api/partner/public/beachmode/unlock?code=CART7')).json()).offlimits")
            rp.evaluate("z => { window.__zones = z; }", zones)
            self.assertEqual(self.route_hits(rp), [], "the turn-by-turn route stays out of the block")
            ctx.close()

            # Shop marks the block around stop 2: no way around, so the renter is told up front.
            ap.evaluate("([lat, lon]) => GCMOffAdmin.map().setView([lat, lon], 17, {animate: false})", list(B))
            draw(ap, "area", square(B, 0.0006), "Garnet block", "Walk in from Mission Blvd.")
            with ap.expect_response(lambda r: r.url.endswith("/shop/offlimits") and r.request.method == "POST") as resp:
                ap.click("#offSave")
            self.assertEqual(resp.value.status, 201)
            ap.wait_for_function("() => document.body.innerText.includes('Area: Garnet block')")
            shot(ap.locator("#offCard"), "offlimits-admin-list.png")

            ctx, rp = self.renter(b, A)
            rp.goto(dev.url + "/p/beachmode/go?code=CART7", wait_until="domcontentloaded")
            rp.wait_for_selector(".xcard")
            rp.click(".xcard")
            rp.wait_for_function("() => ((document.getElementById('routeNote')||{}).textContent || '').includes('\u26d4')", timeout=60000)
            note = rp.inner_text("#routeNote")
            self.assertIn("goes through Garnet block", note)
            self.assertIn("Stop 2 (Garnet tacos) is inside Garnet block", note)
            self.assertIn("Walk in from Mission Blvd.", note)
            self.assertNotIn("Block party", note)
            rp.locator("#routeNote").scroll_into_view_if_needed()
            shot(rp, "offlimits-renter-warning.png")
            rp.click("#startEx")
            rp.wait_for_selector("#navBanner.show", timeout=60000)
            self.assertFalse(rp.is_visible("#zoneBar"))
            ctx.set_geolocation({"latitude": B[0] - 0.00095, "longitude": B[1]})
            rp.wait_for_selector("#zoneBar:not([hidden])", timeout=15000)
            self.assertIn("Off limits ahead: Garnet block", rp.inner_text("#zoneBar"))
            ctx.set_geolocation({"latitude": B[0], "longitude": B[1] - 0.0002})
            rp.wait_for_function("() => document.getElementById('zoneBar').textContent.includes('You are in an off-limits area')", timeout=15000)
            shot(rp, "offlimits-renter-live.png")
            ctx.close()

            # Delete puts things back.
            ap.once("dialog", lambda d: d.accept())
            ap.locator("tr", has_text="Garnet block").locator("[data-zone-del]").click()
            ap.wait_for_function("() => !document.body.innerText.includes('Area: Garnet block')")
            b.close()


if __name__ == "__main__":
    unittest.main()
