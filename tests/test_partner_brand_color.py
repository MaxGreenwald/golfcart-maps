"""Shop admin sets the brand primary color with a swatch. Hex stays in sync for the API.

Empty color is allowed: /p/<slug> keeps the default teal (--brand: var(--aqua)).
"""
import functools
import http.server
import json
import os
import re
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


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parts = urlsplit(self.path)
        path = parts.path
        if path.rstrip("/") == "/partner":
            path = "/partner/index.html"
        elif re.fullmatch(r"/p/[^/]+(?:/go)?/?", path):
            path = "/p.html"
        self.path = path + (("?" + parts.query) if parts.query else "")
        return super().do_GET()


class _S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def shop(**over):
    base = {
        "id": "s1",
        "slug": "lajollacartco",
        "name": "La Jolla Cart Co",
        "region_id": "sd",
        "blurb": "Coastal loops",
        "logo_url": "https://example.com/logo.png",
        "color": "",
        "owner_email": "owner@gmail.com",
        "disabled": False,
    }
    base.update(over)
    return base


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class BrandColorPicker(unittest.TestCase):
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

    def open_admin(self, row):
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
                route.fulfill(json={"shop": row, "experiences": [], "affiliates": [], "codes": []})
                return
            if path == "/api/partner/shop" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                for k in ("name", "region_id", "blurb", "logo_url", "color"):
                    if k in body:
                        row[k] = body[k]
                saved.append(body)
                route.fulfill(json={"shop": dict(row)})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("#brandColorPick")
        return pg, saved

    def save_brand(self, pg):
        with pg.expect_response(lambda r: r.request.method == "GET" and urlsplit(r.url).path == "/api/partner/shop") as got:
            pg.click("#saveBrand")
        self.assertTrue(got.value.ok)
        pg.wait_for_selector(".msg.ok")
        self.assertIn("Brand saved", pg.inner_text(".msg.ok"))

    def test_swatch_syncs_hex_clear_keeps_default_other_fields_save(self):
        row = shop()
        pg, saved = self.open_admin(row)
        try:
            self.assertEqual(pg.locator("#brandColor").get_attribute("type"), "hidden")
            self.assertEqual(pg.locator("#brandColorPick").get_attribute("type"), "color")
            self.assertEqual(pg.input_value("#brandColor"), "")
            self.assertEqual(pg.input_value("#brandColorPick"), "#14b8c4")
            self.assertEqual(pg.inner_text("#brandColorHex").strip(), "Default teal")
            self.assertTrue(pg.locator("#brandColorClear").is_disabled())
            for width in (1280, 390):
                pg.set_viewport_size({"width": width, "height": 900})
                box = pg.locator("#brandColorPick").bounding_box()
                self.assertIsNotNone(box)
                self.assertLess(box["width"], 80)
                self.assertGreater(box["width"], 30)
                self.assertTrue(pg.locator("#brandName").is_visible())
                self.assertTrue(pg.locator("#brandLogo").is_visible())

            pg.locator("#brandColorPick").fill("#ff00aa")
            self.assertEqual(pg.input_value("#brandColor"), "#ff00aa")
            self.assertEqual(pg.inner_text("#brandColorHex").strip(), "#ff00aa")
            self.assertFalse(pg.locator("#brandColorClear").is_disabled())

            pg.locator("#brandColorClear").click()
            self.assertEqual(pg.input_value("#brandColor"), "")
            self.assertEqual(pg.input_value("#brandColorPick"), "#14b8c4")
            self.assertEqual(pg.inner_text("#brandColorHex").strip(), "Default teal")
            self.assertTrue(pg.locator("#brandColorClear").is_disabled())

            pg.locator("#brandColorPick").fill("#abcdef")
            pg.fill("#brandName", "Cove Carts")
            pg.fill("#brandBlurb", "Sunset loops")
            pg.fill("#brandLogo", "https://example.com/new.png")
            pg.select_option("#brandRegion", "sd")
            self.save_brand(pg)
            body = saved[-1]
            self.assertEqual(body["color"], "#abcdef")
            self.assertEqual(body["name"], "Cove Carts")
            self.assertEqual(body["blurb"], "Sunset loops")
            self.assertEqual(body["logo_url"], "https://example.com/new.png")
            self.assertEqual(body["region_id"], "sd")
            self.assertNotIn("disabled", body)
            self.assertEqual(pg.input_value("#brandColor"), "#abcdef")
            self.assertEqual(pg.input_value("#brandColorPick"), "#abcdef")
            self.assertEqual(pg.input_value("#brandName"), "Cove Carts")
            self.assertEqual(pg.input_value("#brandBlurb"), "Sunset loops")
            self.assertEqual(pg.input_value("#brandLogo"), "https://example.com/new.png")
        finally:
            pg.close()

    def test_short_hex_normalizes_and_non_hex_is_kept_until_a_pick(self):
        row = shop(color="#F0A")
        pg, saved = self.open_admin(row)
        try:
            self.assertEqual(pg.input_value("#brandColor"), "#ff00aa")
            self.assertEqual(pg.input_value("#brandColorPick"), "#ff00aa")
            self.assertEqual(pg.inner_text("#brandColorHex").strip(), "#ff00aa")
        finally:
            pg.close()

        row = shop(color="navy")
        pg, saved = self.open_admin(row)
        try:
            self.assertEqual(pg.input_value("#brandColor"), "navy")
            self.assertEqual(pg.inner_text("#brandColorHex").strip(), "navy")
            self.assertEqual(pg.input_value("#brandColorPick"), "#14b8c4")
            self.save_brand(pg)
            self.assertEqual(saved[-1]["color"], "navy")
            self.assertEqual(saved[-1]["name"], "La Jolla Cart Co")
            self.assertEqual(saved[-1]["logo_url"], "https://example.com/logo.png")
            pg.locator("#brandColorPick").fill("#112233")
            self.assertEqual(pg.input_value("#brandColor"), "#112233")
            self.save_brand(pg)
            self.assertEqual(saved[-1]["color"], "#112233")
            self.assertEqual(pg.input_value("#brandColorPick"), "#112233")
        finally:
            pg.close()

    def _pin_state(self, pg, selector):
        return pg.evaluate(
            """(sel) => {
              const el = document.querySelector(sel);
              if (!el || !el._gcmMap) return null;
              const c = el._gcmMap.getCenter();
              const m = el._gcmMarker;
              const tile = el.querySelector('img.leaflet-tile');
              return {
                lat: c.lat,
                lng: c.lng,
                zoom: el._gcmMap.getZoom(),
                marker: m ? {lat: m.getLatLng().lat, lng: m.getLatLng().lng} : null,
                src: tile ? tile.src : '',
              };
            }""",
            selector,
        )

    def _wait_pin_tiles(self, pg, selector):
        pg.wait_for_function(
            """(sel) => {
              const el = document.querySelector(sel);
              const tiles = el ? [...el.querySelectorAll('img.leaflet-tile')] : [];
              return tiles.some(i => i.complete && i.naturalWidth > 0 && i.src.includes('tile.openstreetmap.org/'));
            }""",
            arg=selector,
            timeout=20000,
        )

    def test_drop_pin_tiles_center_on_city_or_prior_stop(self):
        """Empty lat/lon must not become 0,0, and must not inherit the previous stop's pin.

        A stop with no saved coordinates shows tiles near the previous stop (or the
        city) and writes nothing until click or drag. A stop that already has its
        own coordinates opens on that pin.
        """
        pg, _saved = self.open_admin(shop())
        try:
            pg.locator("#stopList .stop .modePin").click()
            self._wait_pin_tiles(pg, "#stopList .stop .pinmap")
            view = self._pin_state(pg, "#stopList .stop .pinmap")
            self.assertIn("https://tile.openstreetmap.org/", view["src"])
            self.assertNotIn("://a.tile.", view["src"])
            # San Diego region center, not the Gulf of Guinea. No marker yet.
            self.assertAlmostEqual(view["lat"], 32.8565, delta=0.02)
            self.assertAlmostEqual(view["lng"], -117.2555, delta=0.02)
            self.assertGreaterEqual(view["zoom"], 14)
            self.assertLessEqual(view["zoom"], 16)
            self.assertIsNone(view["marker"])
            self.assertEqual(pg.input_value("#stopList .stop [data-k=lat]"), "")
            self.assertEqual(pg.input_value("#stopList .stop [data-k=lon]"), "")
            pg.locator("#stopList .stop .pinmap").click(position={"x": 160, "y": 70})
            self.assertNotEqual(pg.input_value("#stopList .stop [data-k=lat]"), "")
            placed_lat = float(pg.input_value("#stopList .stop [data-k=lat]"))
            placed_lon = float(pg.input_value("#stopList .stop [data-k=lon]"))
            self.assertGreater(abs(placed_lat), 1)
            self.assertGreater(abs(placed_lon), 1)
            placed = self._pin_state(pg, "#stopList .stop .pinmap")
            self.assertIsNotNone(placed["marker"])
            self.assertAlmostEqual(placed["marker"]["lat"], placed_lat, delta=0.0002)
            self.assertAlmostEqual(placed["marker"]["lng"], placed_lon, delta=0.0002)
            # Drag confirms a new point and does not snap back to the city center.
            handle = pg.locator("#stopList .stop .leaflet-marker-icon")
            box = handle.bounding_box()
            self.assertIsNotNone(box)
            pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            pg.mouse.down()
            pg.mouse.move(box["x"] + box["width"] / 2 + 50, box["y"] + box["height"] / 2 + 30)
            pg.mouse.up()
            dragged_lat = float(pg.input_value("#stopList .stop [data-k=lat]"))
            dragged_lon = float(pg.input_value("#stopList .stop [data-k=lon]"))
            self.assertGreater(abs(dragged_lat - placed_lat) + abs(dragged_lon - placed_lon), 0.0003)
            placed_lat, placed_lon = dragged_lat, dragged_lon
            # Search place is still the other mode.
            pg.locator("#stopList .stop .modeSearch").click()
            self.assertTrue(pg.locator("#stopList .stop .place-search").is_visible())
            self.assertTrue(pg.locator("#stopList .stop .place-pin").is_hidden())

            pg.locator("#addStop").click()
            second = pg.locator("#stopList .stop").nth(1)
            second.locator(".modePin").click()
            self._wait_pin_tiles(pg, "#stopList .stop:nth-child(2) .pinmap")
            nxt = self._pin_state(pg, "#stopList .stop:nth-child(2) .pinmap")
            # Near the previous stop, not on its exact coordinates, and not street-zoomed onto it.
            self.assertAlmostEqual(nxt["lat"], placed_lat + 0.0022, delta=0.0015)
            self.assertAlmostEqual(nxt["lng"], placed_lon + 0.0022, delta=0.0015)
            self.assertGreater(abs(nxt["lat"] - placed_lat) + abs(nxt["lng"] - placed_lon), 0.001)
            self.assertGreaterEqual(nxt["zoom"], 11)
            self.assertLessEqual(nxt["zoom"], 14)
            self.assertIsNone(nxt["marker"])
            # Opening Drop pin must not copy the last stop into this one.
            self.assertEqual(second.locator("[data-k=lat]").input_value(), "")
            self.assertEqual(second.locator("[data-k=lon]").input_value(), "")
            self.assertAlmostEqual(float(pg.locator("#stopList .stop").nth(0).locator("[data-k=lat]").input_value()), placed_lat, delta=0.00001)

            # This stop already has its own pin (as search would). Show that pin, not the previous stop.
            own_lat, own_lon = 32.7456, -117.1612
            second.locator("[data-k=lat]").evaluate("(el, v) => { el.value = v; }", str(own_lat))
            second.locator("[data-k=lon]").evaluate("(el, v) => { el.value = v; }", str(own_lon))
            second.locator(".modePin").click()
            own = self._pin_state(pg, "#stopList .stop:nth-child(2) .pinmap")
            self.assertEqual(own["zoom"], 16)
            self.assertIsNotNone(own["marker"])
            self.assertAlmostEqual(own["marker"]["lat"], own_lat, delta=0.0002)
            self.assertAlmostEqual(own["marker"]["lng"], own_lon, delta=0.0002)
            self.assertAlmostEqual(own["lat"], own_lat, delta=0.0008)
            self.assertAlmostEqual(own["lng"], own_lon, delta=0.0008)
            self.assertGreater(abs(own["marker"]["lat"] - placed_lat) + abs(own["marker"]["lng"] - placed_lon), 0.01)
            self.assertAlmostEqual(float(second.locator("[data-k=lat]").input_value()), own_lat, delta=0.00001)
            self.assertAlmostEqual(float(second.locator("[data-k=lon]").input_value()), own_lon, delta=0.00001)

            pg.locator("#afModes .modePin").click()
            self._wait_pin_tiles(pg, "#afPinMap")
            af = self._pin_state(pg, "#afPinMap")
            self.assertAlmostEqual(af["lat"], 32.8565, delta=0.02)
            self.assertAlmostEqual(af["lng"], -117.2555, delta=0.02)
            self.assertGreaterEqual(af["zoom"], 14)
            self.assertLessEqual(af["zoom"], 16)
            self.assertIsNone(af["marker"])
            self.assertEqual(pg.input_value("#afLat"), "")
            self.assertEqual(pg.input_value("#afLon"), "")
            pg.locator("#afPinMap").click(position={"x": 140, "y": 80})
            self.assertNotEqual(pg.input_value("#afLat"), "")
            self.assertGreater(abs(float(pg.input_value("#afLat"))), 1)
        finally:
            pg.close()

    def test_brand_and_renter_pages_use_saved_color_or_teal(self):
        state = {"color": "#ff00aa"}
        pg = self.b.new_page()

        def shop_payload():
            return shop(color=state["color"], logo_url="")

        def handle(route):
            path = urlsplit(route.request.url).path
            if path == "/api/partner/public/lajollacartco":
                route.fulfill(json={
                    "shop": shop_payload(),
                    "unlocked": False,
                    "experience_count": 1,
                    "affiliate_count": 0,
                })
                return
            if path.startswith("/api/partner/public/lajollacartco/unlock"):
                route.fulfill(json={
                    "unlocked": True,
                    "shop": shop_payload(),
                    "experiences": [],
                    "affiliates": [],
                    "code": "7K3M9P2Q",
                })
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://*.tile.openstreetmap.org/**", lambda r: r.abort())
        try:
            pg.goto(self.base + "/p/lajollacartco", wait_until="domcontentloaded")
            pg.wait_for_selector("#unlockBtn")
            self.assertEqual(
                pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()"),
                "#ff00aa",
            )
            self.assertEqual(
                pg.evaluate("getComputedStyle(document.querySelector('#unlockBtn')).backgroundColor"),
                "rgb(255, 0, 170)",
            )

            pg.goto(self.base + "/p/lajollacartco/go?code=7K3M9P2Q", wait_until="domcontentloaded")
            pg.wait_for_selector(".yay")
            self.assertEqual(
                pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()"),
                "#ff00aa",
            )

            state["color"] = ""
            # The go?code= unlock above is saved and reopens unlocked (Max t449u); clear it to see the locked page.
            pg.evaluate("localStorage.clear()")
            pg.goto(self.base + "/p/lajollacartco", wait_until="domcontentloaded")
            pg.wait_for_selector("#unlockBtn")
            self.assertEqual(
                pg.evaluate("document.documentElement.style.getPropertyValue('--brand')"),
                "",
            )
            self.assertEqual(
                pg.evaluate("getComputedStyle(document.querySelector('#unlockBtn')).backgroundColor"),
                "rgb(20, 184, 196)",
            )
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
