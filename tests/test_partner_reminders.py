"""Return-time reminders, end to end on the real partner Worker (renter email off, which is
how production starts): the shop picks how long before return to nudge, books a renter, and
the renter's map shows "Head back" for that renter's own return time with a "Route me back"
button that starts a legal route to the return spot."""
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_dev_server import PartnerDev, node_ok, sign_in, ROOT

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
LA = ZoneInfo("America/Los_Angeles")
START = {"latitude": 32.7980, "longitude": -117.2466}
SPOT = {"lat": 32.7966, "lon": -117.2545}
SEED = {"slug": "beachmode", "name": "Beach Mode Rentals", "owner": "owner@example.com", "region_id": "sd",
        "shop": {"color": "#14b8c4", "return_by": "23:30", "return_lat": SPOT["lat"], "return_lon": SPOT["lon"],
                 "rental": {"return_spot": "Crystal Pier lot", "phone": "858-555-0100"}},
        "experiences": [{"title": "Pier loop", "stops": [{"label": "Crystal Pier Entrance", "lat": 32.7966, "lon": -117.2545}]}]}


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class ReturnReminders(unittest.TestCase):
    def test_shop_lead_time_booking_banner_and_route_back(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 1000, "height": 1100}, timezone_id="America/Los_Angeles")
            pg.route("**://photon.komoot.io/**", lambda r: r.abort())
            pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
            pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            sign_in(pg, dev.url, "owner@example.com")
            pg.wait_for_selector("#rentRemindMin")
            self.assertEqual(pg.input_value("#rentRemindMin"), "15")
            pg.select_option("#rentRemindMin", "30")
            pg.click("#saveReminders")
            pg.wait_for_function("() => document.body.innerText.includes('Reminders saved')", timeout=8000)
            pg.wait_for_selector("#rentRemindMin")
            self.assertEqual(pg.input_value("#rentRemindMin"), "30")
            self.assertNotIn("\u2014", pg.inner_text("#rentalCard"))
            shot(pg.locator("#rentalCard"), "reminders-admin.png")

            due = datetime.now(LA) + timedelta(minutes=20)
            pg.fill("#bkName", "Jamie Rivera")
            pg.fill("#bkEmail", "jamie@example.com")
            pg.fill("#bkReturn", due.strftime("%Y-%m-%dT%H:%M"))
            pg.click("#addBooking")
            pg.wait_for_selector("#bkRows [data-remind]")
            self.assertIn("Reminder email off", pg.inner_text("#bkRows"))
            code = pg.locator("#bkRows code").first.inner_text()
            pg.locator("#bkPreview").evaluate("e => e.hidden = true")
            shot(pg.locator("#bookingsCard"), "reminders-booking.png")

            # The shop's daily return-by is 11:30 PM, so only the booked 20-minute return can nudge.
            ctx = b.new_context(viewport={"width": 390, "height": 844}, geolocation=START, permissions=["geolocation"],
                                timezone_id="America/Los_Angeles")
            rp = ctx.new_page()
            rp.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            rp.route("**://basemaps.cartocdn.com/**", lambda r: r.abort())
            rp.goto(dev.url + "/p/beachmode/go?code=" + code, wait_until="domcontentloaded")
            rp.wait_for_selector("#nudgeBar:not([hidden])", timeout=30000)
            self.assertRegex(rp.inner_text("#nudgeBar .nudge-text"), r"Head back in \d+ minutes?\.")
            rp.wait_for_selector("#nudgeBack")
            shot(rp, "reminders-banner.png")
            rp.click("#nudgeBack")
            rp.wait_for_selector("#goPane:not([hidden])")
            rp.wait_for_function("() => /mi on legal golf cart roads|risky/.test(document.getElementById('goNote').textContent)", timeout=30000)
            self.assertEqual(rp.input_value("#goQ"), "Return spot: Crystal Pier lot")
            self.assertEqual(rp.locator("#nudgeBack").count(), 0, "no second button while routing back")
            shot(rp, "reminders-route-back.png")
            ctx.close()
            b.close()

    def test_reminder_email_renders(self):
        script = (
            "import('./lib/partner_bookings.js').then(m => { const at = Math.floor(Date.UTC(2026,10,20,1,0)/1000);"
            "const shop = { name: 'Beach Mode Rentals', color: '#14b8c4', return_lat: 32.79, return_lon: -117.25, rental: { return_spot: 'Crystal Pier lot', phone: '8585550100' } };"
            "const e = m.reminderEmail({ shop, booking: { renter_name: 'Jamie Rivera', return_at: at, tz: 'America/Los_Angeles' }, link: m.backLink('https://golfcartmap.com', 'beachmode', 'ABCD'), minutes: 30 });"
            "process.stdout.write(JSON.stringify(e)); })"
        )
        out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, cwd=ROOT, check=True)
        e = json.loads(out.stdout)
        self.assertEqual(e["subject"], "Head back soon: your Beach Mode Rentals cart is due at 5:00 PM")
        self.assertIn("Route me back", e["html"])
        self.assertNotIn("\u2014", e["html"] + e["text"])
        if sync_playwright is None:
            return
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page(viewport={"width": 600, "height": 560})
            pg.set_content(e["html"])
            self.assertIn("due back in about 30 minutes", pg.inner_text("body"))
            shot(pg, "reminders-email.png")
            b.close()


if __name__ == "__main__":
    unittest.main()
