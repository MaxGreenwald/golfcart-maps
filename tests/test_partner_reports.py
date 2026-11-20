"""Problem reports end to end on the real partner Worker: a renter taps "Report a problem",
sends a cart number and what happened, and the shop sees it in the admin and marks it fixed.
Runs once with photos off (no R2, how production starts) and once with an in-memory photo
store to show the photo path."""
import os
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_dev_server import PartnerDev, node_ok, sign_in

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
SEED = {"slug": "beachmode", "name": "Beach Mode Rentals", "owner": "owner@example.com", "region_id": "sd",
        "shop": {"color": "#14b8c4", "rental": {"return_spot": "Side lot", "phone": "858-555-0100"}},
        "codes": [{"code": "CART7", "multi_use": True}]}


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


def tiny_png(path):
    w, h = 40, 30
    raw = b"".join(b"\x00" + bytes([200, 60, 40]) * w for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def renter_page(b, url):
    ctx = b.new_context(viewport={"width": 390, "height": 1000}, timezone_id="America/Los_Angeles")
    pg = ctx.new_page()
    pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
    pg.goto(url + "/p/beachmode/go?code=CART7", wait_until="domcontentloaded")
    pg.wait_for_selector("#rpOpen")
    return ctx, pg


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class ProblemReports(unittest.TestCase):
    def test_renter_reports_without_photos_and_shop_marks_fixed(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx, pg = renter_page(b, dev.url)
            pg.click("#rpOpen")
            pg.wait_for_selector("#rpForm:not([hidden])")
            pg.wait_for_timeout(300)
            self.assertTrue(pg.locator("#rpPhotoRow").is_hidden(), "no photo field while photos are off")
            pg.click("#rpSend")
            self.assertIn("Pick what happened", pg.inner_text("#rpMsg"))
            pg.fill("#rpCart", "7")
            pg.select_option("#rpKind", "flat")
            pg.fill("#rpNote", "Rear left tire is flat near the pier.")
            pg.fill("#rpPhone", "858-555-0199")
            pg.locator("#rpKind").scroll_into_view_if_needed()
            shot(pg, "report-renter-form.png")
            pg.click("#rpSend")
            pg.wait_for_function("() => /^Sent\\./.test(document.getElementById('rpMsg').textContent)")
            msg = pg.inner_text("#rpMsg")
            self.assertIn("Beach Mode Rentals has your report for cart 7.", msg)
            self.assertIn("call (858) 555-0100", msg)
            self.assertNotIn("\u2014", pg.inner_text("#reportCard"))
            pg.locator("#rpMsg").scroll_into_view_if_needed()
            shot(pg, "report-renter-sent.png")
            ctx.close()

            ap = b.new_page(viewport={"width": 1000, "height": 900})
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#rpRows [data-report]")
            row = ap.inner_text("#rpRows")
            self.assertIn("Cart 7", row)
            self.assertIn("Flat tire", row)
            self.assertIn("Rear left tire is flat near the pier.", row)
            self.assertIn("(858) 555-0199", row)
            self.assertIn("No photo", row)
            self.assertIn("Email off", row)
            state = ap.inner_text("#rpState")
            self.assertIn("1 open report.", state)
            self.assertIn("Photos are off for now", state)
            shot(ap.locator("#reportsCard"), "report-admin-list.png")
            ap.click("[data-rp-fix]")
            ap.wait_for_selector("#rpRows:has-text('No open reports.')")
            ap.check("#rpShowFixed")
            ap.wait_for_selector("[data-rp-open]")
            b.close()

    def test_photo_saved_when_photo_storage_is_on(self):
        with PartnerDev(SEED, env={"DEV_MEMORY_MEDIA": "1"}) as dev, sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
            img = os.path.join(tmp, "cart.png")
            tiny_png(img)
            b = pw.chromium.launch()
            ctx, pg = renter_page(b, dev.url)
            pg.click("#rpOpen")
            pg.wait_for_selector("#rpPhotoRow:not([hidden])")
            pg.fill("#rpCart", "A-3")
            pg.select_option("#rpKind", "damage")
            pg.fill("#rpNote", "Cracked windshield.")
            pg.set_input_files("#rpPhoto", img)
            pg.click("#rpSend")
            pg.wait_for_function("() => /^Sent\\./.test(document.getElementById('rpMsg').textContent)")
            self.assertNotIn("could not be saved", pg.inner_text("#rpMsg"))
            ctx.close()
            ap = b.new_page(viewport={"width": 1000, "height": 900})
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#rpRows img.rp-thumb")
            ap.wait_for_function("() => { const i = document.querySelector('#rpRows img.rp-thumb'); return i && i.complete && i.naturalWidth > 0; }")
            self.assertNotIn("Photos are off", ap.inner_text("#rpState"))
            shot(ap.locator("#reportsCard"), "report-admin-photo.png")
            b.close()


if __name__ == "__main__":
    unittest.main()
