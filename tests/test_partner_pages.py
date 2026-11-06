"""Partner invite pages and top nav (Max via Gary, Nov 6 2026)."""
import os, re, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B, seo_common as C, seo_partner as P, seo_landing as L

EM = "\u2014"
CAL = "calendar.app.google"
NAMES = ("Club Car", "Bintelli", "Evolution")

class PartnerPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shops = P.shops_page()
        cls.mfg = P.manufacturers_page()
        cls.home = L.render()
        cls.t = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.t.name, "w")
        B.build(out=cls.out, native=False)

    @classmethod
    def tearDownClass(cls):
        cls.t.cleanup()

    def test_nav(self):
        for html in (self.home, self.shops, self.mfg):
            self.assertIn(">Map</a>", html)
            self.assertIn(">Towns</a>", html)
            self.assertIn(">For Rental Shops</a>", html)
            self.assertIn(">For Manufacturers</a>", html)
            self.assertIn(">Get the App</a>", html)
            self.assertIn(C.APPSTORE, html)
            self.assertNotIn(EM, html)
            self.assertNotIn(CAL, html)

    def test_shops_page(self):
        h = self.shops
        self.assertIn("Get your renters on the legal roads", h)
        self.assertIn("Get your shop on the map", h)
        self.assertIn("at no cost", h)
        self.assertIn("subject=Rental%20shop%3A%20get%20on%20the%20map", h)
        self.assertNotRegex(h, r"\$\d")
        self.assertNotIn("portal", h.lower())
        for n in NAMES: self.assertNotIn(n, h)
        self.assertTrue(os.path.exists(os.path.join(self.out, "for-rental-shops.html")))

    def test_manufacturers_page(self):
        h = self.mfg
        self.assertIn("Put legal-road maps on every cart", h)
        self.assertIn("Talk with Max about a pilot", h)
        self.assertIn("CarPlay", h)
        self.assertIn("subject=Manufacturer%20%2F%20dealer%20pilot", h)
        self.assertNotRegex(h, r"\$\d")
        self.assertNotIn(CAL, h)
        for n in NAMES: self.assertNotIn(n, h)
        self.assertTrue(os.path.exists(os.path.join(self.out, "for-manufacturers.html")))

    def test_home_teasers_and_hero(self):
        h = self.home
        self.assertIn("Know which roads your golf cart can legally ride.", h)
        self.assertIn('id="townFind"', h)
        self.assertIn("How it works", h)
        self.assertIn('href="/for-rental-shops"', h)
        self.assertIn('href="/for-manufacturers"', h)
        self.assertIn("/hero-map.jpg", h)
        self.assertNotIn("For manufacturers and OEMs", h)  # buried bands gone
        self.assertNotIn("For shops and dealers", h)
        self.assertNotIn(EM, h)
        self.assertNotIn(CAL, h)

    def test_sitemap_and_llms(self):
        sm = open(os.path.join(C.PUB, "sitemap.xml")).read()
        self.assertIn("https://golfcartmap.com/for-rental-shops", sm)
        self.assertIn("https://golfcartmap.com/for-manufacturers", sm)
        llms = open(os.path.join(C.PUB, "llms.txt")).read()
        self.assertIn("for-rental-shops", llms)
        self.assertIn("for-manufacturers", llms)

if __name__ == "__main__":
    unittest.main()
