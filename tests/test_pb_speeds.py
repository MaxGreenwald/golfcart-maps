"""Pacific Beach roads that were 99/'i' (major road, unknown limit; red in every mode) now carry the cited posted speed.
Sources: scripts/overrides.py _PB_GAPS, evidence in research/pb_speeds/. Max (Oct 29 2026): Turquoise, Foothill and Beryl are OK."""
import glob, json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, "public", "data", "sd")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import overrides  # noqa: E402

IDX = json.load(open(os.path.join(SD, "index.json")))
NAMES, SOURCES = IDX["names"], IDX["sources"]
SEGS = [s for t in IDX["meta"]["tiles"] for s in json.load(open(os.path.join(SD, "tiles", t + ".json")))]
PB = (32.785, -117.26, 32.825, -117.215)


def mid(s):
    g = s[7]
    return g[len(g) // 2]


def inb(p, b):
    return b[0] <= p[1] <= b[2] and b[1] <= p[0] <= b[3]


def on(name, bb):
    return [s for s in SEGS if NAMES[s[0]] == name and inb(mid(s), bb)]


# (OSM name, gap bbox from overrides, expected mph). Every named road Max or the audit flagged.
EXPECT = [(overrides.INTEL[k]["road"], overrides.GAP_RULES[k][1], overrides.INTEL[k]["speed_mph"]) for k in overrides.GAP_RULES]
OSM = {"Turquoise St": "Turquoise Street", "Foothill Blvd": "Foothill Boulevard", "Beryl St": "Beryl Street", "Mission Blvd": "Mission Boulevard",
       "Mission Bay Dr": "Mission Bay Drive", "Balboa Ave": "Balboa Avenue", "Soledad Mountain Rd": "Soledad Mountain Road", "Garnet Ave": "Garnet Avenue"}


class PBUnknownSpeeds(unittest.TestCase):
    def test_every_gap_rule_has_a_cited_source(self):
        self.assertEqual(len(EXPECT), 9)
        for k in overrides.GAP_RULES:
            e = overrides.INTEL[k]
            self.assertTrue(e["source_url"].startswith("https://"), e)
            self.assertRegex(e["from_to_segment_if_known"], r"Mapillary|R-316675")

    def test_named_roads_are_no_longer_unknown(self):
        for road, bb, mph in EXPECT:
            segs = on(OSM[road], bb)
            self.assertTrue(segs, road)
            self.assertFalse([s for s in segs if s[2] == 99], f"{road}: still 99 in {bb}")

    def test_filled_pieces_match_the_cited_speed(self):
        for k, (_, bb) in ((k, overrides.GAP_RULES[k]) for k in overrides.GAP_RULES):
            e = overrides.INTEL[k]
            gap = [s for s in on(OSM[e["road"]], bb) if s[3] == "v" and len(s) > 8 and SOURCES[s[8]][0] == e["source_url"]]
            self.assertTrue(gap, e["road"])
            self.assertEqual({s[2] for s in gap}, {e["speed_mph"]}, e["road"])

    def test_max_roads_are_cart_usable(self):
        # Turquoise, Foothill, Beryl in PB: every piece in the box at or under 25 (CA golf cart limit).
        for name in ("Turquoise Street", "Foothill Boulevard", "Beryl Street"):
            segs = [s for s in SEGS if NAMES[s[0]] == name and inb(mid(s), PB)]
            self.assertTrue(segs, name)
            self.assertLessEqual(max(s[2] for s in segs), 25, name)

    def test_garnet_40_near_soledad_stays_40(self):
        # Mapillary 40 sign at 32.80500,-117.22397 and R-316675 Table 1 (Balboa (W) Av - Moraga Av, -5 from 45): not LSV-legal.
        m = [s for s in on("Garnet Avenue", (32.8044, -117.2250, 32.8050, -117.2240)) if s[3] == "m" and s[2] >= 30]
        self.assertTrue(m)
        self.assertEqual({s[2] for s in m}, {40})
        filled = [s for s in on("Garnet Avenue", (32.8040, -117.2250, 32.8055, -117.2235)) if s[3] == "v"]
        self.assertTrue(filled)
        self.assertEqual({s[2] for s in filled}, {40})

    def test_gap_rules_never_replace_an_osm_tag(self):
        ways = [({"name": "Turquoise Street", "maxspeed": "35 mph", "highway": "secondary"}, [[-117.256, 32.809], [-117.254, 32.8095]], ["a", "b"])]
        out, _ = overrides.build(ways)
        self.assertNotIn(0, out)
        out, _ = overrides.build([({"name": "Turquoise Street", "highway": "secondary"}, ways[0][1], ["a", "b"])])
        self.assertEqual(out[0][0], 25)

    def test_only_unresolved_pieces_left_unknown(self):
        # What is still 99 in the box has no posted-speed source (README "Unresolved"): freeway ramps, links, Morena Blvd, a 14 m Balboa piece.
        left = {(NAMES[s[0]], s[1]) for s in SEGS if s[2] == 99 and inb(mid(s), PB)}
        allowed = {("", "motorway_link"), ("", "primary_link"), ("", "secondary_link"), ("Morena Boulevard", "secondary"), ("Balboa Avenue", "primary")}
        self.assertLessEqual(left, allowed, left - allowed)
        self.assertLessEqual(sum(1 for s in SEGS if s[2] == 99 and NAMES[s[0]] == "Balboa Avenue" and inb(mid(s), PB)), 1)


if __name__ == "__main__":
    unittest.main()
