"""Shop admin can edit an experience stop and reorder stops. The save is a PATCH.

Same body as create: title, description, stops. Order is the stop list order.
The next GET is what the list and the editor show, so a reload keeps the edit.
"""
import functools
import http.server
import json
import os
import socketserver
import threading
import unittest
from urllib.parse import urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # unit-test CI job has no browser; the browser job runs this file
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")

STOPS = [
    {"label": "Seals", "lat": 32.85012, "lon": -117.26011, "note": "Morning"},
    {"label": "Cove", "lat": 32.84021, "lon": -117.27031, "note": "Swim"},
    {"label": "Pier", "lat": 32.87033, "lon": -117.25044, "note": "Sunset"},
]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.rstrip("/") == "/partner":
            path = "/partner/index.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def shop():
    return {
        "id": "s1",
        "slug": "lajollacartco",
        "name": "La Jolla Cart Co",
        "region_id": "sd",
        "blurb": "Coastal loops",
        "logo_url": "",
        "color": "",
        "owner_email": "owner@gmail.com",
        "disabled": False,
    }


def experience():
    return {
        "id": "ex1",
        "title": "La Jolla seals joyride",
        "description": "A coastal loop",
        "stops": json.loads(json.dumps(STOPS)),
    }


def form_stops(pg):
    return pg.evaluate(
        """() => [...document.querySelectorAll('#stopList .stop')].map(row => ({
          name: row.querySelector('[data-k=name]').value,
          label: row.querySelector('[data-k=label]').value,
          note: row.querySelector('[data-k=note]').value,
          lat: row.querySelector('[data-k=lat]').value,
          lon: row.querySelector('[data-k=lon]').value,
        }))"""
    )


