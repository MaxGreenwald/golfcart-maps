"""Speed overrides from research/road_intel.json (high/medium confidence only).
Each rule: research index, OSM name regex, bbox (S,W,N,E), optional (cross_from, cross_to) regexes
whose intersection latitudes bound the segment (roads here run ~N-S; for E-W roads use lon)."""
import json, os, re
HERE = os.path.dirname(__file__)
INTEL = json.load(open(os.path.join(HERE, "..", "research", "road_intel.json")))
import datetime as _dt
# Del Mar speed ordinance (Clerk's File 904-4): introduced Oct 6 2026, second reading Oct 20 2026, effective
# Nov 19 2026 (30 days after adoption); the city replaces the signs after that. Source of truth: the Oct 20 2026
# agenda packet, Item 6, Table 1 + Attachment A. Until a segment's new limit is in force AND the new signs are
# confirmed (street imagery or a site visit), the map uses the limit that is posted TODAY. Showing the new, lower
# limit early made three 40-45 mph stretches look LSV-legal (fixed Oct 18 2026).
DM_SRC = "https://www.delmar.ca.us/AgendaCenter/ViewFile/Agenda/_10202026-3943"
DM_EFFECTIVE = "2026-11-19"
DM_SIGNS_CONFIRMED = False   # set True only after the new signs are seen (Street View / Mapillary / site visit)
# (road, segment, posted today, ordinance limit)
_DM = [("Camino del Mar", "Via de la Valle - San Dieguito Bridge", 40, 30),
       ("Camino del Mar", "Coast Blvd - Del Mar Plaza", 35, 30),
       ("Jimmy Durante Blvd", "Via de la Valle - Fairgrounds Gate 2", 45, 40),
       ("Jimmy Durante Blvd", "Fairgrounds Gate 2 - San Dieguito Dr", 45, 30),
       ("Jimmy Durante Blvd", "San Dieguito Dr - Camino del Mar", 35, 30),
       ("Via de la Valle", "Camino del Mar - Jimmy Durante Blvd", 40, 35)]
def dm_in_force(today=None):
    today = today or _dt.date.today().isoformat()
    return today >= DM_EFFECTIVE and DM_SIGNS_CONFIRMED
SURVEY = "https://www.delmar.ca.us/AgendaCenter/ViewFile/Agenda/_09142026-3926"
DM_BASE = len(INTEL)
for road, seg, now_, new_ in _DM:
    use = new_ if dm_in_force() else now_
    note = (f"ordinance limit {new_} mph, in force since {DM_EFFECTIVE}" if dm_in_force() else
            f"posted {now_} mph today; ordinance lowers it to {new_} mph from {DM_EFFECTIVE}, once new signs are up")
    INTEL.append({"road": road, "city": "Del Mar", "from_to_segment_if_known": seg + " — " + note, "speed_mph": use, "lsv_ok": use <= 35,
                  "source_url": DM_SRC, "confidence": "high"})
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
 19: (r"^Camino del Mar$", (32.945, -117.275, 32.96, -117.24), r"9th Street", r"4th Street", "lat"),  # survey seg 7-8: 35
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
_DMBOX = (32.955, -117.275, 32.985, -117.25)
RULES.update({
 DM_BASE + 0: (r"^Camino del Mar$", _DMBOX, r"__BRIDGE__", r"Via de la Valle", "lat"),
 DM_BASE + 1: (r"^Camino del Mar$", _DMBOX, r"__DMPLAZA__", r"Coast Boulevard", "lat"),
 DM_BASE + 2: (r"^Jimmy Durante Boulevard$", _DMBOX, r"__GATE2__", r"Via de la Valle", "lat"),
 DM_BASE + 3: (r"^Jimmy Durante Boulevard$", _DMBOX, r"__SDD__", r"__GATE2__", "lat"),
 DM_BASE + 4: (r"^Jimmy Durante Boulevard$", _DMBOX, r"Camino del Mar", r"__SDD__", "lat"),
 DM_BASE + 5: (r"^Via de la Valle$", _DMBOX, r"Camino del Mar", r"Jimmy Durante Boulevard", "lon"),
})
# rules applied later win: drop older Del Mar research rules superseded by the ordinance
# Del Mar FY2026-27 Engineering & Traffic Survey (TPAC Sept 14 2026, Table 2) + Max's Street View photos (40 signs at 210 S Camino Del Mar, Mar 2025; 261 County Hwy S21, Feb 2025)
SV_BASE = len(INTEL)
INTEL.append({"road": "South Camino del Mar (S21)", "city": "Del Mar", "from_to_segment_if_known": "4th St/Del Mar Heights Rd - Carmel Valley Rd: posted 40 (survey seg 9; Street View signs)", "speed_mph": 40, "lsv_ok": False, "source_url": SURVEY, "confidence": "high"})
INTEL.append({"road": "Camino del Mar", "city": "Del Mar", "from_to_segment_if_known": "San Dieguito Bridge - Coast Blvd: posted 25 (survey seg 3)", "speed_mph": 25, "lsv_ok": True, "source_url": SURVEY, "confidence": "high"})
RULES[SV_BASE] = (r"^(South Camino del Mar|Camino del Mar)$", (32.9395, -117.275, 32.9482, -117.25), None, None, "lat")
RULES[SV_BASE + 1] = (r"^Camino del Mar$", _DMBOX, r"Coast Boulevard", r"__BRIDGE__", "lat")
RULES.pop(16, None); RULES.pop(17, None)  # superseded by survey seg 3
# fixed coordinates for landmarks that aren't cross streets (approximate)
FIXED = {"__POTTERY__": -117.2585, "__BRIDGE__": 32.9745, "__DMPLAZA__": 32.9595, "__GATE2__": 32.9757, "__SDD__": 32.9665, "__LJVD__": -117.236, "__SWAMIS__": 33.0345, "__MANZANO__": 33.112,
         "__I5__": None, "__NORTH__": None, "__SOUTH__": None}
