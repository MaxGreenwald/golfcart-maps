#!/usr/bin/env python3
"""Mapillary speed-limit sign detections -> per-road posted speeds.
fetch(): tiles the coastal coverage area, queries Graph API map_features (bbox +
regulatory--maximum-speed-limit-* values), caches raw tile responses in cache/mapillary/.
match(ways): nearest road within ~20 m (bearing-aware), returns derived speed facts only."""
import json, os, math, time, urllib.request, urllib.parse, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
CACHE = os.path.join(ROOT, "cache", "mapillary")
S, W, N, E = 32.53, -117.42, 33.30, -117.107   # coastal strip (same as build without EAST column)
STEP = 0.05
VALUES = [f"regulatory--maximum-speed-limit-{v}--g{g}" for v in range(5, 70, 5) for g in range(1, 5)]
def token():
    t = os.environ.get("MAPILLARY_TOKEN")
    if t: return t
    for l in open(os.path.join(ROOT, ".env")):
        if l.startswith("MAPILLARY_TOKEN="): return l.split("=", 1)[1].strip()
def _get(bb, tk):
    q = urllib.parse.urlencode({"access_token": tk, "fields": "id,object_value,geometry,aligned_direction",
        "bbox": f"{bb[1]},{bb[0]},{bb[3]},{bb[2]}", "object_values": ",".join(VALUES), "limit": 2000})
    for a in range(6):
        try: return json.load(urllib.request.urlopen("https://graph.mapillary.com/map_features?" + q, timeout=120)).get("data", [])
        except Exception as e:
            print("retry", bb, e, flush=True); time.sleep(5 * (a + 1))
    raise RuntimeError(f"failed {bb}")
def tile(bb, tk, depth=0):
    cp = os.path.join(CACHE, "t_%.4f_%.4f_%.4f_%.4f.json" % bb)
    if os.path.exists(cp): return json.load(open(cp))
    d = _get(bb, tk)
    if len(d) >= 2000 and depth < 4:   # truncated: split
        s, w, n, e = bb; m1, m2 = (s+n)/2, (w+e)/2; d = []
        for sb in [(s,w,m1,m2),(s,m2,m1,e),(m1,w,n,m2),(m1,m2,n,e)]: d += tile(sb, tk, depth+1)
    json.dump(d, open(cp, "w")); time.sleep(0.2); return d
def fetch():
    os.makedirs(CACHE, exist_ok=True); tk = token(); bbs = []
    la = S
    while la < N - 1e-9:
        lo = W
        while lo < E - 1e-9: bbs.append((round(la,4), round(lo,4), round(min(la+STEP,N),4), round(min(lo+STEP,E),4))); lo += STEP
        la += STEP
    sys.path.insert(0, HERE)
    POLY = [(-117.46, 33.27), (-117.30, 33.27), (-117.24, 33.15), (-117.19, 33.05), (-117.15, 32.95), (-117.14, 32.85), (-117.12, 32.75), (-117.06, 32.68), (-117.03, 32.60), (-117.03, 32.53), (-117.46, 32.53)]
    def east(lat):  # inland edge lon at a latitude
        for (x1, y1), (x2, y2) in zip(POLY[1:-2], POLY[2:-1]):
            if y2 <= lat <= y1: return x1 + (x2 - x1) * (lat - y1) / (y2 - y1)
        return -117.03
    bbs = [b for b in bbs if b[1] < max(east(b[0]), east(b[2])) and b[2] <= 33.28]
    print(len(bbs), "tiles", flush=True)
    with ThreadPoolExecutor(4) as ex: res = list(ex.map(lambda b: tile(b, tk), bbs))
    signs = {x["id"]: x for r in res for x in r}
    out = [{"id": k, "mph": int(v["object_value"].split("-limit-")[1].split("--")[0]),
            "lon": v["geometry"]["coordinates"][0], "lat": v["geometry"]["coordinates"][1],
            "dir": v.get("aligned_direction")} for k, v in signs.items()]
    json.dump(out, open(os.path.join(CACHE, "signs.json"), "w")); return out
def load():
    p = os.path.join(CACHE, "signs.json")
    if not os.path.exists(p) and os.environ.get("MLY_SKIP"): return []
    return json.load(open(p)) if os.path.exists(p) else fetch()
def match(ways, maxd=20.0):
    """ways: list of (tags, coords[[lon,lat]]). Returns ({way_index: (mph, url, nsigns)}, stats)."""
    signs = load(); kx = 111320 * math.cos(math.radians(32.9)); ky = 110540
    grid = {}
    for wi, (t, g) in enumerate(ways):
        if t.get("highway", "").startswith("service"): continue
        for k in range(len(g) - 1):
            a, b = g[k], g[k+1]
            for cx in range(int(min(a[0],b[0])*500)-0, int(max(a[0],b[0])*500)+1):
                for cy in range(int(min(a[1],b[1])*500), int(max(a[1],b[1])*500)+1):
                    grid.setdefault((cx, cy), []).append((wi, k))
    per = {}; matched = 0
    for s in signs:
        best = None; px, py = s["lon"]*kx, s["lat"]*ky
        cands = set()
        for dx in (-1,0,1):
            for dy in (-1,0,1): cands.update(grid.get((int(s["lon"]*500)+dx, int(s["lat"]*500)+dy), ()))
        for wi, k in cands:
            a, b = ways[wi][1][k], ways[wi][1][k+1]
            ax, ay, bx, by = a[0]*kx, a[1]*ky, b[0]*kx, b[1]*ky
            vx, vy = bx-ax, by-ay; L = vx*vx+vy*vy
            u = max(0, min(1, ((px-ax)*vx+(py-ay)*vy)/L)) if L else 0
            d = math.hypot(px-ax-u*vx, py-ay-u*vy)
            if d > maxd: continue
            score = d
            if s.get("dir") is not None and L:
                brg = math.degrees(math.atan2(vx, vy)) % 180; sd = s["dir"] % 180
                diff = min(abs(brg-sd), 180-abs(brg-sd))
                if diff > 35: continue  # sign must face traffic on this road (rejects cross-street signs)
            if best is None or score < best[0]: best = (score, wi, s)
        if best: matched += 1; per.setdefault(best[1], []).append(best[2])
    out = {}
    for wi, ss in per.items():
        v = sorted(x["mph"] for x in ss); m = v[len(v)//2]   # median posted speed
        s0 = min(ss, key=lambda x: abs(x["mph"] - m))
        out[wi] = (m, f"https://www.mapillary.com/app/?lat={s0['lat']:.6f}&lng={s0['lon']:.6f}&z=19&focus=map&mapFeatureId={s0['id']}", len(ss))
    return out, {"signs": len(signs), "matched": matched, "ways": len(out)}
if __name__ == "__main__":
    print(len(fetch()), "signs")
