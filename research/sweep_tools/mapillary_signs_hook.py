import sys;sys.path.insert(0,"/workspace/golfcart-maps/scripts")
from mapillary_signs import *
import math
def per_signs(ways, maxd=20.0):
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
    return per