I5_LON = {28: -117.282, 29: -117.2647, 37: -117.3513, 38: -117.3623}  # 29/37/38 = measured I-5 crossings (accuracy sweep Oct 13 2026)

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

# ---- Max's verified updates (Oct 12 2026) ----
# Coronado Orange Ave: replaces research #39 (45, paratransit code). 35 from ~10th St/1466 Orange to RH Dana Pl/Hotel del; 25-30 north of that.
_SVB = len(INTEL)
_ORG_SRC = "https://www.mapillary.com/app/?lat=32.694275&lng=-117.17524&z=19&focus=map&mapFeatureId=1770240414010580"
INTEL.append({"road": "Orange Ave", "city": "Coronado", "from_to_segment_if_known": "10th St (1466 Orange) - RH Dana Pl / Hotel del: posted 35 — Google Street View Jun 2026 (Max), Mapillary Aug 2026",
              "speed_mph": 35, "lsv_ok": True, "source_url": "https://www.google.com/maps/@32.6858,-117.1789,3a,75y,150h,90t/data=!3m1!1e3", "confidence": "high"})
INTEL.append({"road": "Orange Ave", "city": "Coronado", "from_to_segment_if_known": "Ferry Landing/1st St - 10th St: posted 25-30 — Google Street View Jun 2026 (Max), Mapillary Aug 2026",
              "speed_mph": 30, "lsv_ok": True, "source_url": _ORG_SRC, "confidence": "high"})
INTEL.append({"road": "S Coast Hwy 101", "city": "Encinitas (Cardiff)", "from_to_segment_if_known": "Swami's - San Elijo bridge: posted 30 — Street View Mar 2025 and Sep 2025 (Max)",
              "speed_mph": 30, "lsv_ok": True, "source_url": "https://www.google.com/maps/@33.0186,-117.2822,3a,75y,160h,90t/data=!3m1!1e3", "confidence": "high"})
RULES.pop(39, None); RULES.pop(26, None)
RULES[_SVB] = (r"^(Orange Avenue|R\.H\. Dana Place)$", CO, r"__SOUTH__", r"__CO10__", "lat")  # incl. RH Dana Pl at the Hotel del end
RULES[_SVB + 1] = (r"^Orange Avenue$", CO, r"__CO10__", r"__NORTH__", "lat")
RULES[_SVB + 2] = (r"^(South Coast Highway 101|South Highway 101|South Coast Highway|US 101 Hist|Coast Highway 101)$", (32.99, -117.31, 33.035, -117.26), r"__SWAMIS__", r"__SOUTH__", "lat")
FIXED["__CO10__"] = 32.6866  # Orange Ave at 10th St (~1466 Orange)

# ---- Grand Ave, Pacific Beach (Oct 13 2026) ----
# Beach Mode Rentals (local cart rental shop) reports Grand Ave is posted 35; Mapillary detected 35 mph signs at 5 spots
# from west of Mission Blvd to east of Ingraham (one sign each, below the 2-sign auto-flip rule). OSM still says 45.
# City resolution R-316675 (Mar 2026) lists Grand Av (W/O Mission Bl - Ingraham St) and (Ingraham St - Mission Bay Dr) for reduced limits.
_GRB = len(INTEL)
INTEL.append({"road": "Grand Ave", "city": "San Diego (Pacific Beach)", "from_to_segment_if_known": "Mission Blvd - Mission Bay Dr: posted 35 (local rental shop report; Mapillary 35 mph signs; city 2026 speed resolution)",
              "speed_mph": 35, "lsv_ok": True, "source_url": "https://www.mapillary.com/app/?lat=32.797810&lng=-117.240740&z=19&focus=map&mapFeatureId=852220818707394", "confidence": "high"})
RULES[_GRB] = (r"^Grand Avenue$", (32.79, -117.262, 32.81, -117.21), r"^Mission Boulevard$", r"__MBD__", "lon")
FIXED["__MBD__"] = -117.2140  # Grand Ave at Mission Bay Dr (east end of the city segment; Mission Bay Dr itself is outside the coastal strip)

# ---- Accuracy sweep (Oct 13 2026) ----
# research/accuracy_sweep.json: per-way overrides from official city speed lists (San Diego R-316675, Encinitas Ord. 2026-05
# Exhibit A, Oceanside Traffic Code Art. XIV, Imperial Beach MC 10.28.020) and the Mapillary corridor rule (3+ distinct
# spots on one named road agreeing on <=35). Keyed by OSM name + first/last node so they survive rebuilds; the curated
# rules above always win. Generated by research/accuracy_sweep.py-style analysis; each entry cites its source.
_SWEEP_P = os.path.join(HERE, "..", "research", "accuracy_sweep.json")
SWEEP = json.load(open(_SWEEP_P))["ways"] if os.path.exists(_SWEEP_P) else {}
def way_key(t, nk): return f'{t.get("name", "")}|{nk[0]}|{nk[-1]}'
_build_curated = build
def build(ways):
    out, report = _build_curated(ways)
    n = 0
    for i, (t, g, nk) in enumerate(ways):
        if i in out: continue
        e = SWEEP.get(way_key(t, nk))
        if e: out[i] = (e["mph"], e["mph"] < 40, e["url"], e["label"]); n += 1
    report.append(("sweep", "accuracy sweep", f"{n} ways"))
    return out, report
