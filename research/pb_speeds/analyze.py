"""PB unknown-speed audit (Oct 29 2026): every SD way built as 99/'i' in 32.785-32.825, -117.26..-117.215.
Lists each way (name|first|last node key), nearby Mapillary speed signs (<=25 m, cache/mapillary/signs.json)
and current OSM maxspeed via Overpass. Output: research/pb_speeds/ways.json"""
import json, glob, math, os, sys, re, urllib.request, urllib.parse
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
BOX = (32.785, -117.26, 32.825, -117.215)
els = {}
for f in glob.glob(os.path.join(R, "cache", "v2_tile*.json")):
    for e in json.load(open(f)).get("elements", []):
        if e.get("type") == "way" and "geometry" in e:
            e["nodes"] = [f'{q["lat"]:.7f},{q["lon"]:.7f}' for q in e["geometry"]]; els[e["id"]] = e
idx = json.load(open(os.path.join(R, "public/data/sd/index.json"))); N = idx["names"]
built = set()
for f in glob.glob(os.path.join(R, "public/data/sd/tiles/*.json")):
    for s in json.load(open(f)):
        if s[2] == 99: built.add((N[s[0]], tuple(s[7][0])))
signs = json.load(open(os.path.join(R, "cache/mapillary/signs.json")))
def dm(a, b): return math.hypot((a[0]-b[0])*93500, (a[1]-b[1])*110540)
def segd(p, a, b):
    vx, vy = (b[0]-a[0])*93500, (b[1]-a[1])*110540; wx, wy = (p[0]-a[0])*93500, (p[1]-a[1])*110540
    L = vx*vx+vy*vy; t = max(0, min(1, (wx*vx+wy*vy)/L)) if L else 0
    return math.hypot(wx-t*vx, wy-t*vy)
out = []
for w in els.values():
    g = [[q["lon"], q["lat"]] for q in w["geometry"]]; m = g[len(g)//2]; t = w["tags"]
    if not (BOX[0] <= m[1] <= BOX[2] and BOX[1] <= m[0] <= BOX[3]): continue
    nm = t.get("name", "")
    if not re.match(r"(primary|secondary|tertiary|motorway_link|primary_link|secondary_link)", t.get("highway", "")): continue
    if "maxspeed" in t: continue
    near = [s for s in signs if min(segd([s["lon"], s["lat"]], g[k], g[k+1]) for k in range(len(g)-1)) <= 25]
    out.append({"id": w["id"], "name": nm, "hw": t["highway"], "key": f'{nm}|{w["nodes"][0]}|{w["nodes"][-1]}',
                "a": g[0], "b": g[-1], "len_m": round(sum(dm(g[k], g[k+1]) for k in range(len(g)-1))),
                "signs": [(s["mph"], s["id"], s["lat"], s["lon"]) for s in near]})
ids = ",".join(str(o["id"]) for o in out)
q = f'[out:json][timeout:60];way(id:{ids});out tags;'
cur = {}
for ep in ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]:
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "GolfCartMaps/1.0"}), timeout=90))
        cur = {e["id"]: e.get("tags", {}) for e in d["elements"]}; break
    except Exception as e: print("overpass", ep, e, file=sys.stderr)
for o in out:
    tg = cur.get(o["id"], {}); o["osm_now"] = {k: v for k, v in tg.items() if "maxspeed" in k}; o["osm_live"] = o["id"] in cur
out.sort(key=lambda o: (o["name"], o["a"][1]))
json.dump(out, open(os.path.join(os.path.dirname(__file__), "ways.json"), "w"), indent=1)
for o in out: print(o["name"] or o["hw"], o["id"], o["len_m"], "m", o["osm_now"], [s[0] for s in o["signs"]])
