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
        if m >= 99:   # highest approach is a banned/no-limit road (e.g. state-highway ban): stay red, keep 'unknown'
            res["kept_unsure"] += 1; lg["result"] = "unchanged (approach is banned or has no limit)"; res["log"].append(lg); continue
        if not posted or unames:   # only assumed side streets, or an unknown-speed major road we can't vouch for -> keep red
            res["kept_unsure"] += 1; lg["result"] = "unchanged (%s)" % ("only assumed approaches" if not posted else "unknown major approach: " + ", ".join(sorted(unames))); res["log"].append(lg); continue
        lg["result"] = m
        res["fixed"] += 1; res["opened"] += m <= cap; res["approach_40plus"] += m > cap
        for wi in unk: res["set"][wi] = (m, "r")   # 'r' = ring limit taken from its posted approaches
        res["log"].append(lg)
    return res


def validate_rings(wl, WS, rbx, cap=35):
    """Guard for the roundabout rule (run by the builders). Returns (errors, warnings).
    error: a ring that still has no limit although every connecting road is <=cap and at least one is posted
           (exactly the Villages bug: red ring between green 35 mph approaches).
    warning: any other ring left without a limit (listed so a human can check OSM)."""
    errs, warns = [], []
    for lg in rbx["log"]:
        if isinstance(lg.get("result"), int): continue
        ap = [a for a in lg["approaches"] if a[3] != "cartpath"]
        known = [a for a in ap if a[3] != "inferred_high"]
        ok = ap and len(known) == len(ap) and all(a[2] <= cap for a in ap) and any(a[3] != "inferred" for a in ap)
        (errs if ok else warns).append(lg)
    return errs, warns

def _len_m(g):
    return sum(math.hypot((g[k+1]["lon"] - g[k]["lon"]) * 111320 * math.cos(math.radians(g[k]["lat"])), (g[k+1]["lat"] - g[k]["lat"]) * 110540) for k in range(len(g) - 1))

def link_inherit(wl, WS, is_road, cap=35, maxlen=400):
    """Short turn lanes / slip lanes (primary/secondary/tertiary_link; never freeway or trunk ramps) with no limit of their own (src inferred_high) take the HIGHEST limit of the
    roads they connect, like roundabouts. Connected unknown links form one group (<= maxlen m in total).
    Stays unknown (red) if any connecting road is >cap (40+ or banned 99), a freeway/trunk road, an unknown main road, or none is posted.
    WS should already include roundabout results (src 'roundabout' counts as posted).
    Returns {"set": {wi: (mph, "k")}, "groups": n, "fixed": n, "kept": n, "log": [...]}."""
    cand = [wi for wi, w in enumerate(wl) if wi in WS and is_road(w) and w["tags"].get("highway", "") in ("primary_link", "secondary_link", "tertiary_link")
            and WS[wi][1] == "inferred_high" and w["tags"].get("junction") not in ("roundabout", "circular")]
    cs = set(cand); bynode = {}
    for wi, w in enumerate(wl):
        if wi in WS:
            for n in w["nodes"]: bynode.setdefault(n, []).append(wi)
    seen, res = set(), {"set": {}, "groups": 0, "fixed": 0, "kept": 0, "log": []}
    for wi in cand:
        if wi in seen: continue
        comp, st = [], [wi]; seen.add(wi)
        while st:
            k = st.pop(); comp.append(k)
            for n in wl[k]["nodes"]:
                for o in bynode[n]:
                    if o in cs and o not in seen: seen.add(o); st.append(o)
        res["groups"] += 1
        g0 = wl[comp[0]]["geometry"][0]; L = sum(_len_m(wl[k]["geometry"]) for k in comp)
        cps = set(comp)
        appr = {o for k in comp for n in wl[k]["nodes"] for o in bynode[n] if o not in cps and is_road(wl[o]) and WS[o][1] != "cartpath"}
        lg = {"lat": round(g0["lat"], 5), "lon": round(g0["lon"], 5), "hw": wl[comp[0]]["tags"]["highway"], "m": round(L), "ways": [wl[k]["id"] for k in comp],
              "approaches": sorted((wl[o]["tags"].get("name") or wl[o]["tags"].get("ref") or "", wl[o]["tags"]["highway"], WS[o][0], WS[o][1]) for o in appr)}
        why = None
        if L > maxlen: why = "too long (%d m)" % L
        elif not appr: why = "no connecting roads"
        elif any(wl[o]["tags"]["highway"].startswith(("motorway", "trunk")) for o in appr): why = "connects a freeway/trunk road"
        elif any(WS[o][1] == "inferred_high" for o in appr): why = "connects an unknown-speed main road"
        elif any(WS[o][0] > cap for o in appr): why = "connects a %d+ mph or banned road" % (cap + 5)
        elif not any(WS[o][1] != "inferred" for o in appr): why = "no posted connecting road"
        if why: res["kept"] += 1; lg["result"] = "unchanged (" + why + ")"
        else:
            m = max(WS[o][0] for o in appr); lg["result"] = m; res["fixed"] += 1
            for k in comp: res["set"][k] = (m, "k")
        res["log"].append(lg)
    return res

# ---- Trails / bike paths are never cart or LSV roads (Oct 19 2026) ----
# Other regions never fetch path/cycleway/footway ways unless OSM tags golf_cart (build_region.py), so bike paths are simply
# absent. In San Diego a few trails are mapped as ordinary roads (e.g. San Diego River Trail North, Mission Valley:
# highway=unclassified + bicycle=designated). Drop them the same way. A way is a trail when its highway type is a path type,
# or it is a service/unclassified/track way that either carries a trail name plus trail-style tags (designated bike/foot,
# hiking scale, dirt, no motor vehicles) or is closed to motor vehicles and designated for bikes (a bike path mapped as a road).
# Deliberately narrow: motor_vehicle=private/no alone also marks gated streets and HOV lanes, which are handled elsewhere.
# tests/test_trails_coronado.py guards the built tiles.
TRAIL_HW = {"path", "cycleway", "footway", "bridleway", "track", "pedestrian", "steps"}
TRAIL_NAME = re.compile(r"\b(Trails?|Bike ?Path|Bikeway|Greenway|Multi-?Use Path|Rail Trail)\b(\s+(North|South|East|West))?$", re.I)
_CARTV = ("yes", "designated")
def is_trail(t):
    if t.get("golf_cart") in _CARTV: return False
    hw = t.get("highway", "")
    if hw in TRAIL_HW: return True
    if hw not in ("service", "unclassified", "track"): return False
    nomotor = any(t.get(k) == "no" for k in ("motor_vehicle", "vehicle", "motorcar"))
    if nomotor and t.get("bicycle") == "designated": return True
    if TRAIL_NAME.search(t.get("name", "")):
        return (nomotor or t.get("bicycle") == "designated" or t.get("foot") == "designated" or "sac_scale" in t
                or t.get("surface") in ("dirt", "ground", "unpaved", "gravel", "fine_gravel", "compacted"))
    return False
