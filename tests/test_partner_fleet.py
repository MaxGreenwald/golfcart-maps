"""Fleet stickers: a shop types its cart numbers, gets one code per cart, and prints a sheet
(six per page, PDF from the print dialog, or a PNG per page). Runs the real partner Worker
locally (scripts/partner_dev.mjs) so the codes come from the Worker, not a mock."""
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
SEED = {"slug": "lajollacartco", "name": "La Jolla Cart Co", "owner": "owner@example.com",
        "shop": {"color": "#0b6e86"}, "codes": [{"code": "DESKCODE"}]}


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class FleetStickers(unittest.TestCase):
    def test_make_cart_codes_print_sheet_and_png(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(accept_downloads=True, viewport={"width": 1000, "height": 900})
            pg = ctx.new_page()
            pg.route("**://photon.komoot.io/**", lambda r: r.abort())
            pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
            sign_in(pg, dev.url, "owner@example.com")
            pg.wait_for_selector("#fleetKit")
            self.assertTrue(pg.locator("#printFleet").is_disabled())
            pg.fill("#fleetCarts", "1-8")
            with pg.expect_popup() as pop:
                pg.click("#makeFleet")
            sheet = pop.value
            sheet.wait_for_selector("section.sticker svg")
            self.assertEqual(sheet.locator("section.sticker").count(), 8)
            self.assertEqual(sheet.locator(".page").count(), 2)
            html = sheet.content().replace("<wbr>", "")
            self.assertIn("Cart 8", sheet.inner_text("body"))
            self.assertIn(dev.url + "/p/lajollacartco/go?code=", html)
            self.assertNotIn("\u2014", sheet.inner_text("body"))
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                sheet.screenshot(path=os.path.join(SHOTS, "fleet-sheet.png"), full_page=True)
            with sheet.expect_download() as dl:
                sheet.click("[data-png='1']")
            d = dl.value
            self.assertTrue(d.suggested_filename.endswith("stickers-page-1.png"))
            path = d.path()
            with open(path, "rb") as f:
                head = f.read(24)
            self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
            width = int.from_bytes(head[16:20], "big")
            self.assertEqual(width, 1275)
            if SHOTS:
                d.save_as(os.path.join(SHOTS, "fleet-page-1.png"))
            sheet.close()
            pg.wait_for_selector("#fleetNote:has-text('8 carts have codes')")
            self.assertIn("Cart 3", pg.inner_text("#app"))
            self.assertFalse(pg.locator("#printFleet").is_disabled())
            pg.locator("#fleetKit").scroll_into_view_if_needed()
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "fleet-admin.png"))
            # Printing again keeps the same codes for the same carts.
            first = pg.inner_text("#app")
            pg.fill("#fleetCarts", "1-8")
            with pg.expect_popup() as pop2:
                pg.click("#makeFleet")
            pop2.value.wait_for_selector("section.sticker svg")
            pop2.value.close()
            pg.wait_for_selector(".msg.ok:has-text('0 new, 8 kept')")
            # The renter link from a sticker opens the brand page with the cart named.
            code = pg.locator(".code-cart:has-text('Cart 2')").locator("xpath=..").locator("code").inner_text()
            self.assertIn(code, first)
            rp = ctx.new_page()
            rp.goto(dev.url + "/p/lajollacartco/go?code=" + code, wait_until="domcontentloaded")
            rp.wait_for_selector(".yay")
            self.assertIn("cart 2", rp.inner_text(".yay"))
            b.close()


if __name__ == "__main__":
    unittest.main()
