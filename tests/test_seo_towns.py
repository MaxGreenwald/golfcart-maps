"""Town page template: question H1, answer, 'Rules last checked', citations, FAQ schema = visible text, sitemap lastmod."""
import json, os, re, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_towns as T, seo_common as C
EX = os.path.join(T.TOWNS, "_example.json")
class Towns(unittest.TestCase):
    def render(self, mut=None):
        src = tempfile.mkdtemp(); out = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, src); self.addCleanup(shutil.rmtree, out)
        t = json.load(open(EX)); mut and mut(t)
        os.makedirs(os.path.join(src, "sandiego")); json.dump(t, open(os.path.join(src, "sandiego", t["slug"] + ".json"), "w"))
        open(os.path.join(out, "sitemap.xml"), "w").write("<urlset></urlset>")
        T.build(out, src); return open(os.path.join(out, "sandiego", t["slug"] + ".html")).read(), open(os.path.join(out, "sitemap.xml")).read()
    def test_layout(self):
        h, sm = self.render()
        self.assertIn("<h1>Can you drive a golf cart in Pacific Beach?</h1>", h)
        self.assertIn("Rules last checked 2026-10-20", h)
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", h), r"(?i)verified|\bfree\b")
        self.assertIn('href="https://golfcartmap.com/sandiego/pacific-beach"', h)
        self.assertIn(">CVC 21260</a>", h); self.assertIn("Not legal advice; posted signs win.", h)
        self.assertIn("/?r=sd&amp;lat=32.7978&amp;lon=-117.24&amp;z=16", h)
        self.assertIn("<loc>https://golfcartmap.com/sandiego/pacific-beach</loc><lastmod>2026-10-20</lastmod>", sm)
        self.assertNotIn("noindex", h)
    def test_schema_matches_visible(self):
        h, _ = self.render()
        ld = json.loads(re.search(r'application/ld\+json">(.*?)</script>', h, re.S).group(1))
        self.assertEqual({x["@type"] for x in ld}, {"WebPage", "BreadcrumbList", "FAQPage"})
        self.assertEqual([x for x in ld if x["@type"] == "WebPage"][0]["dateModified"], "2026-10-20")
        for q in [x for x in ld if x["@type"] == "FAQPage"][0]["mainEntity"]:
            self.assertIn(C.e(q["name"]), h); self.assertIn(C.e(q["acceptedAnswer"]["text"]), h)
    def test_rejects_bad_copy(self):
        for mut in (lambda t: t.update(answer_short="This is free. " * 3), lambda t: t.update(faq=[{"q": "Verified?", "a": "Yes"}]),
                    lambda t: t.update(answer_short="word " * 61), lambda t: t.pop("last_checked")):
            with self.assertRaises(SystemExit): self.render(mut)
    def test_example_is_noindex_preview(self):
        out = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, out); T.build(out)
        self.assertIn('content="noindex"', open(os.path.join(out, "_preview", "town-example.html")).read())
if __name__ == "__main__": unittest.main()
