import re, math
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

