"""Unit tests for the roundabout inheritance rule and the data validators. Run: python3 -m unittest discover -s tests"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from build_data_lib import roundabout_inherit, validate_rings, classify
import validate_data as V

_ids = iter(range(1, 10**6))
def way(hw, nodes, **tags):
    t = {"highway": hw, **tags}
    return {"id": next(_ids), "tags": t, "nodes": nodes, "geometry": [{"lat": 28.0 + i * 1e-4, "lon": -82.0} for i, _ in enumerate(nodes)]}

def ring_net(approaches, ring_tags=None):
    """A ring split into 2 ways (n1-n2-n3, n3-n4-n1); approaches attach at n1..n4. approaches: [(name, hw, maxspeed|None)]."""
    rt = {"junction": "roundabout", **(ring_tags or {})}
    wl = [way("secondary", ["n1", "n2", "n3"], **rt), way("secondary", ["n3", "n4", "n1"], **rt)]
    for k, (nm, hw, ms) in enumerate(approaches):
        tg = {"name": nm}
        if ms: tg["maxspeed"] = ms
        wl.append(way(hw, [f"n{k % 4 + 1}", f"x{k}"], **tg))
    WS = {i: classify(w["tags"]) for i, w in enumerate(wl)}
    return wl, WS

def rule(approaches, **kw):
    wl, WS = ring_net(approaches, **kw)
    return roundabout_inherit(wl, WS, lambda w: True)

class RingRule(unittest.TestCase):
    def test_untagged_ring_between_35_roads_inherits_35(self):
        r = rule([("Buena Vista Blvd", "secondary", "35 mph"), ("Buena Vista Blvd", "secondary", "35 mph"), ("Side St", "residential", None)])
        self.assertEqual(r["set"], {0: (35, "r"), 1: (35, "r")}); self.assertEqual(r["opened"], 1)

    def test_split_ring_counts_as_one(self):
        self.assertEqual(rule([("A", "secondary", "30 mph")])["rings"], 1)

    def test_takes_highest_and_stays_red_with_40_plus_approach(self):
        r = rule([("Fenney Way", "tertiary", "30 mph"), ("Warm Springs Ave", "secondary", "45 mph")])
        self.assertEqual(r["set"][0], (45, "r")); self.assertEqual(r["opened"], 0); self.assertEqual(r["approach_40plus"], 1)

    def test_exactly_40_stays_red(self):
        r = rule([("A", "secondary", "35 mph"), ("B", "secondary", "40 mph")])
        self.assertEqual(r["set"][0][0], 40); self.assertEqual(r["opened"], 0)

    def test_only_assumed_side_streets_stays_unknown(self):
        r = rule([("Main St", "residential", None), ("Elm St", "residential", None)])
        self.assertEqual(r["set"], {}); self.assertEqual(r["kept_unsure"], 1)

    def test_unknown_major_approach_with_other_name_stays_unknown(self):
        self.assertEqual(rule([("Rifle Range Rd", "secondary", "35 mph"), ("Bowman Rd", "secondary", None)])["set"], {})

    def test_unknown_piece_of_same_named_posted_road_is_ok(self):
        self.assertEqual(rule([("Pope Ave", "secondary", "30 mph"), ("Pope Ave", "secondary", None)])["set"][0], (30, "r"))

    def test_banned_99_approach_does_not_leak_99(self):
        wl, WS = ring_net([("Local Rd", "secondary", "35 mph"), ("Canal Rd", "secondary", None)])
        WS[3] = (99, "verified")   # ordinance / state-highway ban
        self.assertEqual(roundabout_inherit(wl, WS, lambda w: True)["set"], {})

    def test_tagged_ring_untouched(self):
        r = rule([("A", "secondary", "45 mph")], ring_tags={"maxspeed": "15 mph"})
        self.assertEqual(r["set"], {}); self.assertEqual(r["unknown"], 0)

    def test_cart_paths_ignored(self):
        wl, WS = ring_net([("Multi-Modal Path", "path", None), ("B", "secondary", "35 mph")])
        WS[2] = (20, "cartpath")
        self.assertEqual(roundabout_inherit(wl, WS, lambda w: True)["set"][0], (35, "r"))

class RingGuard(unittest.TestCase):
    def test_guard_flags_the_villages_bug(self):
        wl, WS = ring_net([("Buena Vista Blvd", "secondary", "35 mph"), ("Side St", "residential", None)])
        rbx = roundabout_inherit(wl, WS, lambda w: True)
        rbx["set"] = {}; rbx["log"][0]["result"] = "unchanged (rule disabled)"   # simulate the old behaviour
        self.assertEqual(len(validate_rings(wl, WS, rbx)[0]), 1)

    def test_guard_quiet_when_rule_works(self):
        wl, WS = ring_net([("Buena Vista Blvd", "secondary", "35 mph")])
        self.assertEqual(validate_rings(wl, WS, roundabout_inherit(wl, WS, lambda w: True)), ([], []))

    def test_guard_only_warns_for_real_unknowns(self):
        wl, WS = ring_net([("A", "secondary", "35 mph"), ("B", "secondary", None)])
        e, w = validate_rings(wl, WS, roundabout_inherit(wl, WS, lambda w: True)); self.assertEqual((len(e), len(w)), (0, 1))

def seg(sp, code, a, b, hw="secondary"): return [0, hw, sp, code, 0, a, b, [[-82.0, 28.0], [-82.0, 28.0001]]]

class TileValidator(unittest.TestCase):
    def test_red_ring_between_posted_35_is_an_island(self):
        segs = [seg(99, "i", 1, 2), seg(99, "i", 2, 1), seg(35, "t", 1, 10), seg(35, "t", 2, 11), seg(25, "i", 1, 12, "residential")]
        self.assertEqual(len(V.red_islands(segs)), 1)

    def test_inherited_ring_is_not_an_island(self):
        segs = [seg(35, "r", 1, 2), seg(35, "r", 2, 1), seg(35, "t", 1, 10), seg(35, "t", 2, 11)]
        self.assertEqual(V.red_islands(segs), [])

    def test_red_next_to_45_is_fine(self):
        self.assertEqual(V.red_islands([seg(99, "i", 1, 2), seg(35, "t", 1, 10), seg(45, "t", 2, 11)]), [])

    def test_ring_code_needs_a_speed(self):
        self.assertEqual(len(V.ring_errors([seg(99, "r", 1, 2), seg(35, "r", 2, 3)])), 1)

if __name__ == "__main__": unittest.main()
