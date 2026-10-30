"""City of San Diego / SANDAG road segments (webmaps.sandiego.gov Planning/PLN_Mobility layer 19 'Roads (Drivable)', field SPEED)
for the PB box, matched to each SD way the build draws as 99/'i' (25/50/75% points within 25 m of the same-named line).
Caveat: SPEED is 20 on most local streets (below CA's 25 prima facie), so it reads as an assigned class speed, not a posted
sign. Used only as a cross-check next to signs, never alone. Output research/pb_speeds/sandag.json"""
import json, glob, math, os, urllib.request, urllib.parse
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
URL = "https://webmaps.sandiego.gov/arcgis/rest/services/Planning/PLN_Mobility/MapServer/19/query"
q = {"where": "1=1", "geometry": "-117.262,32.783,-117.213,32.827", "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
     "spatialRel": "esriSpatialRelIntersects", "outFields": "RD30FULL,SPEED,ROADSEGID", "f": "json", "resultOffset": 0}
feats = []
while True:
    d = json.load(urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(q), timeout=60))
    feats += d["features"]
    if not d.get("exceededTransferLimit"): break
    q["resultOffset"] += len(d["features"])
kx, ky = 111320 * math.cos(math.radians(32.8)), 110540
def dist(p, line):
    best = 1e9
    for k in range(len(line)-1):
        a, b = line[k], line[k+1]; ax, ay, bx, by = a[0]*kx, a[1]*ky, b[0]*kx, b[1]*ky; px, py = p[0]*kx, p[1]*ky
        vx, vy = bx-ax, by-ay; L = vx*vx+vy*vy; u = max(0, min(1, ((px-ax)*vx+(py-ay)*vy)/L)) if L else 0
        best = min(best, math.hypot(px-ax-u*vx, py-ay-u*vy))
    return best
ABBR = {"Street": "ST", "Boulevard": "BLVD", "Avenue": "AVE", "Drive": "DR", "Road": "RD"}
def norm(n): return " ".join(ABBR.get(w, w).upper() for w in n.split())
def at(g, f):
    L = [0]
    for k in range(len(g)-1): L.append(L[-1] + math.hypot((g[k+1][0]-g[k][0])*kx, (g[k+1][1]-g[k][1])*ky))
    t = L[-1]*f
    for k in range(len(g)-1):
        if L[k+1] >= t: u = (t-L[k])/((L[k+1]-L[k]) or 1); return [g[k][0]+u*(g[k+1][0]-g[k][0]), g[k][1]+u*(g[k+1][1]-g[k][1])]
    return g[-1]
els = {}
for f in glob.glob(os.path.join(R, "cache", "v2_tile*.json")):
    for e in json.load(open(f)).get("elements", []):
        if e.get("type") == "way" and "geometry" in e: els[e["id"]] = e
out = {}
for w in els.values():
    nm = w["tags"].get("name"); g = [[q_["lon"], q_["lat"]] for q_ in w["geometry"]]; m = g[len(g)//2]
    if not nm or not (32.785 <= m[1] <= 32.825 and -117.26 <= m[0] <= -117.215): continue
    cand = [f for f in feats if f["attributes"]["RD30FULL"] == norm(nm)]
    hits = []
    for fr in (0.25, 0.5, 0.75):
        p = at(g, fr); bd = min(((dist(p, f["geometry"]["paths"][0]), f["attributes"]["SPEED"]) for f in cand), default=(1e9, None))
        hits.append(bd[1] if bd[0] <= 25 else None)
    if hits.count(hits[1]) == 3 and hits[1] is not None: out[w["id"]] = hits[1]
json.dump({"source": URL.rsplit("/query", 1)[0], "fetched": "2026-10-29", "ways": out}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandag.json"), "w"), indent=0)
print(len(feats), "features;", len(out), "ways matched")
