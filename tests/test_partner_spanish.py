"""Spanish renter page and seasonal rides, end to end on the real partner Worker.

A phone set to Spanish opens the shop link in Spanish, sees the shop's Spanish cart rules and the
season dates, and can flip to English and back. A ride whose season is over (or not started) stays
off the renter page. The shop sets the dates in its admin and sees which rides are hidden today.
"""
import datetime
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from partner_dev_server import PartnerDev, node_ok, sign_in

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
STOP = {"label": "Seal Rock", "lat": 32.847, "lon": -117.278}
try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date()
except Exception:  # pragma: no cover
    TODAY = datetime.date.today()
D = lambda n: (TODAY + datetime.timedelta(days=n)).isoformat()
SEED = {
    "slug": "beachmode", "name": "Beach Mode Rentals", "owner": "owner@example.com", "region_id": "sd",
    "shop": {"color": "#14b8c4", "vehicle": "golf_cart", "rental": {
        "pickup": "Blue umbrellas", "return_by": "5:00 pm",
        "rules": "Drivers 16 and up. Seat belts on.",
        "rules_es": "Conductores de 16 años o más. Cinturón puesto."}},
    "codes": [{"code": "CART7", "multi_use": True}],
    "experiences": [
        {"title": "Seal loop", "description": "A short coastal loop", "stops": [STOP]},
        {"title": "Holiday lights", "description": "Lights on the bay", "stops": [STOP], "starts_on": D(-3), "ends_on": D(20)},
        {"title": "Summer sunset", "stops": [STOP], "starts_on": D(-200), "ends_on": D(-100)},
    ],
}
# English words that should not be left on a Spanish page (shop names and rides are translate="no").
ENGLISH = re.compile(r"\b(the|your|you|and|stops?|rides?|map|code|offers?|unlock|back|tap|start)\b", re.I)


