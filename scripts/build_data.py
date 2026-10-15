#!/usr/bin/env python3
"""Fetch drivable roads from OSM Overpass for coastal North San Diego and
classify them for golf cart (<=25 mph) and LSV (<=35 mph) use.
Output: public/data/roads.json (compact) + gzip. Stdlib only."""
import json, re, time, urllib.request, urllib.parse, gzip, os, math, sys
sys.path.insert(0, os.path.dirname(__file__)); import overrides, mapillary_signs
S, W, N, E = 32.53, -117.42, 33.30, -116.95
TILES_LAT, TILES_LON = 6, 3
PREFIX = "v2_tile"
if os.environ.get("LEGACY"):  # original smaller coverage (cache/tile*.json)
    S, W, N, E = 32.70, -117.30, 33.18, -117.10; TILES_LAT, TILES_LON = 4, 2; PREFIX = "tile"
HW = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|service"
EP = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "GolfCartMaps/1.0 (personal project)"
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "data", "sd")
CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")

def fetch(bb, i, depth=0):
    """Fetch one tile; on repeated failure split it into 4 smaller tiles (Overpass is often overloaded)."""
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"{PREFIX}{i}.json")
    if os.path.exists(cp): return json.load(open(cp))
    q = f'[out:json][timeout:180];way["highway"~"^({HW})$"]["service"!~"parking_aisle|driveway|drive-through"]["access"!~"private|no"]({bb[0]},{bb[1]},{bb[2]},{bb[3]});out tags geom;'
    tries = 3 if depth < 2 else 30
    for attempt in range(tries):
        ep = EP[attempt % len(EP)]
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
            d = json.load(urllib.request.urlopen(req, timeout=240))
            json.dump(d, open(cp, "w")); print("ok", i, len(d.get("elements", [])), flush=True); return d
        except Exception as e:
            print("retry", i, ep, e, flush=True); time.sleep(min(90, 10 * (attempt + 1)))
    if depth >= 2: raise SystemExit("Overpass failed")
    s_, w_, n_, e_ = bb; ml, mo = (s_ + n_) / 2, (w_ + e_) / 2; els = {}
    for k, sb in enumerate([(s_, w_, ml, mo), (s_, mo, ml, e_), (ml, w_, n_, mo), (ml, mo, n_, e_)]):
        for el in fetch(sb, f"{i}_{k}", depth + 1).get("elements", []): els[el["id"]] = el
    d = {"elements": list(els.values())}; json.dump(d, open(cp, "w")); return d

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
        if PREFIX == "v2_tile" and b == TILES_LON - 1 and not os.environ.get("EAST"): i += 1; continue  # inland column optional
        d = fetch((S+a*dl, W+b*dn, S+(a+1)*dl, W+(b+1)*dn), i); i += 1
        for el in d.get("elements", []):
            if el["type"] == "way" and "geometry" in el:
                # node identity = exact coordinate (shared OSM nodes have identical coords)
                el["nodes"] = [f'{q["lat"]:.7f},{q["lon"]:.7f}' for q in el["geometry"]]
                ways[el["id"]] = el
        if not os.path.exists(os.path.join(CACHE, f"{PREFIX}{i}.json")) or True: pass
# US-Mexico border: drop any way with geometry south of the border line (Playas de Tijuana etc.)
def border_lat(lon): return 32.5343 + (lon + 117.1235) * 0.0367
for k in [k for k, w in ways.items() if any(q["lat"] < border_lat(q["lon"]) - 0.0002 for q in w["geometry"])]: del ways[k]
# Coastal strip (~8-10 km inland from the shoreline), Oceanside to the border. (lon, lat)
POLY = [(-117.46, 33.27), (-117.30, 33.27), (-117.24, 33.15), (-117.19, 33.05), (-117.15, 32.95), (-117.14, 32.85),
        (-117.12, 32.75), (-117.06, 32.68), (-117.03, 32.60), (-117.03, 32.53), (-117.46, 32.53)]
def inpoly(x, y, P=POLY):
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
for k in [k for k, w in ways.items() if not inpoly(w["geometry"][len(w["geometry"]) // 2]["lon"], w["geometry"][len(w["geometry"]) // 2]["lat"])]: del ways[k]
# Node ids are kept at way endpoints + shared nodes so routing graph stays connected.
cnt = {}
for w in ways.values():
    for n in w["nodes"]: cnt[n] = cnt.get(n, 0) + 1
wl = list(ways.values())
ov, rep = overrides.build([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]], w["nodes"]) for w in wl])
for r in rep: print("override", *r)
mly, mst = mapillary_signs.match([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]]) for w in wl])
print("mapillary", json.dumps(mst))
conf = []
sources = []; sidx = {}
names, out, stats = [], [], {"tagged": 0, "inferred": 0, "unknown": 0, "inferred_high": 0, "verified": 0, "mapillary": 0}
nidx = {}
nids = {}
def nid(k): return nids.setdefault(k, len(nids))
# Short split stubs: OSM often splits one street into several ways; when only some pieces carry a
# posted limit (tag/city list/Mapillary), an untagged 99 "inferred_high" leftover of <=200 m shows as an
# isolated red stub between OK pieces. Inherit the adjoining same-street limit when both ends join <=35
# roads and at least one end continues the same street with a known (tagged/verified/mapillary) <=35 limit.
def _len_m(g): return sum(math.hypot((g[k+1]["lon"]-g[k]["lon"])*93500, (g[k+1]["lat"]-g[k]["lat"])*110540) for k in range(len(g)-1))
_spd = []
for wi, w in enumerate(wl):
    s0, src0 = classify(w["tags"])
    if wi in ov: s0, src0 = ov[wi][0], "verified"
    elif wi in mly and not ((s0 >= 40) != (mly[wi][0] >= 40) and mly[wi][2] < 2): s0, src0 = mly[wi][0], "mapillary"
    _spd.append((s0, src0))
