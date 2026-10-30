"""Every built 99/'i' segment in the PB box -> OSM way, SANDAG SPEED and facing-traffic Mapillary signs on the same road nearby."""
import json, glob, math, os
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "..", "..")
BOX = (32.785, -117.26, 32.825, -117.215)
idx = json.load(open(os.path.join(R, "public/data/sd/index.json"))); N = idx["names"]
els = {}
for f in glob.glob(os.path.join(R, "cache", "v2_tile*.json")):
    for e in json.load(open(f)).get("elements", []):
        if e.get("type") == "way" and "geometry" in e: els[e["id"]] = e
vidx = {}
for w in els.values():
    for q in w["geometry"]: vidx.setdefault((round(q["lon"], 5), round(q["lat"], 5)), set()).add(w["id"])
sg = json.load(open(os.path.join(H, "sandag.json")))["ways"]
sbr = json.load(open(os.path.join(H, "signs_by_road.json")))
rows = {}
for f in glob.glob(os.path.join(R, "public/data/sd/tiles/*.json")):
    for s in json.load(open(f)):
        if s[2] != 99 or s[3] != "i": continue
        g = s[7]; m = g[len(g)//2]
        if not (BOX[0] <= m[1] <= BOX[2] and BOX[1] <= m[0] <= BOX[3]): continue
        nm = N[s[0]]
        ids = None
        for p in g:
            c = {i for i in vidx.get((round(p[0], 5), round(p[1], 5)), ()) if els[i]["tags"].get("name", "") == nm}
            ids = c if ids is None else (ids & c or ids)
        wid = min(ids) if ids else None
        L = sum(math.hypot((g[k+1][0]-g[k][0])*93500, (g[k+1][1]-g[k][1])*110540) for k in range(len(g)-1))
        r = rows.setdefault((nm, s[1], wid), {"name": nm, "hw": s[1], "way": wid, "m": 0, "lat": m[1], "lon": m[0], "segs": 0})
        r["m"] += round(L); r["segs"] += 1
for r in rows.values():
    r["sandag"] = sg.get(str(r["way"])) if r["way"] else None
    near = [x for x in sbr.get(r["name"], []) if math.hypot((x["lon"]-r["lon"])*93500, (x["lat"]-r["lat"])*110540) < 400]
    r["signs400m"] = sorted(x["mph"] for x in near)
out = sorted(rows.values(), key=lambda r: (r["name"], r["lat"]))
json.dump(out, open(os.path.join(H, "table.json"), "w"), indent=1)
for r in out: print(f'{r["name"] or r["hw"]:22} way={r["way"]} segs={r["segs"]} {r["m"]}m @{r["lat"]:.5f},{r["lon"]:.5f} sandag={r["sandag"]} signs<=400m={r["signs400m"]}')
print(sum(r["segs"] for r in out), "segments")
