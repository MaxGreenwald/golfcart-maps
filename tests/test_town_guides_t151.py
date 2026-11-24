"""Town guides for St. Augustine, Galveston, Key West and Palm Desert (Max t151s713, Nov 16 2026).

Hard rule: a guide never calls a road legal unless the map data has it posted at or under that town's cap
(posted sign, DOT layer, OSM maxspeed, ordinance) under public/roadrule.js. Every road a guide names as
off limits is red on the map for both vehicles. Where plain golf carts are designated-only and we have no
street list, the map opens nothing to them except cart paths and roads mapped as designated, as the guide says."""
import json, os, re, subprocess, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import seo_common as C, seo_towns as T
HERE = os.path.dirname(os.path.abspath(__file__))

# region id, town file, roads the guide says an LSV may use, roads the guide says are off limits (map red)
GUIDES = [
    ("staug", "staugustine/st-augustine.json", ["Bridge of Lions"],
     ["US 1", "SR 312", "SR 207", "Ponce de Leon Boulevard", "A1A"]),
    ("galveston", "galveston/galveston.json", [],
     ["Broadway - Avenue J", "Broadway Street", "Harborside Drive", "61st Street", "Ferry Road",
      "San Luis Pass Road", "Teichman Road", "Pelican Island Causeway", "Gulf Freeway"]),
    ("keywest", "keywest/key-west.json", ["Duval Street"], []),
    ("coachella", "coachella/palm-desert.json", [], ["East Palm Canyon Drive", "Pines To Palms Highway", "CA- 111"]),
]
DESIGNATED_ONLY_NO_LIST = {"staug", "keywest"}


def claims(rid):
    return json.loads(subprocess.run(["node", os.path.join(HERE, "road_claims.mjs"), rid], capture_output=True, text=True, check=True).stdout)


class Guides(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {rid: claims(rid) for rid, *_ in GUIDES}
        cls.regs = {r["slug"]: r for r in C.regions()}

    def test_lsv_ok_roads_are_fully_posted_under_the_cap(self):
        for rid, _f, ok, _red in GUIDES:
            for n in ok:
                r = self.data[rid]["roads"][n]
                self.assertGreater(r["mi"], 0, (rid, n))
                self.assertAlmostEqual(r["lsv"][0], r["mi"], places=6, msg=(rid, n, "not all posted"))

    def test_named_off_limits_roads_are_red_for_both(self):
        for rid, _f, _ok, red in GUIDES:
            for n in red:
                r = self.data[rid]["roads"][n]
                self.assertGreater(r["mi"], 0, (rid, n))
                for v in ("lsv", "golf_cart"):
                    self.assertAlmostEqual(r[v][2], r["mi"], places=6, msg=(rid, n, v, "not all red"))

    def test_designated_only_towns_show_no_cart_streets(self):
        for rid in DESIGNATED_ONLY_NO_LIST:
            self.assertTrue(self.data[rid]["rules"]["golf_cart"].get("designated_only"), rid)
            self.assertLess(self.data[rid]["golf_cart_open_street_mi"], 1e-9, rid)

    def test_caps_in_copy_match_the_map(self):
        for rid, f, *_ in GUIDES:
            t = json.load(open(os.path.join(T.TOWNS, f)))
            R = self.data[rid]["rules"]
            self.assertEqual(t["lsv"]["speed_line"], "%d mph" % R["lsv"]["max_posted"], f)
            if not R["golf_cart"].get("designated_only"):
                self.assertEqual(t["golf_cart"]["speed_line"], "%d mph" % R["golf_cart"]["max_posted"], f)

    def test_pages_render_clean(self):
        for rid, f, *_ in GUIDES:
            p = os.path.join(T.TOWNS, f); t = json.load(open(p)); T.check(t, p)
            h = T.town_page(t, self.regs[t["region"]], p); text = re.sub(r"<[^>]+>", " ", h)
            self.assertNotIn("\u2014", h); self.assertNotIn("\u2013", h)
            self.assertNotRegex(text, r"(?i)\bbeta\b|verified|carplay|android")
            self.assertIn("Not legal advice; posted signs win.", h)
            self.assertIn(f'href="/map/{t["region"]}?lat=', h)
            self.assertTrue(all(r["source_url"].startswith("https://") for r in t["rules"]), f)


if __name__ == "__main__":
    unittest.main()
