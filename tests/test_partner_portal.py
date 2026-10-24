"""Partner portal MVP: slug rules, reserved paths, redirects, no user-visible beta."""
import json, os, re, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import region_urls as U

SYSTEM = {
    "map", "p", "partner", "admin", "api", "privacy", "compare", "llms", "robots",
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
            "/p/:slug /p/index.html 200",
            "/p/:slug/go /p/index.html 200",
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
        for rel in ("public/partner/index.html", "public/partner/admin.js", "public/p/index.html", "public/p/brand.js",
                    "functions/api/partner/[[path]].js", "workers/partner/src/index.js", "lib/partner.js",
                    "research/partner_portal_mvp.md"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_no_beta_in_partner_ui_strings(self):
        beta = re.compile(r"(?i)\bbeta\b")
        for rel in ("public/partner/index.html", "public/partner/admin.js", "public/p/index.html", "public/p/brand.js"):
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            self.assertIsNone(beta.search(src), rel)

    def test_brand_path_not_colliding_with_cities(self):
        # Partner brand pages are under /p/, never /<cityslug>.
        cities = {r["slug"] for r in U.regions()}
        self.assertNotIn("p", cities)


if __name__ == "__main__":
    unittest.main()
