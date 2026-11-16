"""/app page, /compare freshness and the singular "golf cart map" fixes (Max t151s713, Nov 16 2026)."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_common as C, seo_compare as SC, seo_hubs as H, seo_landing as L
SING = re.compile(r"(?i)\bgolf cart map\b(?!s)")


def ld(h):
    return json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1))


class App(unittest.TestCase):
    def test_app_page(self):
        h = H.app_page(); text = re.sub(r"<[^>]+>", " ", re.search(r"(?s)<main>(.*)</main>", h).group(1))
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/app">', h)
        self.assertRegex(re.search(r"<h1>(.*?)</h1>", h).group(1), SING)
        self.assertIn('href="%s"' % C.APPSTORE, h)
        self.assertIn("Free to use.", re.search(r'<meta name="description" content="([^"]*)"', h).group(1))
        # Only what the live App Store listing says: no CarPlay/Android/ratings/beta/testflight claims, no em dash.
        self.assertNotRegex(text, r"(?i)carplay|android|\bbeta\b|verified|testflight|\brating|\bstars\b")
        self.assertNotIn("\u2014", h)
        types = {x["@type"] for x in ld(h)}
        self.assertTrue({"MobileApplication", "WebPage", "FAQPage", "BreadcrumbList"} <= types)
        app = next(x for x in ld(h) if x["@type"] == "MobileApplication")
        self.assertEqual(app["installUrl"], C.APPSTORE); self.assertNotIn("aggregateRating", app)
        self.assertNotRegex(json.dumps(ld(h)), r"(?i)carplay")

    def test_app_in_sitemap_and_redirects(self):
        sm = open(os.path.join(C.PUB, "sitemap.xml")).read()
        self.assertIn("<loc>https://golfcartmap.com/app</loc>", sm)
        red = open(os.path.join(C.PUB, "_redirects")).read().splitlines()
        self.assertIn("/app/ /app 301", red)
        self.assertIn("/golf-cart-map / 301", red)
        self.assertIn("/golf-cart-map/ / 301", red)

    def test_compare_no_longer_says_in_review(self):
        h = SC.render(); text = re.sub(r"<[^>]+>", " ", h)
        self.assertNotIn("in review", text.lower())
        self.assertIn("iPhone app on the App Store", text)
        self.assertIn('href="%s"' % C.APPSTORE, h)
        self.assertIn("updated %s" % SC.OURS_AS_OF, text)
        self.assertIn("as of %s" % SC.AS_OF, text)  # competitor rows keep their own date

    def test_home_says_golf_cart_map_near_the_top(self):
        h = L.render()
        sub = re.search(r'<p class="sub">(.*?)</p>', h).group(1)
        self.assertTrue(sub.startswith("The golf cart map for %d beach and golf towns." % len(C.regions())), sub)
        self.assertIn('href="/app"', h)
        # og/meta description untouched: still ends "Free to use."
        self.assertTrue(re.search(r'og:description" content="([^"]*)"', h).group(1).endswith("Free to use."))


if __name__ == "__main__":
    unittest.main()
