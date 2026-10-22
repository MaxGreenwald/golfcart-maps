"""Max, Oct 22 1:54 PM: "don't say testflight just link to it and use the apple app store logo".
No visible or schema 'testflight' text on the built site or llms.txt (the join URL in href/installUrl is fine);
the official black Download on the App Store badge links to it in the hero and the iPhone + CarPlay section."""
import os, re, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import build_web as B, seo_common as C
URL = "https://testflight.apple.com/join/P7dVC4zh"
def strip_urls(t): return t.replace(URL, "")
class AppStoreBadge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory(); cls.out = os.path.join(cls.t.name, "w"); B.build(out=cls.out, native=False)
        cls.home = open(os.path.join(cls.out, "index.html")).read()
    @classmethod
    def tearDownClass(cls): cls.t.cleanup()
    def test_badge_present_and_linked(self):
        badges = re.findall(r'<a class="appstore" href="([^"]+)"[^>]*><img src="/download-on-the-app-store.svg"[^>]*alt="Download on the App Store"', self.home)
        self.assertGreaterEqual(len(badges), 2); self.assertTrue(all(h == URL for h in badges))
        svg = open(os.path.join(C.PUB, "download-on-the-app-store.svg")).read()
        self.assertIn("Download_on_the_App_Store_Badge", svg)   # Apple's official artwork, unmodified
        self.assertTrue(os.path.exists(os.path.join(self.out, "download-on-the-app-store.svg")))
    def test_no_testflight_text(self):
        for root, _, fs in os.walk(self.out):
            if os.sep + "data" in root: continue
            for f in fs:
                if not f.endswith((".html", ".txt", ".xml", ".json", ".webmanifest")): continue
                t = strip_urls(open(os.path.join(root, f), errors="ignore").read())
                self.assertNotRegex(t, r"(?i)testflight", os.path.join(root, f))
        self.assertNotRegex(strip_urls(open(os.path.join(C.PUB, "llms.txt")).read()), r"(?i)testflight")
if __name__ == "__main__": unittest.main()
