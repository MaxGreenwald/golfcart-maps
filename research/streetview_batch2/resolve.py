#!/usr/bin/env python3
"""Street View batch 2 (RG, Oct 2026): turn the sheet's confirmed posted signs into per-OSM-way sign entries.
Input: results.csv (the Google Sheet 17DNsyKiXKW5OX4LAadynjKaonLoMgmQRpf8Ht8yhYFQ, Roads tab, exported Oct 22 2026),
photos.json (proof photo name -> Drive link, folder 1wRm6k3TTDc01il3MuZXIhP7p5YhNp1s2), the pre-apply built data
(public/data/<region>, master 1fa5821) and the OSM build inputs (cache/).
Rules (Max): a posted sign is a real source and overrides OSM; can't-tell rows change nothing; rows that agree with the map
change nothing; roads with no posted speed are never marked unconfirmed. Each stretch = the connected run of the same road
with the same limit + source code around the sheet's point (how make_batch2.py cut it).
Output: signs.json {region: [{check_id, road, way, mph, was, kind, url, label}]}. Usage: resolve.py [DATA_DIR]"""
import csv, glob, json, math, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "public", "data")
PH = json.load(open(os.path.join(HERE, "photos.json")))
def label(cid): return f"posted sign, Street View check (RG), photo {cid}.jpg"
def L(p): return sum(math.hypot((p[k+1][0]-p[k][0]) * 111320 * math.cos(math.radians(p[k][1])), (p[k+1][1]-p[k][1]) * 110540) for k in range(len(p)-1))
def kind(r):
    o, p = r["our_speed_mph"], r["posted_speed_seen_mph"]
    return "fill" if o in ("", None) else "agree" if float(o) == float(p) else "correction"
_ways = {}
def ways(rid):
    if rid not in _ways:
        fs = glob.glob(os.path.join(ROOT, "cache", "v2_tile*.json")) if rid == "sd" else [os.path.join(ROOT, "cache", rid + "_osm.json")]
        W = {}
        for f in fs:
            if not os.path.exists(f): continue
            for el in json.load(open(f)).get("elements", []):
                if el.get("type", "way") == "way" and "geometry" in el and el.get("tags", {}).get("highway"):
                    W[el["id"]] = (el["tags"].get("name") or el["tags"].get("ref") or "", {(round(q["lon"], 5), round(q["lat"], 5)) for q in el["geometry"]})
        _ways[rid] = W
    return _ways[rid]
def resolve(r):
    rid = r["region"]; idx = json.load(open(os.path.join(DATA, rid, "index.json"))); names = idx["names"]
    segs = [s for t in idx["meta"]["tiles"] for s in json.load(open(os.path.join(DATA, rid, "tiles", t + ".json")))]
    la, lo = map(float, r["gcm_ref"].split("|")[1].split(","))
    nm = r["road_name"]; cand = [i for i, s in enumerate(segs) if names[s[0]] == nm]
    if not cand: return None, "road not in built data"
    def d(s):   # metres from the sheet point to the segment polyline (the point can sit mid-way along a 2-point segment)
        P = [((x - lo) * 93500, (y - la) * 110540) for x, y in s[7]]
        if len(P) == 1: return math.hypot(*P[0])
        best = 1e18
        for (ax, ay), (bx, by) in zip(P, P[1:]):
            vx, vy = bx - ax, by - ay; t = max(0, min(1, -(ax * vx + ay * vy) / ((vx * vx + vy * vy) or 1)))
            best = min(best, math.hypot(ax + t * vx, ay + t * vy))
        return best
    i0 = min(cand, key=lambda i: d(segs[i]))
    if d(segs[i0]) > 15: return None, f"nearest {nm} is {d(segs[i0]):.0f} m away"
    bynode = collections.defaultdict(list)
    for i in cand:
        for n in (segs[i][5], segs[i][6]): bynode[n].append(i)
    s0 = segs[i0]; comp, st, seen = [], [i0], {i0}
    while st:
        k = st.pop(); comp.append(k)
        for n in (segs[k][5], segs[k][6]):
            for j in bynode[n]:
                if j not in seen and segs[j][2] == s0[2] and segs[j][3] == s0[3]: seen.add(j); st.append(j)
    W = ways(rid); way_ids = set()
    for k in comp:
        pts = {(round(x, 5), round(y, 5)) for x, y in segs[k][7]}
        hit = [wid for wid, (wn, cs) in W.items() if wn == nm and pts <= cs]
        if not hit: return None, f"no OSM way for segment {k}"
        way_ids.update(hit)
    return {"ways": sorted(way_ids), "len_m": round(sum(L(segs[k][7]) for k in comp)), "was": s0[2], "code": s0[3]}, ""
if __name__ == "__main__":
    out, probs = collections.defaultdict(list), []
    for r in csv.DictReader(open(os.path.join(HERE, "results.csv"))):
        if r["status"] != "done" or kind(r) == "agree": continue
        res, why = resolve(r)
        if not res: probs.append((r["check_id"], r["road_name"], why)); continue
        for w in res["ways"]:
            out[r["region"]].append({"check_id": r["check_id"], "road": r["road_name"], "way": w, "mph": int(float(r["posted_speed_seen_mph"])),
                "was": res["was"], "kind": kind(r), "url": PH[r["check_id"]], "label": label(r["check_id"]), "stretch_m": res["len_m"], "sheet_m": float(r["length_m"] or 0)})
    json.dump(out, open(os.path.join(HERE, "signs.json"), "w"), indent=1, ensure_ascii=False)
    print({k: len(v) for k, v in out.items()}, "unresolved:", probs)
