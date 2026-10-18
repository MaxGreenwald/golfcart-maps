"""Region rule citations must point at the right law.

Avalon (Catalina): the AMC requires a City vehicle permit for every vehicle including golf carts
(Title 4, Ch. 4-4, Art. 17 § 4-4.1702; rental autoettes § 4-4.1703(f); one per dwelling unit § 4-4.1703(g);
LSVs up to 138x67 in § 4-4.1705(b)(1); Art. 19 § 4-4.1903 'autoette' = CVC golf cart), https://ecode360.com/AV4054.
The 25 mph street limit for golf carts is CVC 21716. CVC 21115 is the golf-course combined-use designation, not the 25 mph rule."""
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGIONS = json.load(open(os.path.join(ROOT, "public/data/regions.json")))


class RegionCites(unittest.TestCase):
    def test_avalon_rule(self):
        r = next(x for x in REGIONS if x["id"] == "avalon")
        cite = r["rule"]["cite"]
        self.assertEqual(r["rule"]["max_posted"], 25)
        for must in ("§ 4-4.1702", "§ 4-4.1703(f)", "§ 4-4.1703(g)", "CVC 21716"):
            self.assertIn(must, cite)
        self.assertNotIn("21115", cite)
        self.assertTrue(r["rule"]["url"].startswith("https://ecode360.com/AV4054"))
        self.assertIn("rental carts and permitted autoettes", r["cover"])

    def test_no_region_cites_21115_as_the_25mph_rule(self):
        for r in REGIONS:
            cite = (r.get("rule") or {}).get("cite", "")
            if re.search(r"21115(?!\.1)", cite) and re.search(r"(≤|<=|or less|under)\s*25", cite):
                self.fail(f"{r['id']}: CVC 21115 is cited for the 25 mph golf cart rule; that is CVC 21716")


if __name__ == "__main__":
    unittest.main()
