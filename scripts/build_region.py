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
if CFG.get("poly"):   # clip ways to region polygon (midpoint + any vertex inside)
    PG = CFG["poly"]
    def _inp(x, y):
        c = False; j = len(PG) - 1
        for i in range(len(PG)):
            xi, yi = PG[i]; xj, yj = PG[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
            j = i
        return c
    ways = {k: w for k, w in ways.items() if any(_inp(q["lon"], q["lat"]) for q in w["geometry"][:: max(1, len(w["geometry"]) // 4)] + [w["geometry"][-1]])}
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
    sl = [{"id": k, "mph": int(v["object_value"].split("-limit-")[1].split("--")[0]), "lon": v["geometry"]["coordinates"][0], "lat": v["geometry"]["coordinates"][1], "dir": v.get("aligned_direction")} for k, v in signs.items() if v.get("geometry") and "-limit-" in v.get("object_value", "")]
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
# ---- State DOT / FHWA posted speed lines (cache/<id>_dot.json from fetch_dot.py) -> per-way speed via >=60% of samples within 12 m ----
DOT = {}; dotp = os.path.join(ROOT, "cache", RID + "_dot.json")
if os.path.exists(dotp) and not CFG.get("no_dot"):
    dl = json.load(open(dotp)); dg = {}
    kx2, ky2 = 111320 * math.cos(math.radians((S + N) / 2)), 110540
    for li, o in enumerate(dl):
        pt = o["coords"]
        for k in range(len(pt) - 1):
            for cx in range(int(min(pt[k][0], pt[k+1][0]) * 1000), int(max(pt[k][0], pt[k+1][0]) * 1000) + 1):
                for cy in range(int(min(pt[k][1], pt[k+1][1]) * 1000), int(max(pt[k][1], pt[k+1][1]) * 1000) + 1): dg.setdefault((cx, cy), []).append((li, k))
    def dseg2(p, a, b):
        ax, ay, bx, by, px, py = a[0]*kx2, a[1]*ky2, b[0]*kx2, b[1]*ky2, p[0]*kx2, p[1]*ky2
        vx, vy = bx-ax, by-ay; L = vx*vx + vy*vy; u = max(0, min(1, ((px-ax)*vx + (py-ay)*vy) / L)) if L else 0
        return math.hypot(px-ax-u*vx, py-ay-u*vy)
    DOTCLS = set("motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link unclassified".split())
    for wi, w in enumerate(wl):
        if w["tags"]["highway"] not in DOTCLS: continue
        g = w["geometry"]; smp = g[:: max(1, len(g) // 8)] + [g[-1]]; votes = {}
        for q in smp:
            p = (q["lon"], q["lat"]); best = (12, None)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for li, k in dg.get((int(p[0]*1000)+dx, int(p[1]*1000)+dy), ()):
                        dd = dseg2(p, dl[li]["coords"][k], dl[li]["coords"][k+1])
                        if dd < best[0]: best = (dd, li)
            if best[1] is not None:
                o = dl[best[1]]; votes.setdefault(o["mph"], []).append(o)
        if votes:
            mph_, vs = max(votes.items(), key=lambda x: (len(x[1]), x[0]))
            if len(vs) >= 0.6 * len(smp): DOT[wi] = vs[0]
    print("dot matched ways", len(DOT))
DES = {}   # wi -> (url,label): ordinance-designated cart streets
def _norm(x): return re.sub(r"[^a-z0-9 ]", "", x.lower().replace("avenue", "ave").replace("street", "st").replace("drive", "dr").replace("boulevard", "blvd").replace("road", "rd").replace("lane", "ln").replace("court", "ct").replace("circle", "cir").replace("west ", "w ").replace("east ", "e ").replace("saint ", "st "))
import difflib
for dsg in CFG.get("designated_names", []):
    nl = [_norm(n) for n in dsg["names"]]; bb = dsg["bbox"]
    for wi, w in enumerate(wl):
        nm_ = w["tags"].get("name")
        if not nm_ or w["tags"]["highway"] not in ROADS: continue
        q = w["geometry"][len(w["geometry"])//2]
        if not (bb[0] <= q["lat"] <= bb[2] and bb[1] <= q["lon"] <= bb[3]): continue
        n0 = _norm(nm_)
        if n0 in nl or (dsg.get("fuzzy") and difflib.get_close_matches(n0, nl, 1, dsg["fuzzy"])): DES[wi] = (dsg["url"], dsg["label"])
print("designated (ordinance list) ways", len(DES))
CONF = []
CHG = {"dot": 0, "dot_block": 0, "dot_open": 0, "desig_only_block": 0}
names, out, sources, sidx, nidx, nids = [], [], [], {}, {}, {}
stats = {"tagged": 0, "inferred": 0, "inferred_high": 0, "verified": 0, "mapillary": 0, "cartpath": 0, "designated": 0}
WS, WOUT = {}, {}   # wi -> final (mph, src); wi -> indices into out
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
    elif wi in DOT and src == "tagged" and DOT[wi]["src"] == "FHWA" and (s > 35) != (DOT[wi]["mph"] > 35):
        g_ = w["geometry"][len(w["geometry"])//2]; CONF.append({"name": t.get("name") or t.get("ref"), "osm_mph": s, "fhwa_mph": DOT[wi]["mph"], "lat": round(g_["lat"], 5), "lon": round(g_["lon"], 5), "way": w["id"]})
    elif wi in DOT and not (wi in mly and mly[wi][2] >= 2):
        o = DOT[wi]; s0 = s; s, src = o["mph"], "verified"; si = src_i(o["url"], o["label"]); CHG["dot"] += 1
        if s0 <= 35 < s: CHG["dot_block"] += 1
        if s0 > 35 >= s: CHG["dot_open"] += 1
    elif hw not in ROADS:
        s, src = mph(t.get("maxspeed")) or 20, "cartpath"
    elif wi in mly and not ((s >= 40) != (mly[wi][0] >= 40) and mly[wi][2] < 2):
        s, src = mly[wi][0], "mapillary"; si = src_i(mly[wi][1], f"Mapillary: {mly[wi][2]} posted {s} mph sign(s) detected")
    if src not in ("verified", "cartpath") and t.get("golf_cart") in ("yes", "designated") and s <= 35: src = "designated"
    if wi in DES and src not in ("cartpath",) and s <= 35 and not lban: src = "designated"; si = src_i(*DES[wi])
    if hw in ROADS and not lban and src not in ("designated", "cartpath") and w["id"] not in OV:
        mq = w["geometry"][len(w["geometry"])//2]
        for z in CFG.get("designated_only_zones", []):
            bb = z["bbox"]
            if bb[0] <= mq["lat"] <= bb[2] and bb[1] <= mq["lon"] <= bb[3]: s, src = 99, "verified"; si = src_i(z["url"], z["label"]); CHG["desig_only_block"] += 1; break
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
    WS[wi] = (s, src); WOUT[wi] = []
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
        WOUT[wi].append(len(out))
        out.append([nidx[nm], hw, s, code, ow, nids.setdefault(nodes[sg[0]], len(nids)), nids.setdefault(nodes[sg[-1]], len(nids)), pts] + ([si, sflag] if sflag else [si] if si >= 0 else []))
# ---- Roundabouts: OSM rarely tags maxspeed on the ring itself, so an untagged major-class ring (secondary etc.)
# fell to 99 "inferred_high" and showed red even when every approach is posted <=35. A ring with no limit of its own
# takes the HIGHEST known limit among its connecting roads (conservative: a ring touching a 40+ road stays red). ----
from build_data_lib import roundabout_inherit
RBX = roundabout_inherit(wl, WS, lambda w: w["tags"]["highway"] in ROADS)
for wi, (nmph, rcode) in RBX["set"].items():
    for i in WOUT[wi]: out[i][2] = nmph; out[i][3] = rcode
stats["roundabout_inherited"] = len(RBX["set"]); CHG["roundabout_rings"] = RBX["rings"]; CHG["roundabout_rings_opened"] = RBX["opened"]
print("roundabouts", {k: v for k, v in RBX.items() if k not in ("set", "log")})
# ---- Short turn/slip lanes (*_link) with no limit: same safe rule (highest connecting limit; stays red near 40+/banned/unknown roads) ----
from build_data_lib import link_inherit
for wi, (nmph, rcode) in RBX["set"].items(): WS[wi] = (nmph, "roundabout")
LKX = link_inherit(wl, WS, lambda w: w["tags"]["highway"] in ROADS)
for wi, (nmph, lcode) in LKX["set"].items():
    WS[wi] = (nmph, "link")
    for i in WOUT[wi]: out[i][2] = nmph; out[i][3] = lcode
stats["link_inherited"] = len(LKX["set"])
print("turn lanes", {k: v for k, v in LKX.items() if k not in ("set", "log")})
if os.environ.get("RB_DEBUG"): json.dump(LKX["log"], open("/tmp/lk_%s.json" % RID, "w"), indent=0)
from build_data_lib import validate_rings
_re, _rw = validate_rings(wl, WS, RBX)
for x in _rw: print("  warn: roundabout left without a limit", x["lat"], x["lon"], x.get("name"), "-", x["result"])
if _re:
    for x in _re: print("  ERROR: roundabout still unknown but all approaches <=35:", x["lat"], x["lon"], x.get("name"))
    if os.environ.get("VALIDATE") != "warn": sys.exit("roundabout validation failed (VALIDATE=warn to override)")
if os.environ.get("RB_DEBUG"): json.dump(RBX["log"], open("/tmp/rb_%s.json" % RID, "w"), indent=0)
POLY = CFG.get("poly") or [[W, N], [E, N], [E, S], [W, S]]
meta = {"bbox": [S, W, N, E], "generated": time.strftime("%Y-%m-%d"), "ways": len(wl), "segments": len(out), "stats": stats, "poly": POLY, "region": RID, "unverified": CFG.get("unverified", []), "changes": CHG, "dot_conflicts": CONF, "xnodes": sorted(nids[n] for n in XN if n in nids), "crossings": XING}
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
# ---- post-build data validation (red islands vs baseline, ring codes); VALIDATE=warn to report only ----
import validate_data as _VD
if _VD.main([RID]) and os.environ.get("VALIDATE") != "warn": sys.exit("data validation failed for " + RID)
