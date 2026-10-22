"""Static region pages: unique title/H1/canonical, rules from roadrule.js, schema, no banned words."""
import json, os, re, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_pages as S, seo_common as C
class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory(); S.build(cls.t.name)
        cls.pages = {g["slug"]: open(os.path.join(cls.t.name, g["slug"] + ".html")).read() for g in C.regions()}
    def grab(self, rx, h): m = re.search(rx, h, re.S); self.assertTrue(m, rx); return m.group(1)
    def test_unique_title_h1_desc_and_self_canonical(self):
        for k in ("<title>(.*?)</title>", "<h1>(.*?)</h1>", 'name="description" content="(.*?)"'):
            vals = [self.grab(k, h) for h in self.pages.values()]
            self.assertEqual(len(set(vals)), len(vals), k)
        for slug, h in self.pages.items():
            self.assertIn(f'<link rel="canonical" href="https://golfcartmap.com/{slug}">', h)
            import html; self.assertLessEqual(len(html.unescape(self.grab('name="description" content="(.*?)"', h))), 155)
    def test_rules_match_roadrule(self):
        R = C.effective_rules()
        sd = self.pages["sandiego"]; self.assertIn("Roads posted 35 mph or less", sd); self.assertIn("CVC 21260", sd)
        self.assertIn("Not allowed on public roads here", self.pages["kailua"])  # HI: plain carts not street-legal
        for g in C.regions():
            self.assertIn("posted %d mph" % R[g["id"]]["lsv"]["max_posted"], self.pages[g["slug"]])
    def test_schema(self):
        for slug, h in self.pages.items():
            ld = json.loads(self.grab(r'<script type="application/ld\+json">(.*?)</script>', h))
            types = {x["@type"] for x in ld}
            self.assertEqual(types, {"Organization", "WebSite", "SoftwareApplication", "FAQPage", "BreadcrumbList"})
            app = [x for x in ld if x["@type"] == "SoftwareApplication"][0]
            self.assertNotIn("offers", app); self.assertEqual(app["name"], "Golf Cart Maps")
            faq = [x for x in ld if x["@type"] == "FAQPage"][0]
            for q in faq["mainEntity"]:  # FAQ schema matches visible text
                self.assertIn(C.e(q["name"]), h); self.assertIn(C.e(q["acceptedAnswer"]["text"]), h)
    def test_cta_and_no_banned_words(self):
        for slug, h in self.pages.items():
            self.assertRegex(h, r'class="cta" href="/\?r=[a-z0-9]+"')
            text = re.sub(r"<[^>]+>", " ", h)
            self.assertNotRegex(text, r"(?i)\bfree\b|verified|carplay|android")
    def test_sw_caches_only_root_as_shell(self):
        sw = open(os.path.join(C.PUB, "sw.js")).read(); self.assertIn("r.ok&&u.pathname==='/'", sw)
if __name__ == "__main__": unittest.main()
