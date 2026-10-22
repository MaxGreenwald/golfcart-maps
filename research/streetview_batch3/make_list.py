#!/usr/bin/env python3
"""Batch 3 (near-pass regions): the 11 corridors >=0.25 mi that lift pcb/obx/lwr/galveston to 70% of important miles.
Input: /tmp/bg2_dump.json from `DUMP=pcb,obx,lwr,galveston python3 research/beta_exit_gap_v2.py <data root>`.
Columns follow research/streetview_batch2/results.csv (Reginald's sheet)."""
import json, csv, math, collections, os
NAMES = {"pcb": "Panama City Beach", "obx": "Outer Banks", "lwr": "Lakewood Ranch", "galveston": "Galveston"}
d = json.load(open("/tmp/bg2_dump.json")); rows = []
for r in ("pcb", "obx", "lwr", "galveston"):
    for c in d[r]: c["r"] = r; rows.append(c)
rows.sort(key=lambda c: -c["L"])
cols = "check_id,city,road_name,from_cross_street,to_cross_street,osm_way_id,our_speed_mph,our_speed_source,osm_speed_mph,street_view_link,map_link,posted_speed_seen_mph,sign_location_note,imagery_date,confidence,status,checker_initials,notes,why_in_batch,length_mi,length_m,region,gcm_ref".split(",")
out = csv.DictWriter(open(os.path.join(os.path.dirname(__file__), "checks.csv"), "w", newline=""), cols)
out.writeheader()
for i, c in enumerate(rows, 1):
    deg = collections.Counter(n for s in c["segs"] for n in (s["a"], s["b"]))
    ends = [n for n, k in deg.items() if k == 1] or list(deg)[:2]
    cross = [", ".join(c["cross"].get(str(n), [])[:2]) or "(see map link)" for n in ends[:2]]
    seg = max(c["segs"], key=lambda s: s["L"]) if len(c["segs"]) < 3 else sorted(c["segs"], key=lambda s: s["L"])[len(c["segs"]) // 2]
    g = seg["g"]; p, q = g[len(g)//2 - 1] if len(g) > 2 else g[0], g[len(g)//2]
    hd = round(math.degrees(math.atan2((q[0]-p[0])*math.cos(math.radians(q[1])), q[1]-p[1]))) % 360
    lat, lon = q[1], q[0]
    osm = sorted({s["osm"] for s in c["segs"] if s["osm"]}); ways = sorted({str(s["way"]) for s in c["segs"] if s["way"]})
    code = collections.Counter(s["code"] for s in c["segs"]).most_common(1)[0][0]
    out.writerow({"check_id": f"{c['r'].upper()}-B3-{i:03d}", "city": NAMES[c["r"]], "road_name": c["nm"], "from_cross_street": cross[0],
        "to_cross_street": cross[1] if len(cross) > 1 else "(see map link)", "osm_way_id": ";".join(ways[:6]),
        "our_speed_mph": c["mph"] if c["mph"] < 99 else "", "our_speed_source": {"t": "osm", "i": "inferred", "n": "none"}.get(code, code),
        "osm_speed_mph": "/".join(map(str, osm)),
        "street_view_link": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}&heading={hd}",
        "map_link": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}",
        "why_in_batch": f"BETA EXIT: {c['L']:.2f} mi corridor with no real source; one posted-sign photo clears it (longest first, v2 measure)",
        "length_mi": f"{c['L']:.2f}", "length_m": round(c["L"] * 1609.34), "region": c["r"], "gcm_ref": f"{c['r']}|{lat:.5f},{lon:.5f}"})
print(len(rows))
