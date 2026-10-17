#!/usr/bin/env python3
"""Per-region OSM maxspeed coverage (share of drivable road ways with maxspeed, and length-weighted) + build class counts."""
import json, sys, math, os
ROADS = set("motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified residential living_street service".split())
out = {}
for rid in sys.argv[1:]:
    d = json.load(open(f"cache/{rid}_osm.json")); n = t = 0; L = Lt = 0.0; maj = majt = 0
    for e in d["elements"]:
        tg = e["tags"]; hw = tg.get("highway")
        if hw not in ROADS or tg.get("service") in ("parking_aisle", "driveway", "drive-through"): continue
        g = e["geometry"]; l = sum(math.hypot((g[i]["lat"]-g[i-1]["lat"])*110.5, (g[i]["lon"]-g[i-1]["lon"])*111.3*math.cos(math.radians(g[i]["lat"]))) for i in range(1, len(g)))
        has = "maxspeed" in tg; n += 1; t += has; L += l; Lt += l * has
        if hw.replace("_link","") in ("primary","secondary","tertiary","trunk"): maj += 1; majt += has
    ix = json.load(open(f"public/data/{rid}/index.json"))["meta"]
    out[rid] = {"ways": n, "cov_ways_pct": round(100*t/max(n,1),1), "cov_len_pct": round(100*Lt/max(L,1e-9),1), "major_cov_pct": round(100*majt/max(maj,1),1), "km": round(L), "stats": ix["stats"], "segments": ix["segments"]}
    print(rid, json.dumps(out[rid]))
json.dump(out, open("research/expansion15_stats.json", "w"), indent=1)
