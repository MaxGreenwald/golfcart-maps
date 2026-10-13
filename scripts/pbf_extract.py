#!/usr/bin/env python3
"""Clip a Geofabrik .osm.pbf to a bbox -> Overpass-style JSON (ways with tags+geometry), plus POIs.
Used when Overpass is down. usage: pbf_extract.py in.pbf S W N E out.json"""
import osmium, json, sys
pbf, S, W, N, E, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
HW = set("motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified residential living_street service path cycleway footway track".split())
els, pois = [], []
class H(osmium.SimpleHandler):
    def way(self, w):
        hw = w.tags.get("highway")
        if hw not in HW: return
        try: g = [{"lat": n.location.lat, "lon": n.location.lon} for n in w.nodes]
        except osmium.InvalidLocationError: return
        if not any(S <= q["lat"] <= N and W <= q["lon"] <= E for q in g): return
        els.append({"type": "way", "id": w.id, "tags": dict(w.tags), "geometry": g})
    def node(self, n):
        t = n.tags
        if not t.get("name"): return
        l = n.location
        if not (S <= l.lat <= N and W <= l.lon <= E): return
        k = next((x for x in ("amenity", "shop", "leisure", "tourism", "place") if x in t), None)
        if k: pois.append([t["name"], t[k], round(l.lon, 5), round(l.lat, 5), t.get("addr:street", "")])
H().apply_file(pbf, locations=True, idx="flex_mem")
json.dump({"elements": els}, open(out, "w")); json.dump(pois, open(out.replace(".json", "_pois.json"), "w"))
print(len(els), "ways", len(pois), "pois")