def shot(target, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        target.screenshot(path=os.path.join(SHOTS, name))


LEFTOVERS = """() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const t = n.nodeValue.trim();
    if (!t) continue;
    let e = n.parentElement, skip = false, hidden = false;
    for (; e; e = e.parentElement) {
      if (e.getAttribute('translate') === 'no' || /^(SCRIPT|STYLE)$/.test(e.tagName)) skip = true;
      if (e.hidden || e.getAttribute('aria-hidden') === 'true') hidden = true;
    }
    if (!skip && !hidden && n.parentElement.closest('.leaflet-control-attribution') === null) out.push(t);
  }
  return out;
}"""


@unittest.skipIf(sync_playwright is None or not node_ok(), "needs playwright and node 22+ (browser CI job)")
class SpanishAndSeasonal(unittest.TestCase):
    def test_spanish_renter_page_and_seasonal_rides(self):
        with PartnerDev(SEED) as dev, sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(viewport={"width": 390, "height": 1500}, locale="es-MX", timezone_id="America/Los_Angeles")
            rp = ctx.new_page()
            rp.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())

            # Locked page: Spanish from the phone language.
            rp.goto(dev.url + "/p/beachmode", wait_until="domcontentloaded")
            rp.wait_for_selector("#unlockBtn")
            self.assertEqual(rp.evaluate("document.documentElement.lang"), "es")
            self.assertEqual(rp.inner_text("#unlockBtn"), "Desbloquear")
            self.assertEqual(rp.get_attribute("#codeIn", "placeholder"), "Código de acceso")
            self.assertIn("¿Te dieron un código en la tienda?", rp.inner_text("#panel"))
            self.assertIn("2 experiencias listas", rp.inner_text("#panel"), "the summer ride is out of season")
            self.assertEqual(rp.inner_text("#langBtn"), "English")
            left = [t for t in rp.evaluate(LEFTOVERS) if ENGLISH.search(t)]
            self.assertEqual(left, [], "English left on the locked page")
            shot(rp, "spanish-locked.png")

            # Unlocked: Spanish rules, season chip, out-of-season ride hidden.
            rp.goto(dev.url + "/p/beachmode/go?code=CART7", wait_until="domcontentloaded")
            rp.wait_for_selector(".xcard")
            panel = rp.inner_text("#panel")
            self.assertIn("Ya entraste", panel)
            self.assertIn("Reglas del carrito", panel)
            self.assertIn("Conductores de 16 años o más", panel)
            self.assertNotIn("Drivers 16 and up", panel)
            titles = rp.locator(".xtitle").all_inner_texts()
            self.assertEqual(sorted(titles), ["Holiday lights", "Seal loop"])
            chip = rp.inner_text(".chip.season")
            self.assertRegex(chip, r"^\d+ [a-z]{3} al \d+ [a-z]{3}$")
            self.assertIn("Lights on the bay", panel, "the shop's own words are not translated")
            left = [t for t in rp.evaluate(LEFTOVERS) if ENGLISH.search(t)]
            self.assertEqual(left, [], "English left on the unlocked page")
            rp.locator("#rentalCard").scroll_into_view_if_needed()
            shot(rp, "spanish-unlocked.png")
            rp.locator(".chip.season").scroll_into_view_if_needed()
            shot(rp, "spanish-seasonal-ride.png")

            # Flip to English: same page, English words and rules, remembered on reload.
            rp.click("#langBtn")
            rp.wait_for_function("() => document.documentElement.lang === 'en'")
            panel = rp.inner_text("#panel")
            self.assertIn("You\u2019re in", panel)
            self.assertIn("Drivers 16 and up", panel)
            self.assertRegex(rp.inner_text(".chip.season"), r"^[A-Z][a-z]{2} \d+ to [A-Z][a-z]{2} \d+$")
            rp.reload(wait_until="domcontentloaded")
            rp.wait_for_selector(".xcard")
            self.assertEqual(rp.evaluate("document.documentElement.lang"), "en")
            self.assertIn("experiences", rp.inner_text("#panel").lower())
            shot(rp, "english-unlocked.png")
            # ?lang=es wins over the saved English.
            rp.goto(dev.url + "/p/beachmode/go?code=CART7&lang=es", wait_until="domcontentloaded")
            rp.wait_for_selector(".xcard")
            self.assertIn("experiencias", rp.inner_text("#panel").lower())
            ctx.close()

            # Admin: dates on the form, hidden-today badge, and a saved season.
            ap = b.new_page(viewport={"width": 1000, "height": 1600}, timezone_id="America/Los_Angeles")
            ap.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
            sign_in(ap, dev.url, "owner@example.com")
            ap.wait_for_selector("#exFrom")
            ap.wait_for_selector(".ex-season")
            seasons = ap.locator(".ex-season").all_inner_texts()
            self.assertEqual(len(seasons), 2)
            self.assertTrue(any("Hidden from renters today" in s for s in seasons))
            self.assertTrue(any("Hidden" not in s for s in seasons))
            self.assertIn("Cart rules in Spanish", ap.inner_text("body"))
            self.assertEqual(ap.input_value("#rentalRulesEs"), SEED["shop"]["rental"]["rules_es"])
            row = ap.locator("tr", has_text="Seal loop")
            row.locator("[data-edit-ex]").click()
            ap.fill("#exFrom", D(30))
            ap.fill("#exUntil", D(60))
            with ap.expect_response(lambda r: "/shop/experiences/" in r.url and r.request.method == "PATCH") as resp:
                ap.click("#addEx")
            self.assertEqual(resp.value.status, 200)
            body = resp.value.json()
            self.assertEqual((body["experience"]["starts_on"], body["experience"]["ends_on"]), (D(30), D(60)))
            ap.wait_for_function("() => document.querySelectorAll('.ex-season').length === 3")
            ap.locator(".ex-season").first.scroll_into_view_if_needed()
            shot(ap, "seasonal-admin.png")
            # Bad order is refused with a plain reason.
            row = ap.locator("tr", has_text="Holiday lights")
            row.locator("[data-edit-ex]").click()
            ap.fill("#exFrom", D(10))
            ap.fill("#exUntil", D(5))
            ap.click("#addEx")
            ap.wait_for_function("() => document.body.innerText.includes('Show until is before show from')")
            ap.locator("#exFrom").scroll_into_view_if_needed()
            shot(ap, "seasonal-admin-form.png")
            b.close()


if __name__ == "__main__":
    unittest.main()
