"""Street View batch 4 (RG, Oct 22 2026; sheet 1rt3b8LJK-Bo6ItkZ9qaHd2GnfL-zT_5nAigcZV0AB3A, photos in Drive folder
1xb9w8WsXiPPK_KkashiAco3ub_UUR2-M). Same rules as batch 2: a posted sign overrides OSM; no_sign / no_imagery / wrong_road
rows change nothing; agreeing rows keep their speed but now cite the sign (Max, Oct 22 9:13 PM PT: "count the 26
matching signs too"); signs never lift a ban; every changed way cites 'posted sign, Street View check (RG),
photo <file>'. Hawaii rows are not applied (OSM build input missing on the box)."""
import collections, csv, json, math, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, "research", "streetview_batch4")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import importlib.util
_sp = importlib.util.spec_from_file_location("sv4_resolve", os.path.join(H, "resolve.py")); R = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(R)
import streetview_signs as SV
ROWS = list(csv.DictReader(open(os.path.join(H, "results.csv"))))
BY = {r["check_id"]: r for r in ROWS}
SIGNS = json.load(open(os.path.join(H, "signs.json")))
SIGNS2 = json.load(open(os.path.join(ROOT, "research", "streetview_batch2", "signs.json")))
PH = json.load(open(os.path.join(H, "photos.json")))
COR = json.load(open(os.path.join(H, "corridors.json")))
DONE = [r for r in ROWS if r["status"] == "done"]
HAWAII_NOT_APPLIED = {"KAANAPALI-B4-358", "KAANAPALI-B4-378", "WAILEA-B4-375", "WAILEA-B4-377", "WAILEA-B4-409",
                      "KAILUA-B4-130", "KAANAPALI-B4-371", "KAANAPALI-B4-404"}   # last three agree with the map
# The 12 segments the checker reported as flipping out of cart/LSV-legal (posted > 35 mph -> red on the map).
FLIPS_OUT = {"AMELIA-B4-360": 45, "COACHELLA-B4-036": 45, "HHI-B4-048": 45, "LWR-B3-003": 40, "LWR-B4-203": 40,
             "LWR-B4-204": 40, "LWR-B4-275": 40, "MYRTLE-B4-310": 45, "ROCKPORT-B4-383": 60, "SD-B4-125": 40,
             "SD-B4-128": 40, "SUNCITYCENTER-B4-087": 45}
_c = {}
def data(rid):
    if rid not in _c:
        idx = json.load(open(os.path.join(ROOT, "public/data", rid, "index.json")))
        _c[rid] = (idx, [s for t in idx["meta"]["tiles"] for s in json.load(open(os.path.join(ROOT, "public/data", rid, "tiles", t + ".json")))])
    return _c[rid]
def nm(road): return "" if road == "(unnamed)" else road
def at_point(r):
    idx, segs = data(r["region"]); la, lo = map(float, r["gcm_ref"].split("|")[1].split(","))
    def d(s):
        P = [((x - lo) * 93500, (y - la) * 110540) for x, y in s[7]]; best = math.hypot(*P[0])
        for (ax, ay), (bx, by) in zip(P, P[1:]):
            vx, vy = bx - ax, by - ay; t = max(0, min(1, -(ax * vx + ay * vy) / ((vx * vx + vy * vy) or 1))); best = min(best, math.hypot(ax + t * vx, ay + t * vy))
        return best
    return idx, min([s for s in segs if idx["names"][s[0]] == nm(r["road_name"])], key=d)
def corridor_segs(cid):
    """Built segments of a B4 row's checked corridor (node pair + end points + name)."""
    c = COR[cid]; idx, segs = data(c["region"]); out = []
    for a, b, p, q in c["segs"]:
        hit = [x for x in segs if {x[5], x[6]} == {a, b} and idx["names"][x[0]] == nm(c["road"])
               and {tuple(round(v, 5) for v in x[7][0]), tuple(round(v, 5) for v in x[7][-1])} == {tuple(p), tuple(q)}]
        assert hit, (cid, a, b)
        out.append(hit[0])
    return idx, out
APPLIED = sorted({e["check_id"] for v in SIGNS.values() for e in v})

