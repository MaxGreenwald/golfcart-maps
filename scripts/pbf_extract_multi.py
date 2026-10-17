#!/usr/bin/env python3
"""Clip one Geofabrik .pbf to several region bboxes in a single pass.
usage: pbf_extract_multi.py in.pbf id:S,W,N,E [id:S,W,N,E ...]  -> cache/<id>_osm.json + cache/<id>_osm_pois.json"""
import osmium, json, sys, os
pbf = sys.argv[1]; R = {a.split(":")[0]: tuple(map(float, a.split(":")[1].split(","))) for a in sys.argv[2:]}
HW = set("motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified residential living_street service path cycleway footway track".split())
els = {k: [] for k in R}; pois = {k: [] for k in R}
inb = lambda b, la, lo: b[0] <= la <= b[2] and b[1] <= lo <= b[3]
class H(osmium.SimpleHandler):
    def way(self, w):
        if w.tags.get("highway") not in HW: return
        try: g = [{"lat": n.location.lat, "lon": n.location.lon} for n in w.nodes]
        except osmium.InvalidLocationError: return
        for k, b in R.items():
            if any(inb(b, q["lat"], q["lon"]) for q in g): els[k].append({"type": "way", "id": w.id, "tags": dict(w.tags), "geometry": g})
    def node(self, n):
        t = n.tags
        if not t.get("name"): return
        l = n.location
        for k_, b in R.items():
            if inb(b, l.lat, l.lon):
                k = next((x for x in ("amenity", "shop", "leisure", "tourism", "place") if x in t), None)
                if k: pois[k_].append([t["name"], t[k], round(l.lon, 5), round(l.lat, 5), t.get("addr:street", "")])
H().apply_file(pbf, locations=True, idx="sparse_file_array,/tmp/nodeidx_%d" % os.getpid())
os.remove("/tmp/nodeidx_%d" % os.getpid())
for k in R:
    json.dump({"elements": els[k]}, open(f"cache/{k}_osm.json", "w")); json.dump(pois[k], open(f"cache/{k}_osm_pois.json", "w"))
    print(k, len(els[k]), "ways", len(pois[k]), "pois")
