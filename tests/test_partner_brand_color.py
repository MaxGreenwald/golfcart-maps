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
            pg.wait_for_selector(".msg")
            self.assertEqual(
                pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()"),
                "#ff00aa",
            )

            state["color"] = ""
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
