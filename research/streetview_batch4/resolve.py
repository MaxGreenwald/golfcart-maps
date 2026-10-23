#!/usr/bin/env python3
"""Street View batch 4 (RG, Oct 22 2026): turn the sheet's confirmed posted signs into per-OSM-way sign entries.
Same method as research/streetview_batch2/resolve.py (imported, not copied), with three batch-4 differences:
  - input: results.csv = the Google Sheet 1rt3b8LJK-Bo6ItkZ9qaHd2GnfL-zT_5nAigcZV0AB3A, Checks tab, exported Oct 22 2026
    (columns A-K and S-W are checks.csv as uploaded; L-R are Reginald's answers); photos.json = proof photo name -> Drive
    link, folder 1xb9w8WsXiPPK_KkashiAco3ub_UUR2-M (94 jpgs, one per 'done' row);
  - status is done / no_sign / no_imagery / wrong_road; only 'done' rows carry a posted speed;
  - stretch = how make_list.py cut it: a B4 row covers exactly the built segments of its conflict corridor
    (corridors.json, saved from /tmp/bg2_conf.json = `DUMP_CONF` output of research/beta_exit_gap_v2.py that made checks.csv);
    batch-3 rows (B3) keep the batch-2 rule (connected run of the same road, limit and source code around the sheet point).
    batch 2's same-limit run is not used for B4 rows because it can run past the checked corridor (Morena Blvd: 6.4 km
    run vs the 2.9 km corridor that was looked at);
  - '(unnamed)' rows match the built data's '' name.
Rules (Max): a posted sign is a real source and overrides OSM; rows with no sign change nothing; rows that agree with the
map change nothing; a sign never lifts a ban (a stretch the built data cites as a ban is skipped and listed); regions whose
OSM build input is missing on the box (Hawaii: kaanapali, wailea, kailua) are not applied and listed.
Output: signs.json {region: [{check_id, road, way, mph, was, kind, url, label, stretch_m, sheet_m}]}, unresolved.json.
Usage: resolve.py [DATA_DIR]"""
import csv, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "research", "streetview_batch2"))
import resolve as B2   # noqa: E402  (batch-2 resolver: nearest segment, same-limit run, OSM ways by geometry)
DATA = sys.argv[1] if len(sys.argv) > 1 and __name__ == "__main__" else os.path.join(ROOT, "public", "data")
B2.DATA = DATA
PH = json.load(open(os.path.join(HERE, "photos.json")))
label, kind, L = B2.label, B2.kind, B2.L
UNNAMED = "(unnamed)"
def rows(): return list(csv.DictReader(open(os.path.join(HERE, "results.csv"))))
def has_input(rid):
    return os.path.exists(os.path.join(ROOT, "cache", "v2_tile0.json" if rid == "sd" else rid + "_osm.json"))
COR = json.load(open(os.path.join(HERE, "corridors.json")))
def _segs(rid):
    idx = json.load(open(os.path.join(DATA, rid, "index.json")))
    return idx, [x for t in idx["meta"]["tiles"] for x in json.load(open(os.path.join(DATA, rid, "tiles", t + ".json")))]
def corridor(r):
    """B4 row -> {ways, len_m, was, code} from the corridor's built segments (matched by node pair + end points)."""
    c = COR[r["check_id"]]; rid = r["region"]; idx, segs = _segs(rid); names = idx["names"]
    nm = "" if c["road"] == UNNAMED else c["road"]
    by = collections.defaultdict(list)   # node pair -> segments (a service road can share both nodes with the main road)
    for x in segs: by[frozenset((x[5], x[6]))].append(x)
    ends = lambda x: {tuple(round(v, 5) for v in x[7][0]), tuple(round(v, 5) for v in x[7][-1])}
    got, miss = [], 0
    for a, b, p, q in c["segs"]:
        hit = [x for x in by.get(frozenset((a, b)), []) if names[x[0]] == nm and ends(x) == {tuple(p), tuple(q)}]
        if not hit: miss += 1; continue
        got.append(hit[0])
    if not got: return None, "corridor not found in built data"
    if miss: return None, f"{miss} of {len(c['segs'])} corridor segments changed since the list was made"
    W = B2.ways(rid); way_ids = set()
    for x in got:
        pts = {(round(u, 5), round(v, 5)) for u, v in x[7]}
        hit = [wid for wid, (wn, cs) in W.items() if wn == nm and pts <= cs]
        if not hit: return None, "no OSM way for a corridor segment"
        way_ids.update(hit)
    was = collections.Counter(x[2] for x in got).most_common(1)[0][0]; code = collections.Counter(x[3] for x in got).most_common(1)[0][0]
    return {"ways": sorted(way_ids), "len_m": round(sum(L(x[7]) for x in got)), "was": was, "code": code,
            "banned": [x for x in got if x[2] == 99 and x[3] == "v"]}, ""
def resolve(r):
    if "-B4-" in r["check_id"]:
        res, why = corridor(r)
    else:
        r = dict(r)
        if r["road_name"] == UNNAMED: r["road_name"] = ""
        res, why = B2.resolve(r)
        if res: res["banned"] = [1] if (res["was"] == 99 and res["code"] == "v") else []
    if not res: return None, why
    if res.pop("banned"): return None, "stretch includes a cited ban in the built data (a posted sign never lifts a ban)"
    return res, ""
def build():
    out, probs = collections.defaultdict(list), []
    for r in rows():
        if r["status"] != "done" or kind(r) == "agree": continue
        if not has_input(r["region"]): probs.append((r["check_id"], r["road_name"], "OSM build input missing on the box (cache/%s_osm.json)" % r["region"])); continue
        res, why = resolve(r)
        if not res: probs.append((r["check_id"], r["road_name"], why)); continue
        for w in res["ways"]:
            out[r["region"]].append({"check_id": r["check_id"], "road": r["road_name"], "way": w, "mph": int(float(r["posted_speed_seen_mph"])),
                "was": res["was"], "kind": kind(r), "url": PH[r["check_id"]], "label": label(r["check_id"]), "stretch_m": res["len_m"], "sheet_m": float(r["length_m"] or 0)})
    return out, probs
if __name__ == "__main__":
    out, probs = build()
    json.dump(out, open(os.path.join(HERE, "signs.json"), "w"), indent=1, ensure_ascii=False)
    json.dump([{"check_id": c, "road": n, "why": w} for c, n, w in probs], open(os.path.join(HERE, "unresolved.json"), "w"), indent=1)
    print({k: len(v) for k, v in out.items()}, "rows", len({e["check_id"] for v in out.values() for e in v}), "unresolved:", probs)
