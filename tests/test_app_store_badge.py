"""Max, Oct 22: the black Download on the App Store badge, and never the word testflight on the page.
The badge and the MobileApplication installUrl point at the live App Store listing (Nov 4 2026).
The map page og:description still ends with "Free to use." (Max Oct 22)."""
import os, re, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B, seo_common as C
URL = "https://apps.apple.com/us/app/golf-cart-maps/id6823958385"
def strip_urls(t): return t.replace(URL, "")
class AppStoreBadge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory(); cls.out = os.path.join(cls.t.name, "w"); B.build(out=cls.out, native=False)
        cls.home = open(os.path.join(cls.out, "index.html")).read()
        cls.map = open(os.path.join(cls.out, "map.html")).read()
    @classmethod
    def tearDownClass(cls): cls.t.cleanup()
    def test_constant_is_the_live_listing(self):
        self.assertEqual(C.APPSTORE, URL)
        self.assertFalse(hasattr(C, "TESTFLIGHT"))
        self.assertNotIn("testflight.apple.com", C.APPSTORE)
        self.assertNotIn("id0000000000", C.APPSTORE)
    def test_badge_present_and_linked(self):
        badges = re.findall(r'<a class="appstore" href="([^"]+)"[^>]*><img src="/download-on-the-app-store.svg"[^>]*alt="Download on the App Store"', self.home)
        self.assertGreaterEqual(len(badges), 2); self.assertTrue(all(h == URL for h in badges))
        svg = open(os.path.join(C.PUB, "download-on-the-app-store.svg")).read()
        self.assertIn("Download_on_the_App_Store_Badge", svg)   # Apple's official artwork, unmodified
        self.assertTrue(os.path.exists(os.path.join(self.out, "download-on-the-app-store.svg")))
        hubs = open(os.path.join(self.out, "lsv.html")).read()
        self.assertIn('href="%s"' % URL, hubs)
        self.assertIn('"installUrl": "%s"' % URL, self.home)
    def test_no_testflight_text(self):
        for root, _, fs in os.walk(self.out):
            if os.sep + "data" in root: continue
            for f in fs:
                if not f.endswith((".html", ".txt", ".xml", ".json", ".webmanifest")): continue
                t = strip_urls(open(os.path.join(root, f), errors="ignore").read())
                self.assertNotRegex(t, r"(?i)testflight", os.path.join(root, f))
                self.assertNotIn("testflight.apple.com", open(os.path.join(root, f), errors="ignore").read())
        llms = open(os.path.join(C.PUB, "llms.txt")).read()
        self.assertNotRegex(strip_urls(llms), r"(?i)testflight")
        self.assertIn(URL, llms)
    def test_smart_app_banner(self):
        banner = '<meta name="apple-itunes-app" content="app-id=6823958385">'
        self.assertIn(banner, self.home)
        self.assertIn(banner, self.map)
        self.assertEqual(C.APP_ID, "6823958385")
    def test_og_free_text_unchanged(self):
        # Map page (public/index.html) keeps the standing og line. Landing keeps " Free to use."
        for frozen in re.findall(r'<meta (?:property="og:description"|name="twitter:description")[^>]*>', open(os.path.join(C.PUB, "index.html")).read()):
            self.assertIn(frozen, self.map)
            self.assertTrue(frozen.endswith('Free to use.">'))
        self.assertRegex(self.home, r'<meta property="og:description" content="[^"]* Free to use\."')
if __name__ == "__main__": unittest.main()
