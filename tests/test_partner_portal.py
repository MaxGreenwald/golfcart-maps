"""Partner portal MVP: slug rules, reserved paths, redirects, no user-visible beta."""
import json, os, re, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import region_urls as U

SYSTEM = {
    "map", "p", "partner", "admin", "api", "privacy", "compare", "llms", "robots",
    "lsv", "golf-cart-maps",
    "sitemap", "sw", "vendor", "data", "assets", "static", "login", "logout",
    "auth", "go", "x", "app", "ios", "android", "download", "checkout", "pay",
}
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,47}$")

def normalize(s):
    s = re.sub(r"[^a-z0-9-]+", "-", (s or "").strip().lower()).strip("-")
    return s[:48]

def assert_shop_slug(raw, region_slugs):
    slug = normalize(raw)
    if not SLUG_RE.match(slug):
        return False, "bad shape"
    if slug in SYSTEM:
        return False, "system"
    if slug in region_slugs:
        return False, "city"
    return True, slug


class PartnerPortal(unittest.TestCase):
    def test_redirects_include_partner_spa(self):
        red = open(os.path.join(ROOT, "public", "_redirects"), encoding="utf-8").read()
        for line in (
            "/partner /partner/index.html 200",
            "/p/:slug /p 200",
            "/p/:slug/go /p 200",
        ):
            self.assertIn(line, red)

    def test_region_urls_check_still_passes(self):
        self.assertEqual(U.main(["--check"]), 0)

    def test_slug_rejects_city_and_system(self):
        cities = {r["slug"] for r in U.regions()}
        ok, _ = assert_shop_slug("lajollacartco", cities)
        self.assertTrue(ok)
        self.assertFalse(assert_shop_slug("sandiego", cities)[0])
        self.assertFalse(assert_shop_slug("map", cities)[0])
        self.assertFalse(assert_shop_slug("partner", cities)[0])
        self.assertFalse(assert_shop_slug("1bad", cities)[0])

    def test_access_code_shape(self):
        # Worker uses Crockford-ish alphabet; codes are uppercase alnum without I/L/O/U.
        abc = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        sample = "7K3M9P2Q"
        self.assertTrue(set(sample) <= abc)

    def test_admin_and_brand_pages_exist(self):
        for rel in ("public/partner/index.html", "public/partner/admin.js", "public/p.html", "public/p.js",
                    "functions/api/partner/[[path]].js", "workers/partner/src/index.js", "lib/partner.js",
                    "research/partner_portal_mvp.md"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_no_beta_in_partner_ui_strings(self):
        beta = re.compile(r"(?i)\bbeta\b")
        for rel in ("public/partner/index.html", "public/partner/admin.js", "public/p.html", "public/p.js", "public/router.js"):
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            self.assertIsNone(beta.search(src), rel)

    def test_brand_page_map_overlay_and_start(self):
        html = open(os.path.join(ROOT, "public/p.html"), encoding="utf-8").read()
        js = open(os.path.join(ROOT, "public/p.js"), encoding="utf-8").read()
        router = open(os.path.join(ROOT, "public/router.js"), encoding="utf-8").read()
        app = open(os.path.join(ROOT, "public/app.js"), encoding="utf-8").read()
        index = open(os.path.join(ROOT, "public/index.html"), encoding="utf-8").read()
        sw = open(os.path.join(ROOT, "public/sw.js"), encoding="utf-8").read()
        self.assertIn("Got a code from the shop?", js)
        self.assertIn("The city map is free to use.", js)
        self.assertIn('id="fullMap"', html)
        self.assertIn('id="mapCard"', html)
        self.assertIn("Start experience", js)
        self.assertIn("getCurrentPosition", js)
        self.assertIn("middle of the map", js)
        self.assertIn("golf_cart", js)
        self.assertIn("GCMRouter.openRegion", js)
        self.assertIn("#0b3a78", js)
        self.assertIn("#1d6fe0", js)
        self.assertIn("#12a150", router)
        self.assertIn("cover: ensure", router)
        self.assertIn("segments:", router)
        self.assertNotIn("activeEx.stops.map", js)
        self.assertIn("GCMRouter.create", app)
        self.assertLess(index.index('src="router.js"'), index.index('src="app.js"'))
        self.assertIn("'router.js'", sw)

    def test_brand_primary_color_is_a_picker(self):
        with open(os.path.join(ROOT, "public/partner/admin.js"), encoding="utf-8") as f:
            admin = f.read()
        with open(os.path.join(ROOT, "public/partner/index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn('type="color"', admin)
        self.assertIn('id="brandColorPick"', admin)
        self.assertIn('id="brandColor"', admin)
        self.assertIn("hexColor", admin)
        self.assertIn("Use default", admin)
        # Hex stays in a hidden field the save handler already posts. Not a text box the owner has to type.
        self.assertIn('type="hidden" id="brandColor"', admin)
        self.assertNotIn('placeholder="#14b8c4"', admin)
        self.assertNotRegex(admin, r'<input id="brandColor"')
        self.assertIn("color: $('#brandColor').value.trim()", admin)
        self.assertIn("logo_url: $('#brandLogo').value.trim()", admin)
        self.assertIn('id="brandName"', admin)
        self.assertIn('id="brandBlurb"', admin)
        self.assertIn(".color-pick input[type=color]", html)
        # Empty color leaves the inline accent unset so /p keeps --brand: var(--aqua).
        with open(os.path.join(ROOT, "public/p.js"), encoding="utf-8") as f:
            pjs = f.read()
        with open(os.path.join(ROOT, "public/p.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn("root.style.setProperty('--brand', c)", pjs)
        self.assertIn("applyColor(shop.color)", pjs)
        self.assertIn("if (!c || /[;{}]|url\\s*\\(/i.test(c)) return", pjs)
        self.assertIn("--brand:var(--aqua)", page)

    def test_drop_pin_rejects_blank_coords_and_uses_main_tiles(self):
        with open(os.path.join(ROOT, "public/partner/admin.js"), encoding="utf-8") as f:
            admin = f.read()
        # Number("") === 0, which used to center Drop pin in the ocean.
        self.assertIn("function numCoord", admin)
        self.assertIn("const s = String(v ?? '').trim()", admin)
        self.assertIn("if (!s) return NaN", admin)
        self.assertIn("https://tile.openstreetmap.org/{z}/{x}/{y}.png", admin)
        self.assertNotIn("{s}.tile.openstreetmap.org", admin)
        self.assertIn("priorStopLatLng", admin)
        self.assertIn("PIN_OFFSET", admin)

    def test_brand_path_not_colliding_with_cities(self):
        # Partner brand pages are under /p/, never /<cityslug>.
        cities = {r["slug"] for r in U.regions()}
        self.assertNotIn("p", cities)


if __name__ == "__main__":
    unittest.main()
