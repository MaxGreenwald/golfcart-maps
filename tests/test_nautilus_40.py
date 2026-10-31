"""Nautilus St, La Jolla: posted 40 per Max's manual check (Oct 31 2026, t405u). Every piece is 40, cites that check,
and is not LSV-legal (40 > 35) or golf-cart-legal. Routing and red styling: tests/nautilus_40.mjs, run from here."""
import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, "public", "data", "sd")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import overrides  # noqa: E402

IDX = json.load(open(os.path.join(SD, "index.json")))
NAMES, SOURCES = IDX["names"], IDX["sources"]
SEGS = [s for t in IDX["meta"]["tiles"] for s in json.load(open(os.path.join(SD, "tiles", t + ".json")))]
NAUT = [s for s in SEGS if NAMES[s[0]] == "Nautilus Street"]
SRC = "Max manual check, Oct 31 2026 (t405u)"


class NautilusSt40(unittest.TestCase):
    def test_override_rule(self):
        e = overrides.INTEL[overrides._MAX]
        self.assertEqual((e["speed_mph"], e["lsv_ok"], e["source_url"]), (40, False, SRC))

    def test_whole_la_jolla_length_is_40(self):
        self.assertEqual(len(NAUT), 26)
        lons = [p[0] for s in NAUT for p in s[7]]
        self.assertLess(min(lons), -117.280)   # west end at La Jolla Blvd
        self.assertGreater(max(lons), -117.250)  # east end past La Jolla Mesa Dr
        self.assertEqual({s[2] for s in NAUT}, {40})
        for s in NAUT:
            self.assertEqual(SOURCES[s[8]][0], SRC)

    def test_banned_for_lsv_and_cart(self):
        for s in NAUT: self.assertGreater(s[2], 35)

    def test_build_rule_wins_over_osm_tag(self):
        ways = [({"name": "Nautilus Street", "maxspeed": "25 mph", "highway": "secondary"}, [[-117.27, 32.8327], [-117.268, 32.8317]], ["a", "b"])]
        out, _ = overrides.build(ways)
        self.assertEqual(out[0][:2], (40, False))

    def test_node_red_and_routing(self):
        r = subprocess.run(["node", "--test", os.path.join(ROOT, "tests", "nautilus_40.mjs")], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + "\n" + r.stderr)


if __name__ == "__main__":
    unittest.main()
