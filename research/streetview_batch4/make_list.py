#!/usr/bin/env python3
"""Batch 4: every conflict in research/beta_check_list.json (437 on Oct 22 2026), with the 11 unchecked batch-3 rows on top.
Input: /tmp/bg2_conf.json from `NO_STATUS=1 DUMP_CONF=/tmp/bg2_conf.json python3 research/beta_exit_gap_v2.py`.
Sort: sourced_red first, then longest first. Columns and link math match research/streetview_batch3/make_list.py."""
import json, csv, math, collections, os
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.join(HERE, "..", "..")
NAMES = {x["id"]: x.get("short") or x["name"] for x in json.load(open(os.path.join(REPO, "public/data/regions.json")))}
d = json.load(open("/tmp/bg2_conf.json")); rows = []
for r, cs in d.items():
    for c in cs: c["r"] = r; rows.append(c)
rows.sort(key=lambda c: (c["kind"] != "sourced_red", -c["L"]))
cols = "check_id,city,road_name,from_cross_street,to_cross_street,osm_way_id,our_speed_mph,our_speed_source,osm_speed_mph,street_view_link,map_link,posted_speed_seen_mph,sign_location_note,imagery_date,confidence,status,checker_initials,notes,why_in_batch,length_mi,length_m,region,gcm_ref".split(",")
out = csv.DictWriter(open(os.path.join(HERE, "checks.csv"), "w", newline=""), cols); out.writeheader()
b3 = [x for x in csv.DictReader(open(os.path.join(HERE, "..", "streetview_batch3", "checks.csv"))) if not x["posted_speed_seen_mph"].strip() and not x["status"].strip()]
for x in b3: out.writerow(x)
WHY = {"sourced_red": "CONFLICT (sourced_red): sourced piece posted >35 mph between pieces of the same road posted <=35; confirm the posted sign",
       "neighbour_disagrees": "CONFLICT: our speed differs from a sourced neighbouring piece of the same road; confirm the posted sign"}
miss = []
for i, c in enumerate(rows, 1):
    if not c["segs"] or not any(len(s["g"]) for s in c["segs"]): miss.append(c); continue
    deg = collections.Counter(n for s in c["segs"] for n in (s["a"], s["b"]))
    ends = [n for n, k in deg.items() if k == 1] or list(deg)[:2]
    cross = [", ".join(c["cross"].get(str(n), [])[:2]) or "(see map link)" for n in ends[:2]]
    seg = max(c["segs"], key=lambda s: s["L"]) if len(c["segs"]) < 3 else sorted(c["segs"], key=lambda s: s["L"])[len(c["segs"]) // 2]
    g = seg["g"]; p, q = (g[len(g)//2 - 1], g[len(g)//2]) if len(g) >= 2 else (g[0], g[0])
    if p == q and len(g) >= 2: p, q = g[0], g[1]
    hd = round(math.degrees(math.atan2((q[0]-p[0])*math.cos(math.radians(q[1])), q[1]-p[1]))) % 360
    lat, lon = q[1], q[0]
    osm = sorted({s["osm"] for s in c["segs"] if s["osm"]}); ways = sorted({str(s["way"]) for s in c["segs"] if s["way"]})
    code = collections.Counter(s["code"] for s in c["segs"]).most_common(1)[0][0]
    out.writerow({"check_id": f"{c['r'].upper()}-B4-{i:03d}", "city": NAMES.get(c["r"], c["r"]), "road_name": c["nm"], "from_cross_street": cross[0],
        "to_cross_street": cross[1] if len(cross) > 1 else "(see map link)", "osm_way_id": ";".join(ways[:6]),
        "our_speed_mph": c["mph"] if c["mph"] < 99 else "", "our_speed_source": {"t": "osm", "i": "inferred", "n": "none"}.get(code, code),
        "osm_speed_mph": "/".join(map(str, osm)),
        "street_view_link": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}&heading={hd}",
        "map_link": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}",
        "why_in_batch": WHY[c["kind"]], "length_mi": f"{c['L']:.2f}", "length_m": round(c["L"] * 1609.34), "region": c["r"], "gcm_ref": f"{c['r']}|{lat:.5f},{lon:.5f}"})
print("batch3", len(b3), "conflicts", len(rows) - len(miss), "missing", [(c["r"], c["nm"]) for c in miss])
print(collections.Counter(c["r"] for c in rows if c not in miss))
