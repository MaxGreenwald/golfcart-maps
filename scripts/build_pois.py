#!/usr/bin/env python3
"""Fetch named places (beaches, parks, stations, food, shops, landmarks) for instant local search."""
import json, os, time, urllib.request, urllib.parse
S, W, N, E = 32.53, -117.42, 33.30, -116.95
EP = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
bb = f"{S},{W},{N},{E}"
q = f"""[out:json][timeout:240];(
nwr["natural"="beach"]["name"]({bb});nwr["leisure"~"park|golf_course|marina"]["name"]({bb});
nwr["tourism"~"attraction|viewpoint|museum|hotel|zoo|aquarium"]["name"]({bb});
nwr["railway"="station"]["name"]({bb});nwr["public_transport"="station"]["name"]({bb});
nwr["amenity"~"restaurant|cafe|bar|pub|ice_cream|school|college|university|hospital|library|marketplace|cinema|theatre|fuel|pharmacy"]["name"]({bb});
nwr["shop"~"supermarket|convenience|mall|department_store"]["name"]({bb});
nwr["place"~"suburb|neighbourhood|town|city|village"]["name"]({bb}););out tags center;"""
for i in range(6):
    try:
        req = urllib.request.Request(EP[i % len(EP)], data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "GolfCartMaps/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=300)); break
    except Exception as e: print("retry", e); time.sleep(10)
else: raise SystemExit("failed")
out = []
for el in d["elements"]:
    t = el["tags"]; c = el.get("center") or el
    if "lat" not in c: continue
    kind = t.get("natural") or t.get("leisure") or t.get("tourism") or t.get("amenity") or t.get("shop") or t.get("place") or ("station" if t.get("railway") or t.get("public_transport") else "")
    out.append([t["name"], kind, round(c["lon"], 5), round(c["lat"], 5), t.get("addr:city", "")])
p = os.path.join(os.path.dirname(__file__), "..", "public", "data", "sd", "pois.json")
json.dump(out, open(p, "w"), separators=(",", ":"), ensure_ascii=False)
print(len(out), "pois", os.path.getsize(p) / 1e3, "KB")