class Batch4(unittest.TestCase):
    def test_sheet_counts(self):
        self.assertEqual(len(ROWS), 448)
        self.assertEqual(collections.Counter(r["status"] for r in ROWS), {"done": 94, "no_sign": 349, "no_imagery": 4, "wrong_road": 1})
        self.assertEqual(collections.Counter(R.kind(r) for r in DONE), {"agree": 26, "correction": 44, "fill": 24})
        self.assertTrue(all(r["checker_initials"] == "RG" for r in DONE))
        self.assertTrue(all(r["posted_speed_seen_mph"] == "" for r in ROWS if r["status"] != "done"))

    def test_one_photo_per_confirmed_sign(self):
        self.assertEqual(set(PH), {r["check_id"] for r in DONE})

    def test_every_confirmed_sign_applied(self):
        want = {r["check_id"] for r in DONE} - HAWAII_NOT_APPLIED
        self.assertEqual(set(APPLIED), want)
        self.assertEqual(len(want), 86)   # 63 corrections/fills + 23 agreeing rows outside Hawaii
        ways = [(rid, e["way"]) for rid, v in SIGNS.items() for e in v]
        self.assertEqual(len(ways), len(set(ways)), "a way claimed by two rows")
        self.assertFalse(set(ways) & {(rid, e["way"]) for rid, v in SIGNS2.items() for e in v}, "batch 4 re-claims a batch-2 way")

    def test_built_data_has_posted_sign_with_cite(self):
        for cid in APPLIED:
            r = BY[cid]; mph = int(float(r["posted_speed_seen_mph"]))
            idx, segs = corridor_segs(cid) if "-B4-" in cid else (lambda i_s: (i_s[0], [i_s[1]]))(at_point(r))
            for s in segs:
                self.assertEqual(s[2], mph, cid)
                self.assertEqual(s[3], "v", cid)
                self.assertEqual(idx["sources"][s[8]][1], f"posted sign, Street View check (RG), photo {cid}.jpg", cid)
                self.assertEqual(idx["sources"][s[8]][0], PH[cid], cid)

    def test_twelve_flips_are_red(self):
        for cid, mph in FLIPS_OUT.items():
            r = BY[cid]; self.assertEqual(R.kind(r), "correction", cid)
            self.assertEqual(int(float(r["posted_speed_seen_mph"])), mph, cid)
            self.assertLessEqual(int(float(r["our_speed_mph"])), 35, f"{cid} was not cart/LSV-legal before")
            s = at_point(r)[1]
            self.assertEqual(s[2], mph, cid); self.assertEqual(s[3], "v", cid)
            self.assertGreater(s[2], 35, f"{cid} should be red (not LSV-legal)")

    def test_no_ban_lifted(self):
        for cid in APPLIED:
            for e in (e for v in SIGNS.values() for e in v if e["check_id"] == cid):
                self.assertNotEqual(e["mph"], 99)
        # signed ways are never the cited-ban stretches the resolver skipped
        unres = json.load(open(os.path.join(H, "unresolved.json")))
        self.assertEqual({u[0] if isinstance(u, list) else u["check_id"] for u in unres}, HAWAII_NOT_APPLIED)

    def test_unsigned_rows_unchanged(self):
        signed = {e["check_id"] for v in SIGNS.values() for e in v}
        for r in ROWS:
            if r["status"] != "done":
                self.assertNotIn(r["check_id"], signed)

    def test_agreeing_rows_keep_their_speed(self):
        agree = [e for v in SIGNS.values() for e in v if e["kind"] == "agree"]
        self.assertEqual(len({e["check_id"] for e in agree}), 23)
        for e in agree:
            self.assertEqual(e["mph"], e["was"], e["check_id"])
            self.assertEqual(int(float(BY[e["check_id"]]["our_speed_mph"])), e["mph"], e["check_id"])

    def test_batches_cannot_disagree(self):
        saved = dict(SV.ALL)
        try:
            SV.ALL["x"] = [{"way": 1, "mph": 25, "check_id": "A"}, {"way": 1, "mph": 40, "check_id": "B"}]
            with self.assertRaises(ValueError): SV.for_region("x")
            SV.ALL["x"] = [{"way": 1, "mph": 25, "check_id": "A"}, {"way": 1, "mph": 25, "check_id": "B"}]
            self.assertEqual(SV.for_region("x")[1]["check_id"], "A")
        finally:
            SV.ALL.clear(); SV.ALL.update(saved)
        for rid in set(SIGNS) | set(SIGNS2): SV.for_region(rid)

if __name__ == "__main__": unittest.main()
