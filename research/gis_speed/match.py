#!/usr/bin/env python3
"""Test-match downloaded GIS speed layers (raw/*.geojson) to our important-road segments. Analysis only.
A segment matches a GIS line when its 25/50/75% points are all within 20 m of that same line.
Reports: agreement with our real sources (v/m), and unsourced important miles the layer would cover."""
import json, glob, math, sys, collections
ROOT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/gcm-sv2apply"
SPEED = {"sumter_roads": "SpeedLimit", "scdot_speed": "Regulatory", "rivco_highways": "SPEED", "ocgis_speed": "Speed_Limit", "fdot_naples": "SPEED", "fdot_villages": "SPEED"}
REG = {"sumter_roads": "villages", "scdot_speed": "myrtle", "rivco_highways": "coachella", "ocgis_speed": "ocoast", "fdot_naples": "naples", "fdot_villages": "villages"}
IMP = {"primary", "secondary", "tertiary"}; MI = 0.621371; C = 0.0005
def xy(p, lat0): return (p[0]*111320*math.cos(math.radians(lat0)), p[1]*110574)
def pseg(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]; L = dx*dx+dy*dy
    t = 0 if L == 0 else max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L)); return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)
def along(g, f):
    d = [0]
    for i in range(1, len(g)): d.append(d[-1] + math.hypot(g[i][0]-g[i-1][0], g[i][1]-g[i-1][1]))
    t = f*d[-1]
    for i in range(1, len(g)):
        if d[i] >= t: k = (t-d[i-1])/max(d[i]-d[i-1], 1e-12); return [g[i-1][0]+k*(g[i][0]-g[i-1][0]), g[i-1][1]+k*(g[i][1]-g[i-1][1])]
    return g[-1]
def km(g): return sum(math.hypot((g[i][1]-g[i-1][1])*110.574, (g[i][0]-g[i-1][0])*111.32*math.cos(math.radians(g[i][1]))) for i in range(1, len(g)))
segcache = {}
def segs(r):
    if r in segcache: return segcache[r]
    out, seen = [], set()
    for f in glob.glob(f"{ROOT}/public/data/{r}/tiles/*.json"):
        for s in json.load(open(f)):
            hw = s[1].replace("_link", "")
            if not (hw in IMP or (hw == "trunk" and s[2] <= 35)): continue
            k = (min(s[5], s[6]), max(s[5], s[6]))
            if k in seen: continue
            seen.add(k); ok = s[3] in ("v", "m") or (s[3] == "d" and len(s) > 8 and s[8] >= 0)
            out.append(dict(g=s[7], mph=s[2], code=s[3], ok=ok, ban=(len(s) > 9 and s[9] == 1) or (s[3] == "v" and s[2] >= 99), L=km(s[7])*MI))
    segcache[r] = out; return out
res = {}
for f in sorted(glob.glob("raw/*.geojson")):
    n = f.split("/")[-1][:-8]
    if n not in SPEED: continue
    r = REG[n]; S = segs(r); lat0 = S[0]["g"][0][1] if S else 30
    grid = collections.defaultdict(list); lines = []
    for ft in json.load(open(f))["features"]:
        v = ft["properties"].get(SPEED[n]); g = ft.get("geometry") or {}
        try: v = int(float(v))
        except (TypeError, ValueError): continue
        if v < 15: continue
        parts = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])] if g.get("type") == "LineString" else []
        for pt in parts:
            P = [xy(p, lat0) for p in pt]; li = len(lines); lines.append((v, P))
            for p in pt: grid[(int(p[0]/C), int(p[1]/C))].append(li)
    ag = [0, 0]; cov = 0.0; covmi_by = collections.Counter(); tot = sum(s["L"] for s in S); src = sum(s["L"] for s in S if s["ok"]); permissive = 0
    for s in S:
        pts = [along(s["g"], q) for q in (0.25, 0.5, 0.75)]; hit = None
        cands = None
        for p in pts:
            near = set()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1): near |= set(grid.get((int(p[0]/C)+dx, int(p[1]/C)+dy), ()))
            P = xy(p, lat0)
            near = {li for li in near if min(pseg(P, a, b) for a, b in zip(lines[li][1], lines[li][1][1:] or lines[li][1])) <= 20}
            cands = near if cands is None else cands & near
        if cands:
            vs = {lines[li][0] for li in cands}; hit = min(vs) if len(vs) == 1 else None
        if hit is None: continue
        if s["code"] in ("v", "m") and s["mph"] < 99 and not s["ban"]: ag[0] += hit == s["mph"]; ag[1] += 1
        if not s["ok"]:
            cov += s["L"]; permissive += (hit <= 35 < s["mph"])
    res[n] = dict(region=r, features=len(lines), agree=ag, gap_mi=cov, region_mi=tot, before=src/tot, after=(src+cov)/tot, more_permissive=permissive)
    print(f"| {n} | {r} | {len(lines):,} | {ag[0]}/{ag[1]} = {100*ag[0]/max(ag[1],1):.0f}% | {cov:,.1f} | {100*src/tot:.1f}% -> {100*(src+cov)/tot:.1f}% | {permissive} |")
json.dump(res, open("match_results.json", "w"), indent=1)
