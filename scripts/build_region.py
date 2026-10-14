#!/usr/bin/env python3
"""Generic region builder (non-San Diego). usage: build_region.py <region_id>
Input: cache/<id>_osm.json (from pbf_extract.py) + optional research/regions/<id>.json (overrides/bans/notes).
Priority: overrides/bans > cart paths (OSM golf_cart tags) > Mapillary (2+ signs to flip) > OSM maxspeed > default.
Output: public/data/<id>/{index.json,pois.json,tiles/*.json}; same segment format as San Diego, plus
src 'c' = cart path, 'd' = OSM-designated golf cart road (golf_cart=yes|designated on a road)."""
import json, os, sys, math, gzip, time, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import mapillary_signs as M
from build_data_lib import mph, simplify, classify
RID = sys.argv[1]
REG = next(r for r in json.load(open(os.path.join(ROOT, "public/data/regions.json"))) if r["id"] == RID)
S, W, N, E = REG["bbox"]
cfgp = os.path.join(ROOT, "research/regions", RID + ".json")
CFG = json.load(open(cfgp)) if os.path.exists(cfgp) else {}
OUT = os.path.join(ROOT, "public/data", RID)
d = json.load(open(os.path.join(ROOT, "cache", RID + "_osm.json")))
CARTV = {"yes", "designated", "permissive"}
ROADS = set("motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified residential living_street service".split())
ways = {}
for el in d["elements"]:
    t = el["tags"]; hw = t.get("highway")
    if t.get("access") in ("private", "no") and t.get("golf_cart") not in CARTV: continue
    if t.get("area") == "yes": continue
    if hw in ROADS:
        if t.get("service") in ("parking_aisle", "driveway", "drive-through") and t.get("golf_cart") not in CARTV: continue
    elif t.get("golf_cart") not in CARTV: continue   # paths only when carts are tagged
    el["nodes"] = [f'{q["lat"]:.7f},{q["lon"]:.7f}' for q in el["geometry"]]; ways[el["id"]] = el
cnt = {}
for w in ways.values():
    for n in w["nodes"]: cnt[n] = cnt.get(n, 0) + 1
wl = list(ways.values())
# ---- Mapillary (signs cached per 0.05 deg tile in ../golfcart-maps/cache/mapillary) ----
mly, mst = {}, {"signs": 0}
try:
    M.ROOT = os.environ.get("MLY_ROOT", "/workspace/golfcart-maps"); M.CACHE = os.path.join(M.ROOT, "cache", "mapillary"); tk = M.token()
    bbs = []; la = S
    while la < N - 1e-9:
        lo = W
        while lo < E - 1e-9: bbs.append((round(la, 4), round(lo, 4), round(min(la + .05, N), 4), round(min(lo + .05, E), 4))); lo += .05
        la += .05
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda b: M.tile(b, tk), bbs))  # cached after first run
    signs = {x["id"]: x for r in res for x in r}
    sl = [{"id": k, "mph": int(v["object_value"].split("-limit-")[1].split("--")[0]), "lon": v["geometry"]["coordinates"][0], "lat": v["geometry"]["coordinates"][1], "dir": v.get("aligned_direction")} for k, v in signs.items()]
    M.load = lambda: sl
    mly, mst = M.match([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]]) for w in wl])
except Exception as e: print("mapillary skipped:", e)
print("mapillary", mst)
import re
BAN = re.compile(CFG["cart_ban_names"]) if CFG.get("cart_ban_names") else None
OV = {o["way"]: o for o in CFG.get("overrides", [])}   # {"way": osm id, "mph": n, "url":..., "label":...}
XING = CFG.get("crossings", []); XN = set()
def near(la, lo, R=40):
    return any(math.hypot((la - x["lat"]) * 110540, (lo - x["lon"]) * 111320 * math.cos(math.radians(la))) < R for x in XING)
