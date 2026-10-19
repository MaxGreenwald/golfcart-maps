"""Carlsbad hold (Max, Oct 18 2026): Carlsbad MC 10.44 is one source. A road OSM marks 40+, or an untagged major road,
may not turn LSV-legal on the ordinance alone; it stays blocked until a second source agrees (2+ Mapillary posted
<=35 signs or another official list). scripts/build_data.py writes research/sd_flip_hold.json with each held way's
final speed and source (and asserts the same at build time)."""
import json, os, unittest
R = os.path.join(os.path.dirname(__file__), "..")

class CarlsbadHold(unittest.TestCase):
    def test_held_ways_not_legal_on_ordinance_alone(self):
        with open(os.path.join(R, "research", "sd_flip_hold.json")) as f: hold = json.load(f)
        self.assertGreaterEqual(len(hold), 21, "hold list shrank: an ordinance-only flip may have been released")
        bad = [(h["road"], h["way"]) for h in hold if h["final_mph"] <= 35 and ("MC 10.44" in h["final_source"] or h["final_source"] == h["source"])]
        self.assertEqual(bad, [])

if __name__ == "__main__":
    unittest.main()
