"""Street View batch 2 (RG, Oct 2026; sheet 17DNsyKiXKW5OX4LAadynjKaonLoMgmQRpf8Ht8yhYFQ, photos in Drive folder
1wRm6k3TTDc01il3MuZXIhP7p5YhNp1s2). Rules: a posted sign overrides OSM; can't-tell and agreeing rows change nothing;
signs never lift a ban; every changed way cites 'posted sign, Street View check (RG), photo <file>'."""
import collections, csv, json, math, os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, "research", "streetview_batch2")
sys.path.insert(0, H); import resolve as R
ROWS = list(csv.DictReader(open(os.path.join(H, "results.csv"))))
SIGNS = json.load(open(os.path.join(H, "signs.json")))
PH = json.load(open(os.path.join(H, "photos.json")))
DONE = [r for r in ROWS if r["status"] == "done"]
_c = {}
def data(rid):
    if rid not in _c:
        idx = json.load(open(os.path.join(ROOT, "public/data", rid, "index.json")))
        _c[rid] = (idx, [s for t in idx["meta"]["tiles"] for s in json.load(open(os.path.join(ROOT, "public/data", rid, "tiles", t + ".json")))])
    return _c[rid]
def at_point(r):
    idx, segs = data(r["region"]); la, lo = map(float, r["gcm_ref"].split("|")[1].split(","))
    def d(s):
        P = [((x - lo) * 93500, (y - la) * 110540) for x, y in s[7]]; best = math.hypot(*P[0])
        for (ax, ay), (bx, by) in zip(P, P[1:]):
            vx, vy = bx - ax, by - ay; t = max(0, min(1, -(ax * vx + ay * vy) / ((vx * vx + vy * vy) or 1))); best = min(best, math.hypot(ax + t * vx, ay + t * vy))
        return best
    c = [s for s in segs if idx["names"][s[0]] == r["road_name"]]
    return idx, min(c, key=d)

class Batch2(unittest.TestCase):
    def test_sheet_counts(self):
        self.assertEqual(len(ROWS), 1000)
        self.assertEqual(collections.Counter(r["status"] for r in ROWS), {"done": 178, "can't tell": 822})
        self.assertEqual(collections.Counter(R.kind(r) for r in DONE), {"agree": 84, "correction": 50, "fill": 44})
        self.assertEqual(sum("RED ISLAND" in r["why_in_batch"] for r in ROWS), 146)
        self.assertEqual(sum("RED ISLAND" in r["why_in_batch"] for r in DONE), 20)
        self.assertTrue(all(r["checker_initials"] == "RG" for r in ROWS))

    def test_one_photo_per_confirmed_sign(self):
        self.assertEqual(set(PH), {r["check_id"] for r in DONE})

    def test_only_corrections_and_fills_change(self):
        want = {r["check_id"] for r in DONE if R.kind(r) != "agree"} - {"POIPU-B2-001"}   # poipu: OSM build input missing on the box, not applied
        self.assertEqual({e["check_id"] for v in SIGNS.values() for e in v}, want)
        ways = [(rid, e["way"]) for rid, v in SIGNS.items() for e in v]
        self.assertEqual(len(ways), len(set(ways)), "a way claimed by two rows")

    def test_built_data_has_posted_sign_with_cite(self):
        rows = {r["check_id"]: r for r in ROWS}
        for cid in sorted({e["check_id"] for v in SIGNS.values() for e in v}):
            r = rows[cid]; idx, s = at_point(r)
            self.assertEqual(s[2], int(float(r["posted_speed_seen_mph"])), cid)
            self.assertEqual(s[3], "v", cid)
            self.assertEqual(idx["sources"][s[8]][1], f"posted sign, Street View check (RG), photo {cid}.jpg", cid)
            self.assertEqual(idx["sources"][s[8]][0], PH[cid], cid)

    def test_named_flips(self):
        rows = {r["check_id"]: r for r in ROWS}
        for cid, mph in {"SD-B2-064": 35, "OCOAST-B2-002": 35, "CHS-B2-001": 35, "SD-B2-284": 35, "SD-B2-206": 35,
                         "SD-B2-795": 45, "SD-B2-449": 45, "SD-B2-223": 40}.items():
            self.assertEqual(at_point(rows[cid])[1][2], mph, cid)

    def test_cant_tell_rows_unchanged(self):
        signed = {(rid, e["check_id"]) for rid, v in SIGNS.items() for e in v}
        for r in ROWS:
            if r["status"] != "done":
                self.assertNotIn((r["region"], r["check_id"]), signed)

if __name__ == "__main__": unittest.main()
