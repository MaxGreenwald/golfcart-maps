"""Mapillary posted-speed signs that face traffic on each PB road with 99 pieces (bearing within 35 deg, <=20 m),
listed west->east / south->north with position. Same geometry test as scripts/mapillary_signs.match."""
import json, glob, math, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ROADS = ["Turquoise Street", "Foothill Boulevard", "Beryl Street", "Mission Boulevard", "Garnet Avenue", "Mission Bay Drive",
         "Soledad Mountain Road", "Balboa Avenue", "Morena Boulevard"]
BOX = (32.78, -117.265, 32.83, -117.21)
els = {}
for f in glob.glob(os.path.join(R, "cache", "v2_tile*.json")):
    for e in json.load(open(f)).get("elements", []):
        if e.get("type") == "way" and "geometry" in e and e["tags"].get("name") in ROADS: els[e["id"]] = e
signs = json.load(open(os.path.join(R, "cache/mapillary/signs.json")))
kx, ky = 111320 * math.cos(math.radians(32.9)), 110540
res = {r: [] for r in ROADS}
for s in signs:
    if not (BOX[0] <= s["lat"] <= BOX[2] and BOX[1] <= s["lon"] <= BOX[3]): continue
    best = None
    for w in els.values():
        g = w["geometry"]
        for k in range(len(g)-1):
            ax, ay, bx, by = g[k]["lon"]*kx, g[k]["lat"]*ky, g[k+1]["lon"]*kx, g[k+1]["lat"]*ky
            vx, vy = bx-ax, by-ay; L = vx*vx+vy*vy; px, py = s["lon"]*kx, s["lat"]*ky
            u = max(0, min(1, ((px-ax)*vx+(py-ay)*vy)/L)) if L else 0
            d = math.hypot(px-ax-u*vx, py-ay-u*vy)
            if d > 20: continue
            if s.get("dir") is not None and L:
                brg = math.degrees(math.atan2(vx, vy)) % 180; sd = s["dir"] % 180
                if min(abs(brg-sd), 180-abs(brg-sd)) > 35: continue
            if best is None or d < best[0]: best = (d, w["tags"]["name"], w["id"], w["tags"].get("maxspeed"))
    if best: res[best[1]].append({"mph": s["mph"], "lat": s["lat"], "lon": s["lon"], "id": s["id"], "way": best[2], "way_maxspeed": best[3]})
for r in ROADS:
    res[r].sort(key=lambda x: (x["lon"], x["lat"]))
    print(r); [print("  ", x["mph"], f'{x["lat"]:.5f},{x["lon"]:.5f}', x["id"], "way", x["way"], "osm", x["way_maxspeed"]) for x in res[r]]
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "signs_by_road.json"), "w"), indent=1)
