"""Shops upload a logo and a stop photo instead of pasting a URL.

The renter map shows the stop photo. GIF and other types are refused in the browser.
"""
import base64
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
except ImportError:
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR") or os.environ.get("SHOTS") or ""
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PHOTO = "https://example.com/cove.jpg"


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


def shop(logo=""):
    return {
        "id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd",
        "blurb": "", "logo_url": logo, "color": "", "owner_email": "owner@gmail.com",
        "disabled": False, "vehicle": "golf_cart",
    }


class PhotoSource(unittest.TestCase):
    def test_admin_copy_names_the_limits(self):
        with open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8") as f:
            admin = f.read()
        for line in ("Or upload a logo", "JPEG, PNG, or WebP, up to 1.5 MB", "uploadShopPhoto", "data-k=\"photoFile\""):
            self.assertIn(line, admin)
            self.assertNotIn("\u2014", line)


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class PhotoUpload(unittest.TestCase):
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

    def test_upload_logo_and_stop_photo_then_renter_sees_it(self):
        state = {"shop": shop(), "saved": []}
        uploads = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": state["shop"], "experiences": [], "affiliates": [], "places": [], "codes": []})
                return
            if path == "/api/partner/shop/media" and req.method == "POST":
                body = json.loads(req.post_data or "{}")
                uploads.append(body.get("kind"))
                raw = base64.b64decode(body.get("data_base64") or "")
                self.assertEqual(raw[:4], b"\x89PNG")
                url = PHOTO if body.get("kind") == "stop" else self.base + "/favicon.svg"
                route.fulfill(json={"id": "ab" * 16, "url": url, "content_type": "image/png", "bytes": len(raw)})
                return
            if path == "/api/partner/shop" and req.method == "PATCH":
                body = json.loads(req.post_data or "{}")
                state["saved"].append(body)
                state["shop"]["logo_url"] = body.get("logo_url", state["shop"]["logo_url"])
                route.fulfill(json={"shop": state["shop"]})
                return
            if path == "/api/partner/shop/experiences" and req.method == "POST":
                body = json.loads(req.post_data or "{}")
                state["saved"].append(body)
                route.fulfill(json={"experience": {"id": "e1", **body}}, status=201)
                return
            if path.startswith("/api/partner/public/lajollacartco/unlock"):
                route.fulfill(json={
                    "unlocked": True, "code": "DESKCODE", "grant": "g",
                    "shop": shop(self.base + "/favicon.svg"),
                    "experiences": [{
                        "id": "e1", "title": "Cove", "description": "",
                        "stops": [{"label": "Cove", "lat": 32.85, "lon": -117.27, "note": "Park by the umbrellas", "photo": self.base + "/favicon.svg"}],
                    }],
                    "affiliates": [], "places": [],
                })
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.route("https://example.com/**", lambda r: r.abort())
        pg.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
        try:
            pg.goto(self.base + "/partner", wait_until="domcontentloaded")
            pg.wait_for_selector("#brandLogoFile")
            pg.set_input_files("#brandLogoFile", files=[{"name": "logo.png", "mimeType": "image/png", "buffer": PNG}])
            pg.wait_for_function("() => document.querySelector('#logoFileNote').textContent.includes('Save brand')")
            self.assertEqual(uploads, ["logo"])
            self.assertTrue(pg.locator("#logoPreview").is_visible())
            pg.locator("#saveBrand").click()
            pg.wait_for_function("() => document.body.innerText.includes('Brand saved')")
            self.assertEqual(state["saved"][-1]["logo_url"], self.base + "/favicon.svg")

            pg.set_input_files("#brandLogoFile", files=[{"name": "anim.gif", "mimeType": "image/gif", "buffer": b"GIF89a"}])
            pg.wait_for_function("() => document.querySelector('#logoFileNote').textContent.startsWith('Use a JPEG')")
            self.assertEqual(uploads, ["logo"])

            pg.fill("#exTitle", "Cove loop")
            pg.locator("#stopList [data-k=name]").fill("Cove")
            pg.locator("#stopList [data-k=lat]").evaluate("(el) => { el.value = '32.85'; }")
            pg.locator("#stopList [data-k=lon]").evaluate("(el) => { el.value = '-117.27'; }")
            pg.set_input_files("#stopList [data-k=photoFile]", files=[{"name": "cove.png", "mimeType": "image/png", "buffer": PNG}])
            pg.wait_for_function("() => document.querySelector('[data-k=photoNote]').textContent.includes('Save the experience')")
            self.assertEqual(uploads, ["logo", "stop"])
            self.assertTrue(pg.locator("[data-k=photoPreview]").is_visible())
            for width in (1280, 375):
                pg.set_viewport_size({"width": width, "height": 900})
                spill = pg.evaluate(
                    """() => {
                      const vw = document.documentElement.clientWidth;
                      const els = [...document.querySelectorAll('#brandLogoFile, #stopList [data-k=photoFile], #logoPreview, [data-k=photoPreview]')];
                      let worst = 0;
                      for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width <= 0) return 999;
                        worst = Math.max(worst, r.right - vw, -r.left);
                      }
                      return worst;
                    }"""
                )
                self.assertLessEqual(spill, 1, "photo controls spill at %s" % width)
            pg.set_viewport_size({"width": 900, "height": 900})
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.locator("#stopList").scroll_into_view_if_needed()
                pg.screenshot(path=os.path.join(SHOTS, "photo-admin.png"))
            pg.locator("#addEx").click()
            pg.wait_for_function("() => document.body.innerText.includes('Experience added')")
            posted = [b for b in state["saved"] if b.get("stops")][-1]
            self.assertEqual(posted["stops"][0]["photo"], PHOTO)

            renter = self.b.new_page()
            renter.route("**/api/partner/**", handle)
            renter.route(re.compile(r"https://[a-c]?\.?tile|basemaps|openstreetmap"), lambda r: r.abort())
            renter.goto(self.base + "/p/lajollacartco/go?code=DESKCODE", wait_until="domcontentloaded")
            renter.wait_for_selector(".leaflet-marker-icon", timeout=20000)
            renter.locator(".leaflet-marker-icon").first.click()
            renter.wait_for_selector(".leaflet-popup-content img")
            popup = renter.locator(".leaflet-popup-content")
            self.assertIn("Cove", popup.inner_text())
            self.assertIn("Park by the umbrellas", popup.inner_text())
            self.assertIn("/favicon.svg", popup.locator("img").get_attribute("src"))
            if SHOTS:
                renter.screenshot(path=os.path.join(SHOTS, "photo-renter.png"))
            renter.close()
        finally:
            pg.close()
