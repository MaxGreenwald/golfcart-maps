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


def roundabout_inherit(wl, WS, is_road, cap=35):
    """wl: ways with tags/nodes; WS: wi -> (mph, src). Rings (junction=roundabout|circular) whose own limit is unknown
    (src inferred_high) take the max known limit of connecting non-ring roads (cart paths ignored). Kept as-is (red) when no
    approach has a posted/verified limit, or when an unknown-speed major road with a different name feeds the ring.
    Returns {"set": {wi: (mph, "r")}, "rings": n, "unknown": n, "fixed": n, "opened": n, "kept_unsure": n, "log": [...]}."""
    ring = [wi for wi, w in enumerate(wl) if wi in WS and is_road(w) and w["tags"].get("junction") in ("roundabout", "circular")]
    par = {wi: wi for wi in ring}
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    bynode = {}
    for wi, w in enumerate(wl):
        if wi in WS:
            for n in w["nodes"]: bynode.setdefault(n, []).append(wi)
    rs = set(ring)
    for wi in ring:
        for n in wl[wi]["nodes"]:
            for o in bynode[n]:
                if o in rs: par[f(o)] = f(wi)
    groups = {}
    for wi in ring: groups.setdefault(f(wi), []).append(wi)
    res = {"set": {}, "rings": len(groups), "unknown": 0, "fixed": 0, "opened": 0, "no_known_approach": 0, "kept_unsure": 0, "approach_40plus": 0, "log": []}
    for gw in groups.values():
        unk = [wi for wi in gw if WS[wi][1] == "inferred_high"]
        if not unk: continue
        res["unknown"] += 1
        nodes = {n for wi in gw for n in wl[wi]["nodes"]}
        appr = {o for n in nodes for o in bynode[n] if o not in rs and is_road(wl[o])}
        known = [(WS[o][0], WS[o][1] != "inferred") for o in appr if WS[o][1] not in ("inferred_high", "cartpath")] + [(WS[wi][0], WS[wi][1] != "inferred") for wi in gw if WS[wi][1] != "inferred_high"]
        g0 = wl[gw[0]]["geometry"][0]
        lg = {"lat": round(g0["lat"], 5), "lon": round(g0["lon"], 5), "name": wl[gw[0]]["tags"].get("name"), "hw": wl[gw[0]]["tags"].get("highway"), "ways": [wl[w]["id"] for w in gw],
              "approaches": sorted((wl[o]["tags"].get("name") or wl[o]["tags"].get("ref") or "", wl[o]["tags"]["highway"], WS[o][0], WS[o][1]) for o in appr)}
        if not known: res["no_known_approach"] += 1; lg["result"] = "unchanged (no known approach limit)"; res["log"].append(lg); continue
        m, posted = max(k[0] for k in known), any(k[1] for k in known)
        nm = lambda o: wl[o]["tags"].get("name") or wl[o]["tags"].get("ref") or ""
        pnames = {nm(o) for o in appr if WS[o][1] not in ("inferred_high", "cartpath", "inferred")}
        unames = {nm(o) for o in appr if WS[o][1] == "inferred_high"} - pnames
        if not posted or unames:   # only assumed side streets, or an unknown-speed major road we can't vouch for -> keep red
            res["kept_unsure"] += 1; lg["result"] = "unchanged (%s)" % ("only assumed approaches" if not posted else "unknown major approach: " + ", ".join(sorted(unames))); res["log"].append(lg); continue
        lg["result"] = m
        res["fixed"] += 1; res["opened"] += m <= cap; res["approach_40plus"] += m > cap
        for wi in unk: res["set"][wi] = (m, "r")   # 'r' = ring limit taken from its posted approaches
        res["log"].append(lg)
    return res
