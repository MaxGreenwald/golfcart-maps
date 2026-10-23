"""Max, Oct 23 2026: SEO/AEO targets both "golf cart map" and "golf cart maps" (people mix up the s).
The brand stays "Golf Cart Maps"; the home page, llms.txt and the region/town templates also say "golf cart map" naturally."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import gen_llms, seo_landing, seo_common
PUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")
SING = re.compile(r"(?i)\bgolf cart map\b(?!s)")
PLUR = re.compile(r"(?i)\bgolf cart maps\b")

def has_both(t):
    return bool(SING.search(t)) and bool(PLUR.search(t))

class T(unittest.TestCase):
    def test_home_page_both(self):
        h = seo_landing.render()
        self.assertTrue(has_both(h))
        title = re.search(r"<title>(.*?)</title>", h).group(1)
        self.assertTrue(has_both(title), title)
        desc = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
        self.assertRegex(desc, SING); self.assertIn("Free to use", desc)
        self.assertIn("Is it Golf Cart Map or Golf Cart Maps?", h)

    def test_schema_alternate_names(self):
        for f in (seo_common.org, seo_common.website, seo_common.software, seo_common.mobile_app):
            d = f(); self.assertEqual(d["name"], "Golf Cart Maps"); self.assertEqual(d["alternateName"], ["Golf Cart Map", "GolfCartMap"])

    def test_llms_both(self):
        t = open(os.path.join(PUB, "llms.txt")).read()
        intro = next(l for l in t.splitlines() if l.startswith("> "))
        self.assertTrue(has_both(intro), intro)
        self.assertTrue(has_both(gen_llms.render()))

    def test_map_page_both(self):
        h = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
        self.assertTrue(has_both(re.search(r"<title>(.*?)</title>", h).group(1)))

if __name__ == "__main__": unittest.main()
