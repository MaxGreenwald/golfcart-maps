"""Hilton Head Island town page shows a followed Local resources link to HHI.com's golf cart rentals guide."""
import os, re, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_towns as T
class LocalResources(unittest.TestCase):
    def test_hhi_link(self):
        out = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, out)
        open(os.path.join(out, "sitemap.xml"), "w").write("<urlset></urlset>")
        T.build(out)
        h = open(os.path.join(out, "hiltonhead", "hilton-head-island.html")).read()
        self.assertIn("<h2>Local resources</h2>", h)
        self.assertIn('<li>Renting a cart? See <a href="https://hhi.com/plan-your-trip/getting-around/golf-cart-rentals/">HHI.com&#x27;s golf cart rentals guide</a>.</li>', h)
        a = re.search(r'<a href="https://hhi\.com/[^"]*"[^>]*>', h).group(0)
        self.assertNotIn("nofollow", a)
        sec = h.split("<h2>Local resources</h2>", 1)[1].split("<h2>", 1)[0]
        self.assertNotRegex(sec, r"(?i)beta")
if __name__ == "__main__": unittest.main()
