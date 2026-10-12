"""Speed overrides from research/road_intel.json (high/medium confidence only).
Each rule: research index, OSM name regex, bbox (S,W,N,E), optional (cross_from, cross_to) regexes
whose intersection latitudes bound the segment (roads here run ~N-S; for E-W roads use lon)."""
import json, os, re
HERE = os.path.dirname(__file__)
INTEL = json.load(open(os.path.join(HERE, "..", "research", "road_intel.json")))
PB = (32.755, -117.262, 32.815, -117.235); LJ = (32.795, -117.29, 32.885, -117.22)
DM = (32.935, -117.275, 32.985, -117.24); SB = (32.97, -117.28, 33.01, -117.24)
EN = (33.0, -117.31, 33.095, -117.24); CB = (33.08, -117.36, 33.18, -117.27)
OC = (33.165, -117.40, 33.26, -117.30); CO = (32.66, -117.20, 32.70, -117.15); IB = (32.55, -117.145, 32.60, -117.115)
OB = (32.70, -117.26, 32.76, -117.22)
# idx: (name regex, bbox, cross_from, cross_to, axis)
RULES = {
 0: (r"^Mission Boulevard$", PB, r"Santa Clara Place", r"Loring Street", "lat"),
 2: (r"^La Jolla Boulevard$", (32.805, -117.29, 32.845, -117.25), None, None, "lat"),
 4: (r"^Prospect Street$", LJ, None, None, "lat"),
 5: (r"^(East )?Torrey Pines Road$", LJ, r"Girard Avenue", r"Prospect Place", "lon"),
 6: (r"^(East )?Torrey Pines Road$", LJ, r"Prospect Place", r"__POTTERY__", "lon"),
 7: (r"^(East )?Torrey Pines Road$", LJ, r"__POTTERY__", r"__LJVD__", "lon"),
 8: (r"^La Jolla Parkway$", LJ, None, None, "lat"),
 9: (r"^North Torrey Pines Road$", (32.86, -117.27, 32.94, -117.22), None, None, "lat"),
 10: (r"^La Jolla Shores Drive$", LJ, None, None, "lat"),
 11: (r"^(Pearl Street|Girard Avenue|Nautilus Street|El Paseo Grande)$", LJ, None, None, "lat"),
 14: (r"^Sunset Cliffs Boulevard$", OB, r"Niagara Avenue", r"Cape May Avenue", "lat"),
 16: (r"^Camino del Mar$", DM, r"27th Street", r"Coast Boulevard", "lat"),
 17: (r"^Camino del Mar$", (32.965, -117.275, 32.985, -117.25), r"__BRIDGE__", r"27th Street", "lat"),
 18: (r"^Camino del Mar$", DM, r"__DMPLAZA__", r"9th Street", "lat"),
 19: (r"^(Camino del Mar|South Camino del Mar)$", (32.925, -117.275, 32.96, -117.24), r"9th Street", r"__SOUTH__", "lat"),
 20: (r"^(South Coast Highway 101|North Coast Highway 101|South Highway 101|North Highway 101|Highway 101|Camino del Mar|South Coast Highway|North Coast Highway|US 101 Hist)$", SB, r"__NORTH__", r"Dahlia Drive", "lat"),
 21: (r"^(South Coast Highway 101|North Coast Highway 101|South Highway 101|North Highway 101|Highway 101|Camino del Mar|South Coast Highway|North Coast Highway|US 101 Hist)$", (32.97, -117.28, 32.995, -117.25), r"Dahlia Drive", r"Via de la Valle", "lat"),
 22: (r"^(North |South )?Sierra Avenue$", SB, r"Plaza Street", r"Border Avenue", "lat"),
 23: (r"^Lomas Santa Fe Drive$", SB, r"(Highway 101|Coast Highway)", r"Stevens Avenue", "lon"),
 24: (r"^(North Coast Highway 101|North Highway 101|North Coast Highway|US 101 Hist)$", EN, r"La Costa Avenue", r"Encinitas Boulevard", "lat"),
 25: (r"^(South Coast Highway 101|South Highway 101|South Coast Highway|US 101 Hist)$", (33.02, -117.31, 33.05, -117.27), r"Encinitas Boulevard", r"__SWAMIS__", "lat"),
 26: (r"^(South Coast Highway 101|South Highway 101|South Coast Highway|US 101 Hist|Coast Highway 101)$", (32.99, -117.31, 33.035, -117.26), r"__SWAMIS__", r"__SOUTH__", "lat"),
 27: (r"^San Elijo Avenue$", EN, r"Santa Fe Drive", r"Chesterfield Drive", "lat"),
 28: (r"^Leucadia Boulevard$", EN, r"(Highway 101|Coast Highway)", r"__I5__", "lon"),
 29: (r"^Manchester Avenue$", EN, r"San Elijo Avenue", r"__I5__", "lon"),
 30: (r"^Carlsbad Boulevard$", CB, r"__NORTH__", r"State Street", "lat"),
 31: (r"^Carlsbad Boulevard$", CB, r"State Street", r"Tamarack Avenue", "lat"),
 32: (r"^Carlsbad Boulevard$", CB, r"Tamarack Avenue", r"__MANZANO__", "lat"),
 33: (r"^Carlsbad Boulevard$", CB, r"__MANZANO__", r"Island Way", "lat"),
 34: (r"^Carlsbad Boulevard$", (33.06, -117.33, 33.12, -117.28), r"Island Way", r"__SOUTH__", "lat"),
 35: (r"^(North |South )?Coast Highway$", OC, r"Wisconsin Avenue", r"__SOUTH__", "lat"),
 36: (r"^(North |South )?(The )?Strand( North| South)?$", OC, None, None, "lat"),
 37: (r"^Vista Way$", OC, r"Coast Highway", r"__I5__", "lon"),
 38: (r"^Oceanside Boulevard$", OC, r"Coast Highway", r"__I5__", "lon"),
 39: (r"^Orange Avenue$", CO, None, None, "lat"),
 40: (r"^Seacoast Drive$", IB, r"Palm Avenue", r"Imperial Beach Boulevard", "lat"),
}
# fixed coordinates for landmarks that aren't cross streets (approximate)
FIXED = {"__POTTERY__": -117.2585, "__BRIDGE__": 32.9745, "__DMPLAZA__": 32.9595, "__LJVD__": -117.236, "__SWAMIS__": 33.0345, "__MANZANO__": 33.112,
         "__I5__": None, "__NORTH__": None, "__SOUTH__": None}