class ExperienceStopSource(unittest.TestCase):
    def test_admin_has_edit_and_reorder_controls(self):
        with open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8") as f:
            admin = f.read()
        for line in (
            "Move up",
            "Move down",
            "Save changes",
            "data-edit-ex",
            "Editing this experience. Save changes keeps the stops and their order.",
            "Move up and Move down set the order. Save to keep it.",
            "Edit an experience to change a stop or its order.",
            "Name renters see",
            "method: 'PATCH'",
            "'/shop/experiences/' + eid",
        ):
            self.assertIn(line, admin)
            self.assertNotIn("\u2014", line)
        # Create and edit post the same fields. Edit uses the existing PATCH route.
        self.assertIn("title: $('#exTitle').value.trim()", admin)
        self.assertIn("description: $('#exDesc').value", admin)
        self.assertIn("stops,", admin)
        self.assertIn("await api('/shop/experiences', { method: 'POST'", admin)


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class ExperienceStopEdit(unittest.TestCase):
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

    def open_admin(self):
        state = {"experiences": [experience()]}
        saved = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me" and req.method == "GET":
                route.fulfill(json={
                    "user": {"email": "owner@gmail.com", "super": False},
                    "dev_auth": False,
                    "google": True,
                })
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={
                    "shop": shop(),
                    "experiences": state["experiences"],
                    "affiliates": [],
                    "codes": [],
                })
                return
            if path == "/api/partner/shop/experiences/ex1" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                saved.append(body)
                ex = state["experiences"][0]
                ex["title"] = body.get("title", ex["title"])
                ex["description"] = body.get("description", ex["description"])
                ex["stops"] = body.get("stops", ex["stops"])
                route.fulfill(json={"experience": ex})
                return
            if path == "/api/partner/shop/experiences" and req.method == "POST":
                saved.append({"_method": "POST", **json.loads(req.post_data or "{}")})
                route.fulfill(json={"error": "create was not expected"}, status=500)
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("[data-edit-ex='ex1']")
        return pg, saved

    def test_edit_and_reorder_persist_on_save(self):
        pg, saved = self.open_admin()
        try:
            self.assertEqual(pg.locator("#addEx").inner_text(), "Add experience")
            self.assertTrue(pg.locator("#cancelEx").is_hidden())
            self.assertEqual(
                pg.locator(".ex-stops").inner_text(),
                "1. Seals (Morning) · 2. Cove (Swim) · 3. Pier (Sunset)",
            )
            # The blank create row cannot move. Reorder lives on a saved experience.
            self.assertTrue(pg.locator("#stopList .stop .moveUp").is_disabled())
            self.assertTrue(pg.locator("#stopList .stop .moveDown").is_disabled())

            pg.locator("[data-edit-ex='ex1']").click()
            pg.wait_for_function("() => document.querySelector('#exId').value === 'ex1'")
            self.assertEqual(pg.locator("#addEx").inner_text(), "Save changes")
            self.assertTrue(pg.locator("#cancelEx").is_visible())
            self.assertTrue(pg.locator("#exEditing").is_visible())
            self.assertEqual(pg.input_value("#exTitle"), "La Jolla seals joyride")
            self.assertEqual(pg.input_value("#exDesc"), "A coastal loop")
            loaded = form_stops(pg)
            self.assertEqual([s["name"] for s in loaded], ["Seals", "Cove", "Pier"])
            self.assertEqual([s["note"] for s in loaded], ["Morning", "Swim", "Sunset"])
            self.assertEqual(loaded[1]["lat"], "32.84021")
            self.assertEqual(loaded[1]["lon"], "-117.27031")
            rows = pg.locator("#stopList .stop")
            self.assertTrue(rows.nth(0).locator(".moveUp").is_disabled())
            self.assertFalse(rows.nth(0).locator(".moveDown").is_disabled())
            self.assertTrue(rows.nth(2).locator(".moveDown").is_disabled())
            self.assertFalse(rows.nth(1).locator(".moveUp").is_disabled())

            for width in (1280, 430, 390, 375):
                pg.set_viewport_size({"width": width, "height": 900})
                spill = pg.evaluate(
                    """() => {
                      const vw = document.documentElement.clientWidth;
                      const els = [...document.querySelectorAll('#stopList .moveUp, #stopList .moveDown, #stopList [data-k=name], #addEx, #cancelEx')];
                      let worst = 0;
                      for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width <= 0) return 999;
                        worst = Math.max(worst, r.right - vw, -r.left);
                      }
                      return worst;
                    }"""
                )
                self.assertLessEqual(spill, 1, "controls spill at %s by %s px" % (width, spill))
                self.assertTrue(rows.nth(1).locator(".moveUp").is_visible())
                self.assertTrue(rows.nth(1).locator("[data-k=name]").is_visible())
            pg.set_viewport_size({"width": 1280, "height": 900})

            pg.fill("#exTitle", "Cove morning loop")
            pg.fill("#exDesc", "Snorkel then seals")
            cove = rows.nth(1)
            cove.locator("[data-k=name]").fill("La Jolla Cove")
            cove.locator("[data-k=note]").fill("Snorkel here")
            self.assertEqual(cove.locator("[data-k=label]").input_value(), "La Jolla Cove")
            self.assertEqual(cove.locator("[data-k=q]").input_value(), "La Jolla Cove")
            # Move the edited stop up, then exercise Move down and Move up again.
            cove.locator(".moveUp").click()
            self.assertEqual([s["name"] for s in form_stops(pg)], ["La Jolla Cove", "Seals", "Pier"])
            rows.nth(0).locator(".moveDown").click()
            self.assertEqual([s["name"] for s in form_stops(pg)], ["Seals", "La Jolla Cove", "Pier"])
            rows.nth(1).locator(".moveUp").click()
            moved = form_stops(pg)
            self.assertEqual([s["name"] for s in moved], ["La Jolla Cove", "Seals", "Pier"])
            self.assertEqual([s["note"] for s in moved], ["Snorkel here", "Morning", "Sunset"])
            self.assertEqual(moved[0]["lat"], "32.84021")
            self.assertEqual(moved[0]["lon"], "-117.27031")
            self.assertEqual(moved[1]["lat"], "32.85012")
            # Nothing is stored until Save changes.
            self.assertEqual(saved, [])
            self.assertEqual(
                pg.locator(".ex-stops").inner_text(),
                "1. Seals (Morning) · 2. Cove (Swim) · 3. Pier (Sunset)",
            )

            with pg.expect_response(lambda r: r.request.method == "PATCH" and urlsplit(r.url).path == "/api/partner/shop/experiences/ex1") as patched:
                with pg.expect_response(lambda r: r.request.method == "GET" and urlsplit(r.url).path == "/api/partner/shop") as got:
                    pg.click("#addEx")
            self.assertTrue(patched.value.ok)
            self.assertTrue(got.value.ok)
            pg.wait_for_function(
                """() => {
                  const line = document.querySelector('.ex-stops');
                  return line && line.textContent.indexOf('1. La Jolla Cove (Snorkel here)') === 0;
                }"""
            )
            self.assertEqual(len(saved), 1)
            body = saved[0]
            self.assertEqual(body["title"], "Cove morning loop")
            self.assertEqual(body["description"], "Snorkel then seals")
            self.assertEqual([s["label"] for s in body["stops"]], ["La Jolla Cove", "Seals", "Pier"])
            self.assertEqual([s["note"] for s in body["stops"]], ["Snorkel here", "Morning", "Sunset"])
            self.assertAlmostEqual(body["stops"][0]["lat"], 32.84021, places=5)
            self.assertAlmostEqual(body["stops"][0]["lon"], -117.27031, places=5)
            self.assertAlmostEqual(body["stops"][1]["lat"], 32.85012, places=5)
            self.assertAlmostEqual(body["stops"][1]["lon"], -117.26011, places=5)
            self.assertAlmostEqual(body["stops"][2]["lat"], 32.87033, places=5)
            self.assertAlmostEqual(body["stops"][2]["lon"], -117.25044, places=5)
            self.assertNotIn("_method", body)
            self.assertIn("Experience saved", pg.inner_text(".msg.ok"))
            self.assertEqual(
                pg.locator(".ex-stops").inner_text(),
                "1. La Jolla Cove (Snorkel here) · 2. Seals (Morning) · 3. Pier (Sunset)",
            )
            self.assertIn("Cove morning loop", pg.locator("table").nth(0).inner_text())
            self.assertEqual(pg.locator("#addEx").inner_text(), "Add experience")
            self.assertEqual(pg.input_value("#exId"), "")

            # Reopen. The form is filled from the saved shop bundle, not the unsaved draft.
            pg.locator("[data-edit-ex='ex1']").click()
            pg.wait_for_function("() => document.querySelector('#exId').value === 'ex1'")
            again = form_stops(pg)
            self.assertEqual(pg.input_value("#exTitle"), "Cove morning loop")
            self.assertEqual(pg.input_value("#exDesc"), "Snorkel then seals")
            self.assertEqual([s["name"] for s in again], ["La Jolla Cove", "Seals", "Pier"])
            self.assertEqual([s["label"] for s in again], ["La Jolla Cove", "Seals", "Pier"])
            self.assertEqual([s["note"] for s in again], ["Snorkel here", "Morning", "Sunset"])
            self.assertEqual(again[0]["lat"], "32.84021")
            self.assertEqual(again[0]["lon"], "-117.27031")
            self.assertEqual(again[1]["lat"], "32.85012")
        finally:
            pg.close()

    def test_cancel_edit_does_not_save(self):
        pg, saved = self.open_admin()
        try:
            pg.locator("[data-edit-ex='ex1']").click()
            pg.wait_for_function("() => document.querySelector('#exId').value === 'ex1'")
            pg.locator("#stopList .stop").nth(0).locator("[data-k=note]").fill("Changed")
            pg.locator("#stopList .stop").nth(0).locator(".moveDown").click()
            self.assertEqual([s["name"] for s in form_stops(pg)], ["Cove", "Seals", "Pier"])
            pg.click("#cancelEx")
            self.assertEqual(pg.input_value("#exId"), "")
            self.assertEqual(pg.locator("#addEx").inner_text(), "Add experience")
            self.assertTrue(pg.locator("#cancelEx").is_hidden())
            self.assertTrue(pg.locator("#exEditing").is_hidden())
            self.assertEqual(pg.locator("#stopList .stop").count(), 1)
            self.assertEqual(pg.input_value("#stopList .stop [data-k=name]"), "")
            self.assertEqual(saved, [])
            self.assertEqual(
                pg.locator(".ex-stops").inner_text(),
                "1. Seals (Morning) · 2. Cove (Swim) · 3. Pier (Sunset)",
            )
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
