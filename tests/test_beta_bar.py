"""Beta bar v3 (Max, Oct 22 2026, 2:47 PM ET): >=70% of important miles sourced with cited bans counted, >=50% of non-ban miles,
local-rules check recorded (ordinance or state law); San Diego exempt and never beta.
Overrides: research/beta_overrides.json (Galveston, Max Oct 22 2026 9:40 PM PT: "yes. Galveston is fine")."""
import json, os, subprocess, sys, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REGS = json.load(open(os.path.join(ROOT, "public/data/regions.json")))
ST = json.load(open(os.path.join(ROOT, "research/beta_status.json")))["regions"]
OVR = {k: v for k, v in json.load(open(os.path.join(ROOT, "research/beta_overrides.json"))).items() if not k.startswith("_")}
class BetaBar(unittest.TestCase):
    def test_sd_never_beta(self):
        self.assertFalse(next(r for r in REGS if r["id"] == "sd").get("beta"))
    def test_overrides_are_documented_and_narrow(self):
        # only Galveston, approved by Max in his words; the bar constants are untouched
        self.assertEqual(set(OVR), {"galveston"})
        g = OVR["galveston"]
        self.assertEqual(g["quote"], "yes. Galveston is fine"); self.assertEqual(g["approved_by"], "Max"); self.assertIn("2026-10-22", g["date"])
        self.assertGreaterEqual(g["min_pct_bans_in"], 69.9)
        src = open(os.path.join(ROOT, "research/beta_exit_gap_v2.py")).read()
        self.assertIn("BAR = 0.70", src); self.assertIn("FLOOR = 0.50", src); self.assertIn('EXEMPT = {"sd"}', src)
    def test_galveston_override(self):
        v = ST["galveston"]
        self.assertTrue(v["passes"]); self.assertTrue(v["override"]["applied"]); self.assertFalse(v["exempt"])
        self.assertLess(v["pct_bans_in"], 70); self.assertTrue(v["missing"])   # real gap stays visible
        self.assertFalse(next(r for r in REGS if r["id"] == "galveston").get("beta"))
        for rid, v in ST.items():
            if rid not in OVR: self.assertFalse(v.get("override"), rid)
    def test_every_region_measured(self):
        self.assertEqual(sorted(r["id"] for r in REGS), sorted(ST))
    def test_flags_match_bar(self):
        for r in REGS:
            if r["id"] == "sd": continue
            self.assertEqual(bool(r.get("beta")), not ST[r["id"]]["passes"], r["id"])
    def test_pass_needs_v3_bar(self):
        acc = json.load(open(os.path.join(ROOT, "research/access_sources.json")))
        for rid, v in ST.items():
            if rid == "sd": self.assertTrue(v["passes"] and v["exempt"]); continue
            a = rid in acc["regions"] or rid in acc.get("state_law", {})
            self.assertEqual(v["access_check"], a, rid)
            bar = v["pct_bans_in"] >= 70 and v["pct_nonban"] >= 50 and a
            o = OVR.get(rid)   # Max-approved override: only down to its min_pct_bans_in; floor and access check still required
            ovr = bool(o) and v["pct_bans_in"] >= o["min_pct_bans_in"] and v["pct_nonban"] >= 50 and a
            self.assertEqual(v["passes"], bar or ovr, rid)
            if not bar and v["passes"]: self.assertTrue(v["override"]["applied"], rid)
    def test_v3_floor_blocks_ban_heavy_regions(self):
        # cited bans can lift the headline %, but never past the 50% non-ban floor
        for rid, v in ST.items():
            if rid != "sd" and v["pct_nonban"] < 50: self.assertFalse(v["passes"], rid)
    def test_state_law_entries_record_the_search(self):
        acc = json.load(open(os.path.join(ROOT, "research/access_sources.json")))
        for r, v in acc.get("state_law", {}).items():
            self.assertEqual(v["text"], "state law, no local ordinance found", r); self.assertTrue(v["searched"], r); self.assertTrue(v["law_url"].startswith("http"), r)
        for r, v in acc["regions"].items(): self.assertTrue(v["url"].startswith("http"), r)
    def test_nocatee_has_access_source(self):
        acc = json.load(open(os.path.join(ROOT, "research/access_sources.json")))["regions"]
        self.assertIn("nocatee", acc); self.assertIn("2017-66", acc["nocatee"]["label"])
    def test_bans_scored_apart(self):
        for rid, v in ST.items():
            self.assertIn("ban_mi", v); self.assertLessEqual(v["ban_sourced_mi"], v["ban_mi"] + 0.05, rid)
    def test_30a_grids_defined(self):
        g = json.load(open(os.path.join(ROOT, "research/beta_grids.json")))["regions"]["30a"]
        self.assertEqual(set(g), {"Seaside", "Alys Beach", "Seacrest", "Rosemary Beach"})
    def test_check_list_conflicts_first(self):
        cl = json.load(open(os.path.join(ROOT, "research/beta_check_list.json")))
        for rid, v in cl.items():
            flags = [c["conflict"] for c in v["gap"]]
            self.assertEqual(flags, sorted(flags, reverse=True), rid)
    def test_apply_check_clean(self):
        self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts/apply_beta_bar.py"), "--check"], capture_output=True).returncode, 0)
if __name__ == "__main__": unittest.main()

