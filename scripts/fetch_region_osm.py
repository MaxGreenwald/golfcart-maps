#!/usr/bin/env python3
"""Fetch one region's roads (and a small POI set) from Overpass into cache/<id>_osm.json.
usage: fetch_region_osm.py <region_id>   (bbox comes from public/data/regions.json)
Skips the download when cache/<id>_osm.json already exists."""
import json, os, sys, time, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EP = ["https://overpass.openstreetmap.fr/api/interpreter", "https://overpass.osm.ch/api/interpreter",
      "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "GolfCartMaps/1.0 (region build)"
HW = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|service|path|cycleway|footway|track"

def fetch(q, timeout=100):
    last = None
    for attempt in range(6):
        ep = EP[attempt % len(EP)]
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e
            print("retry", ep, type(e).__name__, e, flush=True)
            time.sleep(min(60, 8 * (attempt + 1)))
    raise SystemExit("Overpass failed: %s" % last)

def main():
    rid = sys.argv[1]
    os.makedirs(os.path.join(ROOT, "cache"), exist_ok=True)
    out = os.path.join(ROOT, "cache", rid + "_osm.json")
    pois_out = os.path.join(ROOT, "cache", rid + "_osm_pois.json")
    if os.path.exists(out) and os.path.getsize(out) > 100:
        print(rid, "cached", os.path.getsize(out))
        return
    reg = next(r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json"))) if r["id"] == rid)
    s, w, n, e = reg["bbox"]
    bb = f"{s},{w},{n},{e}"
    q = f'[out:json][timeout:180];way["highway"~"^({HW})$"]({bb});out tags geom;'
    d = fetch(q)
    els = [el for el in d.get("elements", []) if el.get("type") == "way" and el.get("geometry")]
    json.dump({"elements": els}, open(out, "w"))
    print(rid, "ways", len(els), flush=True)
    if not os.path.exists(pois_out):
        pq = f'[out:json][timeout:60];node["name"]["place"~"city|town|village|hamlet|suburb"]({bb});out tags;'
        try:
            pd = fetch(pq, timeout=70)
        except (SystemExit, Exception) as e:
            print(rid, "pois skipped", e, flush=True)
            pd = {"elements": []}
        pois = []
        for el in pd.get("elements", []):
            t = el.get("tags") or {}
            if "lat" not in el or "lon" not in el or not t.get("name"): continue
            k = next((x for x in ("amenity", "shop", "leisure", "tourism", "place") if x in t), None)
            if k: pois.append([t["name"], t[k], round(el["lon"], 5), round(el["lat"], 5), t.get("addr:street", "")])
        json.dump(pois, open(pois_out, "w"))
        print(rid, "pois", len(pois), flush=True)

if __name__ == "__main__":
    main()