_ends = {}
for wi, w in enumerate(wl):
    for n in (w["nodes"][0], w["nodes"][-1]): _ends.setdefault(n, []).append(wi)
_mid = {}
for wi, w in enumerate(wl):
    for n in w["nodes"]: _mid.setdefault(n, []).append(wi)
STUB = {}
_ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street"}
_CAND = {wi for wi, w in enumerate(wl) if _spd[wi][1] == "inferred_high" and w["tags"].get("name") and _len_m(w["geometry"]) <= 200}
for _pass in range(2):
    _prev = dict(STUB)  # only resolve from the previous pass so a chain of split pieces grows at most one piece per pass
    for wi, w in enumerate(wl):
        s0, src0 = _spd[wi]; nm = w["tags"].get("name")
        if src0 != "inferred_high" or wi in STUB or not nm or _len_m(w["geometry"]) > 200: continue
        ok_ends, known = 0, []
        for n in (w["nodes"][0], w["nodes"][-1]):
            nb = [j for j in _mid.get(n, []) if j != wi and wl[j]["tags"].get("highway", "").replace("_link", "") in _ROADS and (j not in _CAND or j in _prev)]
            same = [j for j in nb if wl[j]["tags"].get("name") == nm]
            pool = same or nb
            sp = [_prev[j][0] if j in _prev else _spd[j][0] for j in pool]
            if not sp or max(sp) > 35: ok_ends = -9; break
            ok_ends += 1
            known += [(_prev[j][0] if j in _prev else _spd[j][0]) for j in same if j in _prev or _spd[j][1] in ("tagged", "verified", "mapillary")]
        if ok_ends == 2 and known: STUB[wi] = (max(known), nm)
print("short stubs inherited", len(STUB))
json.dump([{"way": wl[k]["id"], "road": v[1], "mph": v[0], "m": round(_len_m(wl[k]["geometry"])), "at": [wl[k]["geometry"][0]["lat"], wl[k]["geometry"][0]["lon"]]} for k, v in STUB.items()],
          open(os.path.join(os.path.dirname(__file__), "..", "research", "short_stubs.json"), "w"), indent=1)
for wi, w in enumerate(wl):
    t = w["tags"]; s, src = classify(t); si = -1
    if wi in STUB and _spd[wi][1] == "inferred_high":  # also covers a lone, unapplied Mapillary match
        s, src = STUB[wi][0], "inferred"
        key = ("", f"Short piece of {STUB[wi][1]} with no limit of its own; uses the adjoining {STUB[wi][0]} mph posting")
        if key not in sidx: sidx[key] = len(sources); sources.append(list(key))
        si = sidx[key]
    if wi in ov:
        vmph, ok, url, label = ov[wi]; s, src = vmph, "verified"
        key = (url, label)
        if key not in sidx: sidx[key] = len(sources); sources.append([url, label])
        si = sidx[key]
        if wi in mly and (mly[wi][0] >= 40) != (vmph >= 40):
            conf.append({"road": t.get("name", ""), "way": w["id"], "override_mph": vmph, "mapillary_mph": mly[wi][0], "signs": mly[wi][2], "url": mly[wi][1]})
    elif wi in mly and not ((s >= 40) != (mly[wi][0] >= 40) and mly[wi][2] < 2):  # flipping allowed/forbidden needs 2+ agreeing signs
        osm = s; s, src = mly[wi][0], "mapillary"
        key = (mly[wi][1], f"Mapillary: {mly[wi][2]} posted {s} mph sign(s) detected")
        if key not in sidx: sidx[key] = len(sources); sources.append([key[0], key[1]])
        si = sidx[key]
        if (osm >= 40) != (s >= 40): conf.append({"road": t.get("name", ""), "way": w["id"], "osm_mph": osm, "mapillary_mph": s, "change": "newly forbidden" if s >= 40 else "newly allowed", "url": key[0]})
    stats[src] += 1
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
        out.append([nidx[nm], t["highway"], s, src[0], ow, nid(nodes[sg[0]]), nid(nodes[sg[-1]]), pts] + ([si] if si >= 0 else []))
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "research"), exist_ok=True)
json.dump({"stats": mst, "changes": conf}, open(os.path.join(os.path.dirname(__file__), "..", "research", "mapillary_report.json"), "w"), indent=1)
total = sum(stats.values())
meta = {"bbox": [S, W, N, E], "generated": time.strftime("%Y-%m-%d"), "ways": total, "segments": len(out), "stats": stats, "poly": POLY}
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
idx = json.dumps({"meta": meta, "names": names, "sources": sources}, separators=(",", ":"))
open(os.path.join(OUT, "index.json"), "w").write(idx)
if os.path.exists(os.path.join(OUT, "roads.json")): os.remove(os.path.join(OUT, "roads.json"))
print(json.dumps({k: v for k, v in meta.items() if k != "tiles"}), "tiles", len(tiles), "raw MB", raw/1e6, "gz MB", gz/1e6, "index KB", len(idx)/1e3)
