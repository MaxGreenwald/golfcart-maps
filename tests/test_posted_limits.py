"""Conservative posted-limit rule (scripts/overrides.py; CVC 22357): a stretch still signed above the LSV cap must not be shown
LSV-legal until its new signs are confirmed, whatever caution, note or override covers it. Data: research/posted_limits.json.
Guard: scripts/check_posted_limits.py. Run: python3 -m unittest discover -s tests"""
import copy, io, json, os, sys, tempfile, unittest
from contextlib import redirect_stdout
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import check_posted_limits as G
import overrides as O
LIM = os.path.join(ROOT, "research", "posted_limits.json")
BLOCKED = {"delmar-cdm-vdlv-bridge": 40, "delmar-jd-gate2-sdd": 45, "delmar-vdlv-cdm-jd": 40}


def run(limits_obj):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(limits_obj, f); p = f.name
    try:
        return G.check(ROOT, p)
    finally:
        os.unlink(p)


class PostedLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lim = json.load(open(LIM))

    def test_repo_passes_guard(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = G.main(["--root", ROOT])
        self.assertEqual(rc, 0, buf.getvalue())

    def test_del_mar_blocked_stretches_declared(self):
        by = {e["id"]: e for e in self.lim["stretches"]}
        for i, mph in BLOCKED.items():
            e = by[i]
            self.assertEqual(e["posted_mph"], mph, i)
            self.assertTrue(e["map_uses_posted"], i)
            self.assertFalse(e["new_signs_confirmed"], i)   # flip only with signs_evidence; then rebuild and drop the BLK line
            self.assertIn("_10202026-3943", e["posted_source"])

    def test_guard_fails_when_a_signed_over_35_stretch_is_shown_legal(self):
        bad = copy.deepcopy(self.lim)
        e = next(x for x in bad["stretches"] if x["id"] == "delmar-cdm-coast-plaza")   # shown 30, LSV-legal
        e["posted_mph"] = 45
        fails, _ = run(bad)
        self.assertTrue(any(f.startswith("delmar-cdm-coast-plaza: signs posted 45") and "shown LSV-legal" in f for f in fails), fails)

    def test_guard_fails_on_an_undeclared_caution(self):
        bad = copy.deepcopy(self.lim)
        bad["stretches"] = [x for x in bad["stretches"] if x["id"] != "sd-lajolla-loring-colima"]
        fails, _ = run(bad)
        self.assertTrue(any("CAU caution 'La Jolla Blvd" in f for f in fails), fails)

    def test_guard_needs_evidence_to_confirm_signs(self):
        bad = copy.deepcopy(self.lim)
        next(x for x in bad["stretches"] if x["id"] == "delmar-vdlv-cdm-jd")["new_signs_confirmed"] = True
        fails, _ = run(bad)
        self.assertTrue(any("delmar-vdlv-cdm-jd: new_signs_confirmed needs signs_evidence" in f for f in fails), fails)

    def test_overrides_build_blocked_stretches_at_posted_and_lift_cleanly(self):
        got = {e["from_to_segment_if_known"].split(":")[0]: e for e in O.INTEL if e.get("source_url") == O.DM_ORD}
        for road, seg, mph_, pid in O._DM:
            if pid not in BLOCKED:
                continue
            e = got[seg]
            self.assertEqual((e["speed_mph"], e["lsv_ok"]), (BLOCKED[pid], False), seg)
            lifted = dict(O.POSTED[pid], new_signs_confirmed=True, signs_evidence="photo")
            l = O.dm_entry(road, seg, mph_, lifted)
            self.assertEqual((l["speed_mph"], l["lsv_ok"]), (mph_, True), seg)
            self.assertNotIn("until new signs are confirmed", l["from_to_segment_if_known"])


if __name__ == "__main__":
    unittest.main()
