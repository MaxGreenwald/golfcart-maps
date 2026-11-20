"""Rental-day welcome in the partner admin: add a renter, preview the email, and see the
booking listed with its email status. Runs the real partner Worker locally (renter email off,
which is how production starts)."""
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
SEED = {"slug": "lajollacartco", "name": "La Jolla Cart Co", "owner": "owner@example.com", "region_id": "sd",
        "shop": {"color": "#14b8c4", "return_by": "17:00",
                 "rental": {"return_spot": "Side lot on Prospect St", "rules": "Drivers 16 and up. Seat belts on.", "phone": "858-555-0100"}}}


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class WelcomeFlow(unittest.TestCase):
    def test_add_renter_preview_and_list(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1000, "height": 1000}, timezone_id="America/Los_Angeles")
            pg.route("**://photon.komoot.io/**", lambda r: r.abort())
            pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
            sign_in(pg, dev.url, "owner@example.com")
            pg.wait_for_selector("#bookingsCard")
            pg.wait_for_selector("#bkRows:has-text('No renters booked yet')")
            self.assertIn("Renter email is off for now", pg.inner_text("#bkState"))
            self.assertRegex(pg.input_value("#bkReturn"), r"^\d{4}-\d\d-\d\dT\d\d:\d\d$")
            pg.fill("#bkName", "Jamie Rivera")
            pg.fill("#bkEmail", "jamie@example.com")
            pg.fill("#bkPhone", "858-555-0199")
            pg.click("#previewBooking")
            pg.wait_for_selector("#bkPreview:not([hidden])")
            self.assertIn("Your La Jolla Cart Co cart map and return time", pg.inner_text("#bkSubject"))
            frame = pg.frame_locator("#bkFrame")
            self.assertIn("Hi Jamie", frame.locator("body").inner_text())
            body = frame.locator("body").inner_text()
            self.assertIn("Return by", body)
            self.assertIn("Golf carts may drive on roads posted 25 mph or less", body)
            self.assertIn("From the shop: Drivers 16 and up. Seat belts on.", body)
            self.assertIn("Posted signs always take precedence", body)
            self.assertNotIn("\u2014", body)
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.locator("#bookingsCard").screenshot(path=os.path.join(SHOTS, "welcome-preview.png"))
            pg.click("#addBooking")
            pg.wait_for_selector("#bkRows [data-booking]")
            self.assertIn("Saved. Email is off for now", pg.inner_text("#bkState"))
            row = pg.inner_text("#bkRows")
            self.assertIn("Jamie Rivera", row)
            self.assertIn("Email off: share the link", row)
            self.assertIn("Text: not set up", row)
            code = pg.locator("#bkRows code").first.inner_text()
            self.assertRegex(code, r"^[0-9A-Z]{7,8}$")
            pg.locator("#bkPreview").evaluate("e => e.hidden = true")
            if SHOTS:
                pg.locator("#bookingsCard").screenshot(path=os.path.join(SHOTS, "welcome-booked.png"))
            # The renter's link opens the shop map unlocked.
            rp = b.new_page()
            rp.goto(dev.url + "/p/lajollacartco/go?code=" + code, wait_until="domcontentloaded")
            rp.wait_for_selector(".yay")
            self.assertIn(code, rp.inner_text(".yay"))
            b.close()


if __name__ == "__main__":
    unittest.main()
