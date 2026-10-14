#!/usr/bin/env python3
"""Before/after accuracy metrics per region. usage: accuracy_audit.py BEFORE_DATA_DIR id ... -> research/accuracy15.json + .md tables"""
import json, sys, os, math
B = sys.argv[1]; IDS = sys.argv[2:]
regs = {r["id"]: r for r in json.load(open("public/data/regions.json"))}
def load(d, rid):
    ix = json.load(open(f"{d}/{rid}/index.json")); segs = []
    for t in ix["meta"]["tiles"]: segs += json.load(open(f"{d}/{rid}/tiles/{t}.json"))
    return ix, segs
def L(pts): return sum(math.hypot((pts[i][1]-pts[i-1][1])*110.5, (pts[i][0]-pts[i-1][0])*111.3*math.cos(math.radians(pts[i][1]))) for i in range(1, len(pts)))
MAJ = ("secondary", "tertiary", "unclassified", "primary", "trunk")
res = {}
for rid in IDS:
    cap = (regs[rid].get("rule") or {}).get("max_posted", 35)
    blk = lambda s: s[3] != "c" and (s[2] is None or s[2] > cap or (len(s) > 9 and s[9] == 1 and s[1].startswith(("motorway", "trunk", "primary"))))
    r = {}
    st = {}
    for tag, d in (("before", B), ("after", "public/data")):
        ix, segs = load(d, rid); kn = tot = 0; key = {}
        for s in segs:
            if s[3] == "c": continue
            l = L(s[7]); tot += l; kn += l * (s[3] != "i")
            key[(ix["names"][s[0]], s[5], s[6])] = (blk(s), s[2])
        st[tag] = (round(100 * kn / max(tot, 1e-9), 1), key, ix, segs)
    kb, ka = st["before"][1], st["after"][1]
    flips = {}
    for k, v in ka.items():
        if k in kb and kb[k][0] != v[0]: flips.setdefault(k[0] or "(unnamed)", [0, 0]); flips[k[0] or "(unnamed)"][0 if v[0] else 1] += 1
    ix, segs = st["after"][2], st["after"][3]; un = {}
    for s in segs:
        if s[3] == "i" and s[1].replace("_link", "") in MAJ and not blk(s):
            nm = ix["names"][s[0]] or "(unnamed " + s[1] + ")"; l = L(s[7]); m = s[7][len(s[7])//2]
            u = un.setdefault(nm, {"km": 0, "hw": s[1], "lat": m[1], "lon": m[0]}); u["km"] += l
            if l > u.get("_l", 0): u.update(lat=m[1], lon=m[0], _l=l)
    unl = sorted(({"name": k, "hw": v["hw"], "km": round(v["km"], 2), "lat": round(v["lat"], 5), "lon": round(v["lon"], 5)} for k, v in un.items()), key=lambda x: -x["km"])
    r = {"known_len_pct_before": st["before"][0], "known_len_pct_after": st["after"][0], "segments_newly_blocked": sum(v[0] for v in flips.values()), "segments_newly_ok": sum(v[1] for v in flips.values()),
         "roads_changed": len(flips), "top_changed": sorted(flips.items(), key=lambda x: -sum(x[1]))[:8], "unresolved_major_count": len(unl), "unresolved_major_km": round(sum(u["km"] for u in unl), 1), "unresolved_major_top": unl[:12], "changes": ix["meta"].get("changes")}
    res[rid] = r; print(rid, r["known_len_pct_before"], "->", r["known_len_pct_after"], "blocked+", r["segments_newly_blocked"], "ok+", r["segments_newly_ok"], "roads", r["roads_changed"], "unres", r["unresolved_major_count"], r["unresolved_major_km"], "km")
json.dump(res, open("research/accuracy15.json", "w"), indent=1)
