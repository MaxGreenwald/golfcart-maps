"""/compare: factual, dated, no banned words, no price for us, schema."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_compare as S
class T(unittest.TestCase):
    def test_page(self):
        h = S.render(); text = re.sub(r"<[^>]+>", " ", h)
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/compare">', h)
        self.assertIn("<h1>How do golf cart navigation apps compare?</h1>", h)
        self.assertIn("as of 2026-10-19", text.lower())
        self.assertNotRegex(text, r"(?i)\bbeta\b|verified|carplay|android|\b(worst|bad|terrible|scam|outdated|abandoned)\b")
        for a in S.APPS: self.assertIn(S.e(a[0]), h)
        ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1))
        self.assertEqual({x["@type"] for x in ld}, {"Organization", "WebSite", "FAQPage", "BreadcrumbList"})
        self.assertNotIn('"price"', json.dumps(ld))
    def test_in_sitemap(self):
        self.assertIn("<loc>https://golfcartmap.com/compare</loc>", open(os.path.join(S.PUB, "sitemap.xml")).read())
if __name__ == "__main__": unittest.main()
