"""Max, Oct 23 2026: SEO/AEO targets both "golf cart map" and "golf cart maps" (people mix up the s).
The brand stays "Golf Cart Maps"; the home page, llms.txt and the region/town templates also say "golf cart map" naturally."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import gen_llms, seo_landing, seo_common, seo_pages, seo_towns
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
        h1 = re.search(r"<h1>(.*?)</h1>", h).group(1)
        self.assertRegex(h1, r"^Golf Cart Maps: golf cart map for \d+ towns$")
        desc = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
        self.assertTrue(has_both(desc), desc)
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
        title = re.search(r"<title>(.*?)</title>", h).group(1)
        self.assertTrue(has_both(title))
        self.assertIn("LSV Map", title)

    # Max Oct 23 11:56 AM PT: LSV targeting next to golf cart map(s), accurate to our LSV rules (not a blanket 35 mph)
    def test_home_lsv(self):
        h = seo_landing.render(); txt = re.sub(r"<[^>]+>", " ", h)
        for pat in [r"\bLSV map\b", r"\bLSV map app\b", r"(?i)\blow speed vehicle map\b", r"(?i)\bstreet[- ]legal golf cart\b", r"35 mph or less"]:
            self.assertRegex(txt, pat)
        self.assertRegex(re.search(r"<title>(.*?)</title>", h).group(1), r"\bLSV Map\b")
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', h, re.S).group(1))
        sw = next(x for x in ld if x["@type"] == "SoftwareApplication"); self.assertIn("LSV map app", sw["description"])
        fq = next(x for x in ld if x["@type"] == "FAQPage"); qs = [q["name"] for q in fq["mainEntity"]]
        self.assertIn("Is there an LSV map app?", qs); self.assertIn("Where can I drive my LSV?", qs)

    def test_lsv_limit_not_overclaimed(self):
        """Regions whose LSV limit isn't 35 mph are named wherever the home page and llms.txt give the 35 mph number."""
        L = seo_common.lsv_limits(); h = seo_landing.render(); t = open(os.path.join(PUB, "llms.txt")).read()
        self.assertIn("35 mph or less in %d of our %d regions" % (L["n35"], L["n"]), t)
        for mp, gs in L["other"].items():
            for g in gs: self.assertIn(g["name"], t); self.assertIn(seo_common.e(g["name"]), h)

    def test_llms_lsv(self):
        t = open(os.path.join(PUB, "llms.txt")).read()
        self.assertRegex(t.splitlines()[2], r"\bLSV map\b"); self.assertRegex(t, r"(?i)low speed vehicle map")

    def test_region_and_town_templates_lsv(self):
        R = seo_common.effective_rules(); regs = {g["slug"]: g for g in seo_common.regions()}
        for slug in ("sandiego", "oceancitynj"):
            g = regs[slug]; h = seo_pages.region_page(g, R[g["id"]])
            self.assertIn("Where can I drive my LSV in", h); self.assertRegex(h, SING); self.assertIn("LSV map", h)
            self.assertIn("LSVs on roads posted %s mph or less" % R[g["id"]]["lsv"]["max_posted"], h)
        f = os.path.join(seo_towns.TOWNS, "30a", "seaside.json"); tw = json.load(open(f))
        h = seo_towns.town_page(tw, regs["30a"], f); self.assertIn("Where can I drive my LSV in Seaside?", h); self.assertRegex(h, SING)

if __name__ == "__main__": unittest.main()