# ---- Wildwood golf cart district map (ArcGIS export) -> per-way flag via nearest line within 20 m + boundary ----
WW = {}
if CFG.get("wildwood"):
    wc = CFG["wildwood"]; lines = []
    for f in json.load(open(os.path.join(ROOT, wc["roads"])))["features"]:
        a = f["properties"].get("Approved"); fl = {"PERMITTED": 2, "PROHIBITED": 1}.get(a)
        if not fl or not f.get("geometry"): continue
        gm = f["geometry"]; parts = gm["coordinates"] if gm["type"] == "MultiLineString" else [gm["coordinates"]]
        for pt in parts: lines.append((fl, pt))
    for f in json.load(open(os.path.join(ROOT, wc["state"])))["features"]:
        gm = f.get("geometry") or {}; parts = gm.get("coordinates", []) if gm.get("type") == "MultiLineString" else [gm.get("coordinates", [])]
        for pt in parts: lines.append((1, pt))
    grid = {}
    for li, (fl, pt) in enumerate(lines):
        for k in range(len(pt) - 1):
            for cx in range(int(min(pt[k][0], pt[k+1][0]) * 500), int(max(pt[k][0], pt[k+1][0]) * 500) + 1):
                for cy in range(int(min(pt[k][1], pt[k+1][1]) * 500), int(max(pt[k][1], pt[k+1][1]) * 500) + 1): grid.setdefault((cx, cy), []).append((li, k))
    kx, ky = 111320 * math.cos(math.radians(28.9)), 110540
    def dseg(p, a, b):
        ax, ay, bx, by, px, py = a[0]*kx, a[1]*ky, b[0]*kx, b[1]*ky, p[0]*kx, p[1]*ky
        vx, vy = bx-ax, by-ay; L = vx*vx + vy*vy; u = max(0, min(1, ((px-ax)*vx + (py-ay)*vy) / L)) if L else 0
        return math.hypot(px-ax-u*vx, py-ay-u*vy)
    for wi, w in enumerate(wl):
        if w["tags"]["highway"] not in ROADS: continue
        g = w["geometry"]; votes = {}
        for q in g[:: max(1, len(g) // 5)] + [g[-1]]:
            p = (q["lon"], q["lat"]); best = (21, None)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for li, k in grid.get((int(p[0]*500)+dx, int(p[1]*500)+dy), ()):
                        dd = dseg(p, lines[li][1][k], lines[li][1][k+1])
                        if dd < best[0]: best = (dd, lines[li][0])
            if best[1]: votes[best[1]] = votes.get(best[1], 0) + 1
        n = len(g[:: max(1, len(g) // 5)]) + 1
        if votes:
            fl, v = max(votes.items(), key=lambda x: x[1])
            if v * 2 > n: WW[wi] = fl
    print("wildwood matched ways", len(WW), "permitted", sum(1 for v in WW.values() if v == 2), "prohibited", sum(1 for v in WW.values() if v == 1))
names, out, sources, sidx, nidx, nids = [], [], [], {}, {}, {}
stats = {"tagged": 0, "inferred": 0, "inferred_high": 0, "verified": 0, "mapillary": 0, "cartpath": 0, "designated": 0}
def src_i(url, label):
    if (url, label) not in sidx: sidx[(url, label)] = len(sources); sources.append([url, label])
    return sidx[(url, label)]
for wi, w in enumerate(wl):
    t = w["tags"]; hw = t["highway"]; si = -1
    s, src = classify(t)
    lban = None
    if hw in ROADS:
        mla, mlo = w["geometry"][len(w["geometry"])//2]["lat"], w["geometry"][len(w["geometry"])//2]["lon"]
        for b in CFG.get("bans", []):   # local ordinance / state-highway bans -> blocked for everyone (single rule)
            if not any(re.search(b["names"], t.get(k, "")) for k in ("name", "ref")): continue
            if "south_of" in b and mla >= b["south_of"]: continue
            if "north_of" in b and mla <= b["north_of"]: continue
            if "west_of" in b and mlo >= b["west_of"]: continue
            if "bbox" in b and not (b["bbox"][0] <= mla <= b["bbox"][2] and b["bbox"][1] <= mlo <= b["bbox"][3]): continue
            lban = b; break
    if w["id"] in OV:
        o = OV[w["id"]]; s, src = o["mph"], "verified"; si = src_i(o["url"], o["label"])
    elif lban:
        s, src = 99, "verified"; si = src_i(lban["url"], lban["label"])
    elif hw not in ROADS:
        s, src = mph(t.get("maxspeed")) or 20, "cartpath"
    elif wi in mly and not ((s >= 40) != (mly[wi][0] >= 40) and mly[wi][2] < 2):
        s, src = mly[wi][0], "mapillary"; si = src_i(mly[wi][1], f"Mapillary: {mly[wi][2]} posted {s} mph sign(s) detected")
    if src not in ("verified", "cartpath") and t.get("golf_cart") in ("yes", "designated") and s <= 35: src = "designated"
    stats[src] += 1
    nm = t.get("name") or t.get("ref") or ("Cart path" if src == "cartpath" else "")
    if src == "cartpath" and t.get("tunnel") in ("yes", "culvert"): nm += " (cart tunnel)"
    if src == "cartpath" and t.get("bridge") == "yes": nm += " (cart bridge)"
    if nm not in nidx: nidx[nm] = len(names); names.append(nm)
    g, nodes = w["geometry"], w["nodes"]; segs, cur = [], [0]
    for k in range(1, len(nodes)):
        cur.append(k)
        if cnt[nodes[k]] > 1 and k < len(nodes) - 1: segs.append(cur); cur = [k]
    segs.append(cur)
    nm2 = t.get("name", "") + "|" + t.get("ref", "")
    cflag = 0   # golf-cart flag: 1 banned, 2 designated by ordinance (<=35), 3 designated crossing stretch
    if src != "cartpath":
        if BAN and any(BAN.search(t.get(k, "")) for k in ("name", "ref")) and t.get("golf_cart") not in ("yes", "designated"): cflag = 1
        mlat = g[len(g)//2]["lat"]; mlon = g[len(g)//2]["lon"]
        for bn in CFG.get("cart_ban_north_of", []):
            if any(re.search(bn["names"], t.get(k, "")) for k in ("name", "ref")): cflag = 1 if mlat > bn["lat"] else 2
        ca = CFG.get("cart_allow_names")
        if ca and re.search(ca["names"], t.get("name", "")) and ca["bbox"][0] <= mlat <= ca["bbox"][2] and ca["bbox"][1] <= mlon <= ca["bbox"][3]: cflag = 2
        if wi in WW: cflag = WW[wi]
        if src == "verified" and t.get("golf_cart") in ("yes", "designated") and s <= 30 and cflag != 1: cflag = 2   # verified-speed cart-lane road
        if t.get("golf_cart") == "no": cflag = 1
        if lban: cflag = 1
    code = {"cartpath": "c", "designated": "d"}.get(src, src[0])
    for sg in segs:
        sflag = cflag
        if XING and src != "cartpath" and any(near(g[k]["lat"], g[k]["lon"]) for k in sg) and (cflag == 1 or (s or 99) > 35 or classify(t)[1] == "inferred_high"):
            sflag = 3; stats["crossing_segs"] = stats.get("crossing_segs", 0) + 1
            for k in sg:
                if near(g[k]["lat"], g[k]["lon"]): XN.add(nodes[k])
        stats["cart_banned"] = stats.get("cart_banned", 0) + (sflag == 1); stats["cart_ordinance"] = stats.get("cart_ordinance", 0) + (sflag == 2)
        pts = simplify([[round(g[k]["lon"], 5), round(g[k]["lat"], 5)] for k in sg])
        ow = 1 if t.get("oneway") in ("yes", "1") else (-1 if t.get("oneway") == "-1" else 0)
        if t.get("junction") == "roundabout" and ow == 0: ow = 1
        out.append([nidx[nm], hw, s, code, ow, nids.setdefault(nodes[sg[0]], len(nids)), nids.setdefault(nodes[sg[-1]], len(nids)), pts] + ([si, sflag] if sflag else [si] if si >= 0 else []))
POLY = CFG.get("poly") or [[W, N], [E, N], [E, S], [W, S]]
meta = {"bbox": [S, W, N, E], "generated": time.strftime("%Y-%m-%d"), "ways": len(wl), "segments": len(out), "stats": stats, "poly": POLY, "region": RID, "unverified": CFG.get("unverified", []), "xnodes": sorted(nids[n] for n in XN if n in nids), "crossings": XING}
TS = 0.1; tiles = {}
for sg in out:
    p = sg[7][0]; tiles.setdefault(f"{math.floor(p[0]/TS)}_{math.floor(p[1]/TS)}", []).append(sg)
td = os.path.join(OUT, "tiles"); os.makedirs(td, exist_ok=True)
for f in os.listdir(td): os.remove(os.path.join(td, f))
raw = gz = 0
for k, sg in tiles.items():
    x = json.dumps(sg, separators=(",", ":")); raw += len(x); gz += len(gzip.compress(x.encode())); open(os.path.join(td, k + ".json"), "w").write(x)
meta["tileSize"] = TS; meta["tiles"] = sorted(tiles)
idx = json.dumps({"meta": meta, "names": names, "sources": sources}, separators=(",", ":")); open(os.path.join(OUT, "index.json"), "w").write(idx)
pp = os.path.join(ROOT, "cache", RID + "_osm_pois.json")
pois = json.load(open(pp)) if os.path.exists(pp) else []
pj = json.dumps(pois, separators=(",", ":")); open(os.path.join(OUT, "pois.json"), "w").write(pj)
print(json.dumps(stats), "tiles", len(tiles), "raw MB %.2f gz MB %.2f index KB %.1f (gz %.1f) pois KB %.1f (gz %.1f)" % (raw/1e6, gz/1e6, len(idx)/1e3, len(gzip.compress(idx.encode()))/1e3, len(pj)/1e3, len(gzip.compress(pj.encode()))/1e3))