I5_LON = {28: -117.282, 29: -117.258, 37: -117.36, 38: -117.355}

def inb(p, b): return b[0] <= p[1] <= b[2] and b[1] <= p[0] <= b[3]

def build(ways):
    """ways: list of (tags, coords[[lon,lat]...], nodekeys). Returns {way_index: (mph, lsv_ok, url, label)}"""
    nodes_by_name = {}
    for i, (t, g, nk) in enumerate(ways):
        nm = t.get("name", "")
        for k, p in zip(nk, g): nodes_by_name.setdefault(k, set()).add(nm)
    def cross(road_re, x_re, bbox, axis):
        r, x = re.compile(road_re), re.compile(x_re, re.I); vals = []
        for t, g, nk in ways:
            if not r.search(t.get("name", "")): continue
            for k, p in zip(nk, g):
                if inb(p, bbox) and any(x.search(n) for n in nodes_by_name.get(k, ())): vals.append(p[1] if axis == "lat" else p[0])
        return sum(vals) / len(vals) if vals else None
    out, report = {}, []
    for idx, (rre, bbox, cf, ct, axis) in RULES.items():
        e = INTEL[idx]
        if e["confidence"] not in ("high", "medium"): continue
        mph, ok = e["speed_mph"], e["lsv_ok"]
        if mph is None and ok is None: continue
        if mph is None: mph = 35 if ok else 45
        lo = hi = None
        if cf:
            def pos(c):
                if c in FIXED and FIXED[c] is not None: return FIXED[c]
                if c == "__I5__": return I5_LON.get(idx)
                if c in ("__NORTH__", "__SOUTH__"): return None
                return cross(rre, c, bbox, axis)
            a, b = pos(cf), pos(ct)
            if a is None and cf not in ("__NORTH__", "__SOUTH__", "__I5__"): report.append((idx, e["road"], "cross not found: " + cf)); continue
            if b is None and ct not in ("__NORTH__", "__SOUTH__", "__I5__"): report.append((idx, e["road"], "cross not found: " + ct)); continue
            if a is not None and b is not None: lo, hi = min(a, b), max(a, b)
            else:
                v = a if a is not None else b; open_end = ct if a is not None else cf
                if v is None: lo = hi = None
                elif open_end == "__NORTH__": lo, hi = v, 999
                else: lo, hi = -999, v   # __SOUTH__ (lat) or unknown west/coast end
        r = re.compile(rre); n = 0
        for i, (t, g, nk) in enumerate(ways):
            if not r.search(t.get("name", "")): continue
            mid = g[len(g) // 2]
            if not inb(mid, bbox): continue
            if lo is not None:
                v = mid[1] if axis == "lat" else mid[0]
                if not (lo - 1e-4 <= v <= hi + 1e-4): continue
            out[i] = (mph, ok, e["source_url"], f'{e["road"]} ({e["from_to_segment_if_known"] or e["city"]})'); n += 1
        report.append((idx, e["road"], f"{n} ways -> {mph} mph"))
    return out, report
