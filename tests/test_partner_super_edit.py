"""Super-admin opens any shop's owner editor from the shop list, with a banner and a way back.

Every /shop call made while editing names that shop (?shop_id=), so the Worker edits the right one.
"""
import functools
import http.server
import json
import os
import re
import socketserver
import threading
import unittest
from urllib.parse import urlsplit, parse_qs

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # unit-test CI job has no browser; the browser job runs this file
    sync_playwright = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
SHOTS = os.environ.get("SHOTS_DIR")


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


SHOPS = {
    "s1": {"id": "s1", "slug": "beachmode", "name": "Beach Mode Rentals", "region_id": "sd", "blurb": "", "logo_url": "",
           "color": "", "owner_email": "brian@gmail.com", "disabled": False},
    "s2": {"id": "s2", "slug": "maxtest", "name": "Max Test Rentals", "region_id": "sd", "blurb": "", "logo_url": "",
           "color": "", "owner_email": "", "disabled": False},
}


@unittest.skipIf(sync_playwright is None, "playwright not installed (runs in the browser CI job)")
class SuperEdit(unittest.TestCase):
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

    def open_super(self):
        shops = {k: dict(v) for k, v in SHOPS.items()}
        exps = {"s2": [{"id": "e1", "shop_id": "s2", "title": "Old loop", "description": "", "stops": [
            {"label": "A", "lat": 32.79, "lon": -117.25}, {"label": "B", "lat": 32.80, "lon": -117.24}]}]}
        afs = {"s2": [{"id": "a1", "shop_id": "s2", "name": "Bar One", "lat": 32.795, "lon": -117.252,
                       "offer": "10% off", "coupon": "OFFER-1"}, {"id": "a2", "shop_id": "s2", "name": "Gone Cafe",
                       "lat": 32.79, "lon": -117.25, "offer": "", "coupon": ""}]}
        self.exps, self.afs = exps, afs
        self.codes, self.code_posts = [], []
        calls = []
        pg = self.b.new_page()

        def handle(route):
            req = route.request
            u = urlsplit(req.url)
            path, q = u.path, parse_qs(u.query)
            sid = (q.get("shop_id") or [""])[0]
            if path == "/api/partner/auth/me":
                return route.fulfill(json={"user": {"email": "max@golfcartmap.com", "super": True}, "dev_auth": False, "google": True})
            if path == "/api/partner/admin/shops" and req.method == "GET":
                return route.fulfill(json={"shops": list(shops.values())})
            if path == "/api/partner/admin/shops" and req.method == "POST":
                body = json.loads(req.post_data or "{}")
                shops["s3"] = dict(SHOPS["s2"], id="s3", slug=body["slug"], name=body["name"])
                return route.fulfill(json={"shop": shops["s3"]}, status=201)
            if path.startswith("/api/partner/shop"):
                calls.append((req.method, path, sid, json.loads(req.post_data) if req.post_data else None))
                if sid not in shops:
                    return route.fulfill(json={"error": "shop_id required for super-admin"}, status=400)
                if path == "/api/partner/shop" and req.method == "GET":
                    return route.fulfill(json={"shop": shops[sid], "experiences": exps.get(sid, []), "affiliates": afs.get(sid, []), "codes": list(self.codes)})
                if path == "/api/partner/shop" and req.method == "PATCH":
                    shops[sid].update(json.loads(req.post_data or "{}"))
                    return route.fulfill(json={"shop": shops[sid]})
                m = re.fullmatch(r"/api/partner/shop/(experiences|affiliates)/(\w+)", path)
                if m:
                    lst = (exps if m.group(1) == "experiences" else afs).setdefault(sid, [])
                    row = next((x for x in lst if x["id"] == m.group(2)), None)
                    if row is None:
                        return route.fulfill(json={"error": "forbidden"}, status=403)
                    if req.method == "DELETE":
                        lst.remove(row)
                        return route.fulfill(json={"ok": True})
                    row.update(json.loads(req.post_data or "{}"))
                    return route.fulfill(json={m.group(1)[:-1]: row})
                if path == "/api/partner/shop/codes":
                    body = json.loads(req.post_data or "{}")
                    d = body.get("expires_days")
                    c = {"code": "C%d" % len(self.codes), "uses": 0, "max_uses": 0, "multi_use": 1,
                         "expires_at": None if d is None else 1893456000 + d * 86400}
                    self.codes.append(c)
                    self.code_posts.append(body)
                    return route.fulfill(json={"code": c}, status=201)
            route.fallback()

        pg.route("**/api/partner/**", handle)
        pg.route("**://photon.komoot.io/**", lambda r: r.abort())
        pg.route("**://nominatim.openstreetmap.org/**", lambda r: r.abort())
        pg.goto(self.base + "/partner", wait_until="domcontentloaded")
        pg.wait_for_selector("[data-open-shop]")
        return pg, shops, calls

    def test_edit_any_shop_banner_scoped_calls_and_back(self):
        pg, shops, calls = self.open_super()
        try:
            pg.click("[data-open-shop='s2']")
            pg.wait_for_selector("#superBanner")
            self.assertIn("Editing Max Test Rentals as super-admin", pg.inner_text("#superBanner"))
            # Full owner editor is there.
            for sel in ("#brandName", "#brandColorPick", "#exTitle", "#addEx", "#saveBrand"):
                self.assertTrue(pg.locator(sel).count() > 0, sel)
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "super_edit_banner.png"), full_page=True)
            pg.fill("#brandBlurb", "Set up by Max")
            pg.click("#saveBrand")
            pg.wait_for_selector(".msg.ok")
            self.assertEqual(shops["s2"]["blurb"], "Set up by Max")
            self.assertEqual(shops["s1"]["blurb"], "", "other shop untouched")
            self.assertTrue(calls and all(c[2] == "s2" for c in calls), calls)
            pg.click("#backToShops")
            pg.wait_for_selector("[data-open-shop]")
            self.assertEqual(pg.locator("#superBanner").count(), 0)
        finally:
            pg.close()

    def test_super_edits_experience_and_affiliates(self):
        pg, shops, calls = self.open_super()
        try:
            pg.click("[data-open-shop='s2']")
            pg.wait_for_selector("#superBanner")
            # Experience: rename, edit a stop, reorder.
            pg.click("[data-edit-ex='e1']")
            pg.fill("#exTitle", "Sunset loop")
            pg.fill("#exDesc", "Golden hour")
            pg.locator("#stopList .stop").nth(1).locator(".moveUp").click()
            pg.click("#addEx")
            pg.wait_for_selector(".msg.ok, .msg.err")
            self.assertEqual(pg.locator(".msg.err").count(), 0, pg.locator(".msg.err").all_inner_texts())
            ex = self.exps["s2"][0]
            self.assertEqual(ex["title"], "Sunset loop")
            self.assertEqual(ex["description"], "Golden hour")
            self.assertEqual([x["label"] for x in ex["stops"]], ["B", "A"])
            # Affiliate: edit every field.
            pg.click("[data-edit-af='a1']")
            self.assertEqual(pg.input_value("#afNameEdit"), "Bar One")
            self.assertEqual(pg.input_value("#afCouponText"), "OFFER-1")
            pg.fill("#afNameEdit", "Bar One Patio")
            pg.fill("#afOffer", "2-for-1 tacos")
            pg.fill("#afCouponText", "TACO2")
            if SHOTS:
                pg.screenshot(path=os.path.join(SHOTS, "super_edit_affiliate.png"), full_page=True)
            pg.click("#addAf")
            pg.wait_for_selector(".msg.ok")
            a = self.afs["s2"][0]
            self.assertEqual((a["name"], a["offer"], a["coupon"]), ("Bar One Patio", "2-for-1 tacos", "TACO2"))
            self.assertAlmostEqual(a["lat"], 32.795)
            # Affiliate delete.
            pg.once("dialog", lambda d: d.accept())
            pg.click("[data-del-af='a2']")
            pg.wait_for_function("!document.querySelector(\"[data-del-af='a2']\")")
            self.assertEqual([x["id"] for x in self.afs["s2"]], ["a1"])
            edits = [c for c in calls if c[0] in ("PATCH", "DELETE", "POST")]
            self.assertTrue(edits and all(c[2] == "s2" for c in edits), edits)
        finally:
            pg.close()

    def test_code_duration_chips_and_no_expiry(self):
        pg, shops, calls = self.open_super()
        try:
            pg.click("[data-open-shop='s2']")
            pg.wait_for_selector("#codeChips")
            pg.click("#codeChips [data-days='7']")
            self.assertEqual(pg.input_value("#codeDays"), "7")
            pg.click("#genCode")
            pg.wait_for_function("document.querySelectorAll('.code-exp').length === 1")
            self.assertEqual(self.code_posts[-1]["expires_days"], 7)
            self.assertIn("Expires", pg.inner_text(".code-exp"))
            pg.click("#codeChips [data-days='never']")
            self.assertTrue(pg.locator("#codeDays").is_disabled())
            pg.click("#genCode")
            pg.wait_for_function("document.querySelectorAll('.code-exp').length === 2")
            self.assertIsNone(self.code_posts[-1]["expires_days"])
            self.assertIn("Never expires", pg.locator(".code-exp").all_inner_texts())
            pg.fill("#codeDays", "45")
            pg.click("#genCode")
            pg.wait_for_selector(".msg.err")
            self.assertEqual(len(self.code_posts), 2, "45 days is refused before the API")
            if SHOTS:
                pg.locator("#codeChips").scroll_into_view_if_needed()
                pg.screenshot(path=os.path.join(SHOTS, "code_duration.png"), full_page=True)
        finally:
            pg.close()

    def test_create_shop_opens_its_editor(self):
        pg, shops, calls = self.open_super()
        try:
            pg.fill("#shopName", "New Carts")
            pg.fill("#shopSlug", "newcarts")
            pg.click("#createShop")
            pg.wait_for_selector("#superBanner")
            self.assertIn("Editing New Carts as super-admin", pg.inner_text("#superBanner"))
            self.assertEqual(calls[-1][2], "s3")
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
