"""Unit tests for the turn-lane (*_link) inheritance rule. Run: python3 -m unittest discover -s tests"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from build_data_lib import link_inherit, classify

_ids = iter(range(1, 10**6))
def way(hw, nodes, **tags):
    return {"id": next(_ids), "tags": {"highway": hw, **tags}, "nodes": nodes,
            "geometry": [{"lat": 28.9 + i * 3e-4, "lon": -82.0} for i, _ in enumerate(nodes)]}   # ~33 m per step

def net(roads, link_hw="secondary_link", link_nodes=("a", "m", "b"), link_tags=None):
    """One slip lane a-m-b; roads: [(hw, name, maxspeed|None, node)] attached at a or b."""
    wl = [way(link_hw, list(link_nodes), **(link_tags or {}))]
    for k, (hw, nm, ms, at) in enumerate(roads):
        t = {"name": nm}
        if ms: t["maxspeed"] = ms
        wl.append(way(hw, [at, f"x{k}"], **t))
    return wl, {i: classify(w["tags"]) for i, w in enumerate(wl)}

def run(roads, **kw):
    wl, WS = net(roads, **kw); return link_inherit(wl, WS, lambda w: True), WS

class TurnLanes(unittest.TestCase):
    def test_slip_lane_between_35_and_side_street_inherits_35(self):
        r, _ = run([("secondary", "Buena Vista Blvd", "35 mph", "a"), ("residential", "Ternberry Forest Dr", None, "b")])
        self.assertEqual(r["set"], {0: (35, "k")})

    def test_highest_connected_posted_limit(self):
        r, _ = run([("secondary", "A", "30 mph", "a"), ("secondary", "B", "35 mph", "b")])
        self.assertEqual(r["set"][0], (35, "k"))

    def test_stays_red_with_40_plus_road(self):
        r, _ = run([("secondary", "A", "35 mph", "a"), ("secondary", "B", "45 mph", "b")])
        self.assertEqual(r["set"], {}); self.assertIn("40+", r["log"][0]["result"])

    def test_stays_red_with_banned_road(self):
        wl, WS = net([("secondary", "A", "35 mph", "a"), ("primary", "US 441", None, "b")]); WS[2] = (99, "verified")
        self.assertEqual(link_inherit(wl, WS, lambda w: True)["set"], {})

    def test_stays_red_with_unknown_main_road(self):
        r, _ = run([("secondary", "A", "35 mph", "a"), ("primary", "B", None, "b")])
        self.assertEqual(r["set"], {}); self.assertIn("unknown", r["log"][0]["result"])

    def test_needs_a_posted_road(self):
        r, _ = run([("residential", "A", None, "a"), ("residential", "B", None, "b")])
        self.assertEqual(r["set"], {})

    def test_freeway_ramps_never_inherit(self):
        r, _ = run([("primary", "Broadway", "25 mph", "a")], link_hw="motorway_link")
        self.assertEqual(r["groups"], 0)
        r, _ = run([("secondary", "A", "25 mph", "a"), ("motorway_link", "", "25 mph", "b")])
        self.assertEqual(r["set"], {}); self.assertIn("freeway", r["log"][0]["result"])

    def test_tagged_link_untouched(self):
        r, _ = run([("secondary", "A", "35 mph", "a")], link_tags={"maxspeed": "45 mph"})
        self.assertEqual(r["groups"], 0)

    def test_long_link_stays(self):
        r, _ = run([("secondary", "A", "35 mph", "a"), ("secondary", "B", "35 mph", "z")], link_nodes=tuple("a" + "bcdefghijklmnopqrstuvwxy") + ("z",))
        self.assertEqual(r["set"], {}); self.assertIn("too long", r["log"][0]["result"])

    def test_chained_links_are_one_group(self):
        wl = [way("secondary_link", ["a", "m"]), way("secondary_link", ["m", "b"]), way("secondary", ["a", "x"], name="A", maxspeed="35 mph"), way("tertiary", ["b", "y"], name="B")]
        WS = {i: classify(w["tags"]) for i, w in enumerate(wl)}
        r = link_inherit(wl, WS, lambda w: True)
        self.assertEqual((r["groups"], r["set"]), (1, {0: (35, "k"), 1: (35, "k")}))

    def test_roundabout_result_counts_as_posted(self):
        wl, WS = net([("secondary", "", None, "a"), ("residential", "B", None, "b")]); WS[1] = (35, "roundabout")
        self.assertEqual(link_inherit(wl, WS, lambda w: True)["set"], {0: (35, "k")})

if __name__ == "__main__": unittest.main()
