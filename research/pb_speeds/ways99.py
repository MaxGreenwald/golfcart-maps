"""Ways the SD build draws as 99/'i' in the PB box, with bearing-aware Mapillary matches (same matcher as the build)
and any old accuracy-sweep entry within 15 m (stale key). Output research/pb_speeds/ways99.json"""
import json, glob, math, os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(R, "scripts")); import mapillary_signs
BOX = (32.785, -117.26, 32.825, -117.215)
els = {}
for f in glob.glob(os.path.join(R, "cache", "v2_tile*.json")):
    for e in json.load(open(f)).get("elements", []):
        if e.get("type") == "way" and "geometry" in e: els[e["id"]] = e
wl = list(els.values())
mly, _ = mapillary_signs.match([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]]) for w in wl])
idx = json.load(open(os.path.join(R, "public/data/sd/index.json"))); N = idx["names"]
b99 = set()
for f in glob.glob(os.path.join(R, "public/data/sd/tiles/*.json")):
    for s in json.load(open(f)):
        if s[2] == 99 and s[3] == "i":
            m = s[7][len(s[7])//2]
            if BOX[0] <= m[1] <= BOX[2] and BOX[1] <= m[0] <= BOX[3]: b99.add((N[s[0]], round(s[7][0][0], 4), round(s[7][0][1], 4)))
sweep = json.load(open(os.path.join(R, "research/accuracy_sweep.json")))["ways"]
sw_pts = []
for k, v in sweep.items():
    nm, a, b = k.split("|"); la, lo = map(float, a.split(",")); sw_pts.append((nm, lo, la, v))
out = []
for wi, w in enumerate(wl):
    g = [[q["lon"], q["lat"]] for q in w["geometry"]]; nm = w["tags"].get("name", "")
    if (nm, round(g[0][0], 4), round(g[0][1], 4)) not in b99: continue
    L = sum(math.hypot((g[k+1][0]-g[k][0])*93500, (g[k+1][1]-g[k][1])*110540) for k in range(len(g)-1))
    sw = [v for (n2, lo, la, v) in sw_pts if n2 == nm and math.hypot((lo-g[0][0])*93500, (la-g[0][1])*110540) < 15]
    out.append({"way": w["id"], "name": nm, "hw": w["tags"]["highway"], "len_m": round(L), "a": g[0], "b": g[-1],
                "mly": mly.get(wi), "old_sweep": sw[0] if sw else None})
out.sort(key=lambda o: (o["name"], o["a"][0]))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ways99.json"), "w"), indent=1)
for o in out: print(f'{o["name"] or o["hw"]:22} {o["way"]:>11} {o["len_m"]:>4}m a={o["a"][1]:.5f},{o["a"][0]:.5f} mly={o["mly"] and (o["mly"][0],o["mly"][2])} sweep={o["old_sweep"] and (o["old_sweep"]["mph"], o["old_sweep"]["label"][:50])}')
print(len(out), "of", len(b99))
