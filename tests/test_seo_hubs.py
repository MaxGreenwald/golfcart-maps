"""Plural hub /golf-cart-maps and /lsv. Home keeps its own canonical. Hubs self-canonical.
The four markets already have map regions, so their pages link to /map?r= and do not invent a second rule set."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_common as C, seo_hubs as H, seo_landing as L, seo_pages as P, seo_towns as T

EM = "\u2014"
PUB = C.PUB


def ld(html):
    return json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))


class Hubs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = L.render()
        cls.maps = H.maps_page()
        cls.lsv = H.lsv_page()
        cls.n = len(C.regions())

    def test_home_plural_and_links(self):
        h = self.home
        title = re.search(r"<title>(.*?)</title>", h).group(1)
        h1 = re.search(r"<h1>(.*?)</h1>", h).group(1)
        desc = re.search(r'<meta name="description" content="([^"]*)"', h).group(1)
        self.assertEqual(title, f"Golf Cart Maps: golf cart map for {self.n} towns | LSV Map")
        self.assertEqual(h1, f"Golf Cart Maps: golf cart map for {self.n} towns")
        self.assertIn("Golf Cart Maps", desc)
        self.assertIn("golf cart map", desc)
        self.assertIn("Free to use", desc)
        self.assertIn('href="/golf-cart-maps"', h)
        self.assertIn('href="/lsv"', h)
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/">', h)
        self.assertIn("https://golfcartmap.com/golf-cart-maps", h)
        self.assertNotIn(EM, h)

    def test_plural_hub_canonical_and_schema(self):
        h = self.maps
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/golf-cart-maps">', h)
        self.assertNotIn('href="https://golfcartmap.com/"', re.search(r'<link rel="canonical"[^>]*>', h).group(0))
        self.assertIn(f"<h1>Golf cart maps for {self.n} towns</h1>", h)
        self.assertIn("golf cart map", h.lower())
        for slug in ("hiltonhead", "villages", "gulfshores", "naples"):
            self.assertIn(f'href="/{slug}"', h)
        for r in C.regions():
            self.assertIn(f'href="/{r["slug"]}"', h)
        types = {x["@type"] for x in ld(h)}
        self.assertTrue({"CollectionPage", "ItemList", "FAQPage", "BreadcrumbList", "Organization"} <= types)
        self.assertEqual(len([x for x in ld(h) if x["@type"] == "ItemList"][0]["itemListElement"]), self.n)
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", h), r"(?i)\bbeta\b|verified|android")
        self.assertNotIn(EM, h)
        self.assertIn("<loc>https://golfcartmap.com/golf-cart-maps</loc>", open(os.path.join(PUB, "sitemap.xml")).read())

    def test_lsv_page(self):
        h = self.lsv
        title = re.search(r"<title>(.*?)</title>", h).group(1)
        self.assertIn("LSV Map App", title)
        self.assertIn("low speed vehicle map", title.lower())
        self.assertIn("<h1>LSV map app: low speed vehicle map</h1>", h)
        self.assertIn('<link rel="canonical" href="https://golfcartmap.com/lsv">', h)
        self.assertIn("35 mph or less in", h)
        Lims = C.lsv_limits()
        self.assertIn("35 mph or less in %d of our %d regions" % (Lims["n35"], Lims["n"]), re.sub(r"<[^>]+>", " ", h))
        for mp, gs in Lims["other"].items():
            for g in gs:
                self.assertIn(C.e(g["name"]), h)
        self.assertIn('href="/map?veh=lsv"', h)
        for slug, rid in (("hiltonhead", "hhi"), ("villages", "villages"), ("gulfshores", "gulfshores"), ("naples", "naples")):
            self.assertIn(f'href="/map?r={rid}&amp;veh=lsv"', h)
            self.assertIn(f'href="/{slug}"', h)
        qs = [q["name"] for q in next(x for x in ld(h) if x["@type"] == "FAQPage")["mainEntity"]]
        self.assertIn("Is there an LSV map app?", qs)
        self.assertIn("What is a low speed vehicle map?", qs)
        self.assertNotIn("offers", next(x for x in ld(h) if x["@type"] == "SoftwareApplication"))
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", h), r"(?i)\bbeta\b|verified|android")
        self.assertNotIn(EM, h)
        self.assertIn("<loc>https://golfcartmap.com/lsv</loc>", open(os.path.join(PUB, "sitemap.xml")).read())

    def test_markets_link_to_live_maps(self):
        R = C.effective_rules()
        regs = {g["slug"]: g for g in C.regions()}
        for slug, place in P.MARKETS.items():
            g = regs[slug]
            h = P.region_page(g, R[g["id"]])
            self.assertIn(f"{place} golf cart map and LSV map", h)
            self.assertIn(f"{place} golf cart maps:", h)
            self.assertIn(f'href="/map?r={g["id"]}"', h)
            self.assertIn(f'href="/map?r={g["id"]}&amp;veh=lsv"', h)
            self.assertIn('<link rel="canonical" href="https://golfcartmap.com/%s">' % slug, h)
            self.assertNotIn(EM, h)
        gs = P.region_page(regs["gulfshores"], R["gulfshores"])
        self.assertIn("Ordinance No. 2210", gs)
        self.assertIn("Cotton Bay", gs)
        self.assertIn("2025-1521", gs)
        self.assertIn("Chapter 70", gs)
        self.assertNotIn("Meyer Park", gs)
        # Rules in the table still come from roadrule, not from the ordinance blurbs.
        self.assertIn("posted %d mph" % R["gulfshores"]["lsv"]["max_posted"], gs)

    def test_town_titles_with_a_hook(self):
        regs = {g["slug"]: g for g in C.regions()}
        want = {
            ("gulfshores", "gulf-shores.json"): "Gulf Shores golf cart map and LSV map",
            ("gulfshores", "orange-beach.json"): "Orange Beach golf cart map and LSV map",
            ("hiltonhead", "hilton-head-island.json"): "Hilton Head golf cart map and LSV map",
            ("villages", "the-villages.json"): "The Villages golf cart map and LSV map",
            ("naples", "naples.json"): "Naples golf cart map and LSV map",
        }
        for (region, name), phrase in want.items():
            f = os.path.join(T.TOWNS, region, name)
            tw = json.load(open(f))
            h = T.town_page(tw, regs[region], f)
            self.assertIn(phrase, re.search(r"<title>(.*?)</title>", h).group(1))
            self.assertIn(tw["question_title"], h)
        # A town without the hook keeps the old title shape.
        f = os.path.join(T.TOWNS, "30a", "seaside.json")
        tw = json.load(open(f))
        h = T.town_page(tw, regs["30a"], f)
        self.assertIn("Rules and legal roads", re.search(r"<title>(.*?)</title>", h).group(1))
        self.assertNotIn("seo_title", tw)


if __name__ == "__main__":
    unittest.main()
