#!/usr/bin/env python3
"""Fetch drivable roads from OSM Overpass for coastal North San Diego and
classify them for golf cart (<=25 mph) and LSV (<=35 mph) use.
Output: public/data/roads.json (compact) + gzip. Stdlib only."""
import json, re, time, urllib.request, urllib.parse, gzip, os, math
S, W, N, E = 32.53, -117.42, 33.30, -116.95
TILES_LAT, TILES_LON = 6, 3
HW = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|service"
EP = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "GolfCartMaps/1.0 (personal project)"
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "data")
CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")

def fetch(bb, i):
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"v2_tile{i}.json")
    if os.path.exists(cp): return json.load(open(cp))
    q = f'[out:json][timeout:180];way["highway"~"^({HW})$"]["service"!~"parking_aisle|driveway|drive-through"]["access"!~"private|no"]({bb[0]},{bb[1]},{bb[2]},{bb[3]});out tags geom;'
    for attempt in range(6):
        ep = EP[attempt % len(EP)]
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
            d = json.load(urllib.request.urlopen(req, timeout=240))
            json.dump(d, open(cp, "w")); return d
        except Exception as e:
            print("retry", i, ep, e); time.sleep(10 * (attempt + 1))
    raise SystemExit("Overpass failed")

def mph(v):
    if not v: return None
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(mph|km/h|kmh)?", v)
    if not m: return None
    x = float(m.group(1))
    return round(x if (m.group(2) == "mph" or not m.group(2)) else x / 1.609)
# NB: in the US, OSM maxspeed is normally "25 mph"; bare numbers are treated as mph here.

def classify(t):
    hw = t.get("highway", "").replace("_link", "")
    s = mph(t.get("maxspeed"))
    if s is not None: return s, "tagged"
    if hw in ("residential", "living_street", "service", "unclassified", "tertiary"): return 25, "inferred"
    return 99, "inferred_high"

def simplify(pts, tol=0.00004):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]; dx, dy = b[0]-a[0], b[1]-a[1]
        L = dx*dx + dy*dy
        d = abs(dy*(p[0]-a[0]) - dx*(p[1]-a[1])) / math.sqrt(L) if L else math.hypot(p[0]-a[0], p[1]-a[1])
        if d > dmax: dmax, idx = d, i
    if dmax > tol: return simplify(pts[:idx+1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]

ways = {}
dl, dn = (N-S)/TILES_LAT, (E-W)/TILES_LON; i = 0
for a in range(TILES_LAT):
    for b in range(TILES_LON):
        d = fetch((S+a*dl, W+b*dn, S+(a+1)*dl, W+(b+1)*dn), i); i += 1
        for el in d.get("elements", []):
            if el["type"] == "way" and "geometry" in el:
                # node identity = exact coordinate (shared OSM nodes have identical coords)
                el["nodes"] = [f'{q["lat"]:.7f},{q["lon"]:.7f}' for q in el["geometry"]]
                ways[el["id"]] = el
        time.sleep(2)
# Node ids are kept at way endpoints + shared nodes so routing graph stays connected.
cnt = {}
for w in ways.values():
    for n in w["nodes"]: cnt[n] = cnt.get(n, 0) + 1
names, out, stats = [], [], {"tagged": 0, "inferred": 0, "unknown": 0, "inferred_high": 0}
nidx = {}
nids = {}
def nid(k): return nids.setdefault(k, len(nids))
for w in ways.values():
    t = w["tags"]; s, src = classify(t); stats[src] += 1
    nm = t.get("name") or t.get("ref") or ""
    if nm not in nidx: nidx[nm] = len(names); names.append(nm)
    g = w["geometry"]; nodes = w["nodes"]
    # split at junction nodes so graph edges are correct; simplify each segment
    segs, cur = [], [0]
    for k in range(1, len(nodes)):
        cur.append(k)
        if cnt[nodes[k]] > 1 and k < len(nodes) - 1: segs.append(cur); cur = [k]
    segs.append(cur)
    for sg in segs:
        pts = simplify([[round(g[k]["lon"], 5), round(g[k]["lat"], 5)] for k in sg])
        ow = 1 if t.get("oneway") in ("yes", "1") else (-1 if t.get("oneway") == "-1" else 0)
        if t.get("junction") == "roundabout" and ow == 0: ow = 1
        out.append([nidx[nm], t["highway"], s, src[0], ow, nid(nodes[sg[0]]), nid(nodes[sg[-1]]), pts])
total = sum(stats.values())
meta = {"bbox": [S, W, N, E], "generated": time.strftime("%Y-%m-%d"), "ways": total, "segments": len(out), "stats": stats}
os.makedirs(OUT, exist_ok=True)
TS = 0.1  # output tile size (degrees); segment goes to tile of its first point
tiles = {}
for sg in out:
    p = sg[7][0]; k = f"{math.floor(p[0]/TS)}_{math.floor(p[1]/TS)}"
    tiles.setdefault(k, []).append(sg)
td = os.path.join(OUT, "tiles"); os.makedirs(td, exist_ok=True)
for f in os.listdir(td): os.remove(os.path.join(td, f))
raw = gz = 0
for k, segs in tiles.items():
    d = json.dumps(segs, separators=(",", ":")); raw += len(d); gz += len(gzip.compress(d.encode()))
    open(os.path.join(td, k + ".json"), "w").write(d)
meta["tileSize"] = TS; meta["tiles"] = sorted(tiles)
idx = json.dumps({"meta": meta, "names": names}, separators=(",", ":"))
open(os.path.join(OUT, "index.json"), "w").write(idx)
if os.path.exists(os.path.join(OUT, "roads.json")): os.remove(os.path.join(OUT, "roads.json"))
print(json.dumps({k: v for k, v in meta.items() if k != "tiles"}), "tiles", len(tiles), "raw MB", raw/1e6, "gz MB", gz/1e6, "index KB", len(idx)/1e3)
