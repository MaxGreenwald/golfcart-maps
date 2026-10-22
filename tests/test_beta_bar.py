"""Beta bar (Max, 2026-10-22): beta = < 70% of important miles sourced; San Diego never beta."""
import json, os, subprocess, sys, unittest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REGS = json.load(open(os.path.join(ROOT, "public/data/regions.json")))
ST = json.load(open(os.path.join(ROOT, "research/beta_status.json")))["regions"]
class BetaBar(unittest.TestCase):
    def test_sd_never_beta(self):
        self.assertFalse(next(r for r in REGS if r["id"] == "sd").get("beta"))
    def test_every_region_measured(self):
        self.assertEqual(sorted(r["id"] for r in REGS), sorted(ST))
    def test_flags_match_bar(self):
        for r in REGS:
            if r["id"] == "sd": continue
            self.assertEqual(bool(r.get("beta")), not ST[r["id"]]["passes"], r["id"])
    def test_pass_needs_miles_and_access_source(self):
        acc = json.load(open(os.path.join(ROOT, "research/access_sources.json")))["regions"]
        for rid, v in ST.items():
            self.assertEqual(v["passes"], v["sourced_pct"] >= 70 and rid in acc, rid)
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
