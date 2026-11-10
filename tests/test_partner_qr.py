"""Partner admin prints a cart sticker and a counter card for one access code.

The QR target is the same /p/<slug>/go?code= link the codes table already copies.
"""
import functools
import http.server
import os
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


def shop(base):
    return {
        "id": "s1", "slug": "lajollacartco", "name": "La Jolla Cart Co", "region_id": "sd",
        "blurb": "Coastal loops", "logo_url": base + "/favicon.svg", "color": "#0b6e86",
        "owner_email": "owner@gmail.com", "disabled": False, "vehicle": "golf_cart",
    }


class QrKitSource(unittest.TestCase):
    def test_admin_offers_one_print_button_per_code(self):
        with open(os.path.join(PUB, "partner", "admin.js"), encoding="utf-8") as f:
            admin = f.read()
        with open(os.path.join(PUB, "partner", "index.html"), encoding="utf-8") as f:
            page = f.read()
        for line in (
            "Print QR kit",
            "Access code on the QR",
            "Generate an access code first",
            "qrKitBlock(s, b.codes)",
            "GCMQrKit.printHtml",
        ):
            self.assertIn(line, admin)
            self.assertNotIn("\u2014", line)
        self.assertIn("/vendor/qrcode.js", admin)
        self.assertIn("/qrkit.js", admin)
        self.assertNotIn("/vendor/qrcode.js", page)


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class QrKitPrint(unittest.TestCase):
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

    def open_admin(self, codes):
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/api/partner/auth/me" and req.method == "GET":
                route.fulfill(json={"user": {"email": "owner@gmail.com", "super": False}, "dev_auth": False, "google": True})
                return
            if path == "/api/partner/shop" and req.method == "GET":
                route.fulfill(json={"shop": shop(self.base), "experiences": [], "affiliates": [], "places": [], "codes": codes})
                return
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("#qrKit")
        return pg

    def test_print_page_has_sticker_card_logo_and_prefilled_code(self):
        pg = self.open_admin([
            {"code": "OLDCODE", "uses": 1, "max_uses": 0, "multi_use": 1, "expires_at": None},
            {"code": "DESKCODE", "uses": 0, "max_uses": 0, "multi_use": 1, "expires_at": None},
        ])
        try:
            self.assertEqual(pg.locator("#qrCode").input_value(), "OLDCODE")
            pg.select_option("#qrCode", "DESKCODE")
            for width in (1280, 430, 390, 375):
                pg.set_viewport_size({"width": width, "height": 900})
                spill = pg.evaluate(
                    """() => {
                      const vw = document.documentElement.clientWidth;
                      const els = [...document.querySelectorAll('#qrKit select, #qrKit button, #qrKit p')];
                      let worst = 0;
                      for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width <= 0) return 999;
                        worst = Math.max(worst, r.right - vw, -r.left);
                      }
                      return worst;
                    }"""
                )
                self.assertLessEqual(spill, 1, "QR kit spills at %s by %s px" % (width, spill))
            pg.set_viewport_size({"width": 900, "height": 800})
            pg.locator("#qrKit").scroll_into_view_if_needed()
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                pg.screenshot(path=os.path.join(SHOTS, "qr-kit-admin.png"))
            with pg.expect_popup() as pop:
                pg.locator("#printQr").click()
            kit = pop.value
            kit.wait_for_selector("section.sticker svg")
            kit.wait_for_selector("section.card svg")
            body = kit.inner_text("body")
            html = kit.content().replace("<wbr>", "")
            self.assertIn("Scan for your rides", html)
            self.assertIn("Ask the desk, then scan", html)
            self.assertIn("DESKCODE", body)
            self.assertIn("La Jolla Cart Co", body)
            self.assertIn(self.base + "/p/lajollacartco/go?code=DESKCODE", html)
            self.assertIn(self.base + "/favicon.svg", html)
            self.assertIn("#0b6e86", html)
            self.assertNotIn("\u2014", body)
            self.assertEqual(kit.locator("svg").count(), 2)
            if SHOTS:
                kit.screenshot(path=os.path.join(SHOTS, "qr-kit-print.png"), full_page=True)
            kit.close()
        finally:
            pg.close()

    def test_button_stays_disabled_until_a_code_exists(self):
        pg = self.open_admin([])
        try:
            self.assertTrue(pg.locator("#printQr").is_disabled())
            self.assertTrue(pg.locator("#qrCode").is_disabled())
            self.assertIn("Generate an access code first", pg.locator("#qrCode").inner_text())
        finally:
            pg.close()
