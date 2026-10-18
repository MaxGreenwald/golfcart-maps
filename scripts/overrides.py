"""Speed overrides from research/road_intel.json (high/medium confidence only).
Each rule: research index, OSM name regex, bbox (S,W,N,E), optional (cross_from, cross_to) regexes
whose intersection latitudes bound the segment (roads here run ~N-S; for E-W roads use lon)."""
import json, os, re
HERE = os.path.dirname(__file__)
INTEL = json.load(open(os.path.join(HERE, "..", "research", "road_intel.json")))
DM_SRC = "https://thecoastnews.com/del-mar-moves-to-lower-speed-limits-explore-additional-parking/"
DM_NOTE = "adopted Oct 2026, signs may still show old limit"
# Del Mar council speed ordinance (Oct 2026; user-provided map + Coast News article). Appended as extra intel entries.
_DM = [("Camino del Mar", "Via de la Valle - San Dieguito Bridge", 30, True),
       ("Camino del Mar", "Coast Blvd - Del Mar Plaza", 30, True),
       ("Jimmy Durante Blvd", "Via de la Valle - Fairgrounds Gate 2", 40, False),
       ("Jimmy Durante Blvd", "Fairgrounds Gate 2 - San Dieguito Dr", 30, True),
       ("Jimmy Durante Blvd", "San Dieguito Dr - Camino del Mar", 30, True),
       ("Via de la Valle", "Camino del Mar - Jimmy Durante Blvd", 35, True)]
SURVEY = "https://www.delmar.ca.us/AgendaCenter/ViewFile/Agenda/_09142026-3926"
DM_BASE = len(INTEL)
for road, seg, mph_, ok in _DM:
    INTEL.append({"road": road, "city": "Del Mar", "from_to_segment_if_known": seg + " — " + DM_NOTE, "speed_mph": mph_, "lsv_ok": ok,
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

# ---- Carlsbad Municipal Code ch. 10.44 Article II speed limits (E&TS-based; https://ecode360.com/44006773), coastal streets (Oct 18 2026) ----
# Carlsbad Blvd itself is already covered above (research #30-34, same code). Streets not listed in 10.44 keep OSM/defaults.
C_SRC = "https://ecode360.com/44006773#10.44-coastal-streets"
# Safety: these code sections are old (some 1970s-2000s). They may lower a limit, but they never turn a road OSM shows
# as 40+ (or unknown major) into an LSV-legal road unless a posted sign (Mapillary, 1+) agrees. Otherwise: listed for a Street View check.
CORROBORATE_FLIP = {C_SRC}
_CBX = (33.08, -117.36, 33.176, -117.27)
_CMC = [  # (road, segment text, mph, name regex, cross_from, cross_to, axis, I-5 lon if an end is I-5)
    ("Tamarack Ave", "Carlsbad Blvd - I-5 (MC 10.44.300 A)", 30, r"^Tamarack Avenue$", r"^Carlsbad Boulevard$", "__I5__", "lon", -117.3367),
    ("Grand Ave", "Ocean St - I-5 (MC 10.44.440)", 25, r"^Grand Avenue$", r"^Ocean Street$", "__I5__", "lon", -117.3410),
    ("Carlsbad Village Dr", "Pio Pico Dr - Highland Dr (MC 10.44.080 A)", 35, r"^Carlsbad Village Drive$", r"^Pio Pico Drive$", r"^Highland Drive$", "lon", None),
    ("Jefferson St", "Grand Ave - north city limit (MC 10.44.050)", 35, r"^Jefferson Street$", r"^Grand Avenue$", "__NORTH__", "lat", None),
    ("Pio Pico Dr", "Tamarack Ave - Elm Ave/Carlsbad Village Dr (MC 10.44.310)", 35, r"^Pio Pico Drive$", r"^Tamarack Avenue$", r"^Carlsbad Village Drive$", "lat", None),
    ("Poinsettia Ln", "Carlsbad Blvd - Paseo del Norte (MC 10.44.360 A)", 35, r"^Poinsettia Lane$", r"^Carlsbad Boulevard$", r"^Paseo del Norte$", "lon", None),
    ("Cannon Rd", "Carlsbad Blvd - Paseo del Norte (MC 10.44.380 A)", 35, r"^Cannon Road$", r"^Carlsbad Boulevard$", r"^Paseo del Norte$", "lon", None),
    ("Palomar Airport Rd", "Carlsbad Blvd - Paseo del Norte (MC 10.44.170 A)", 35, r"^Palomar Airport Road$", r"^Carlsbad Boulevard$", r"^Paseo del Norte$", "lon", None),
    ("Laguna Dr", "State St - Jefferson St (MC 10.44.580)", 30, r"^Laguna Drive$", r"^State Street$", r"^Jefferson Street$", "lon", None),
    ("Las Flores Dr", "Jefferson St - Highland Dr (MC 10.44.560)", 30, r"^Las Flores Drive$", r"^Jefferson Street$", r"^Highland Drive$", "lon", None),
    ("Chestnut Ave", "Pio Pico Dr - El Camino Real (MC 10.44.040 A)", 30, r"^Chestnut Avenue$", r"^Pio Pico Drive$", r"^El Camino Real$", "lon", None),
]
for road, seg, mph_, rre, cf, ct, axis, i5 in _CMC:
    k = len(INTEL)
    INTEL.append({"road": road, "city": "Carlsbad", "from_to_segment_if_known": seg, "speed_mph": mph_, "lsv_ok": mph_ <= 35, "source_url": C_SRC, "confidence": "high"})
    RULES[k] = (rre, _CBX if axis == "lon" else (33.155, -117.36, 33.176, -117.33), cf, ct, axis)
    if i5 is not None: I5_LON[k] = i5

# ---- Grand Ave, Pacific Beach (Oct 13 2026) ----
# Beach Mode Rentals (local cart rental shop) reports Grand Ave is posted 35; Mapillary detected 35 mph signs at 5 spots
# from west of Mission Blvd to east of Ingraham (one sign each, below the 2-sign auto-flip rule). OSM still says 45.
# City resolution R-316675 (Mar 2026) lists Grand Av (W/O Mission Bl - Ingraham St) and (Ingraham St - Mission Bay Dr) for reduced limits.
_GRB = len(INTEL)
INTEL.append({"road": "Grand Ave", "city": "San Diego (Pacific Beach)", "from_to_segment_if_known": "Mission Blvd - Mission Bay Dr: posted 35 (local rental shop report; Mapillary 35 mph signs; city 2026 speed resolution)",
              "speed_mph": 35, "lsv_ok": True, "source_url": "https://www.mapillary.com/app/?lat=32.797810&lng=-117.240740&z=19&focus=map&mapFeatureId=852220818707394", "confidence": "high"})
RULES[_GRB] = (r"^Grand Avenue$", (32.79, -117.262, 32.81, -117.21), r"^Mission Boulevard$", r"__MBD__", "lon")
FIXED["__MBD__"] = -117.2140  # Grand Ave at Mission Bay Dr (east end of the city segment; Mission Bay Dr itself is outside the coastal strip)

# ---- Safety caution (Oct 18 2026): stretches where a dated sign photo or OpenStreetMap shows a HIGHER limit than our source ----
# Conservative rule: where a dated sign photo shows the higher posted limit, use it (a local limit only takes effect once its
# signs are up, CVC 22357), and flag the stretch in the app (CAU list in public/app.js matches these labels). Where only
# OpenStreetMap disagrees, keep the official value and flag it. Evidence: research/sd_safety_caution.md.
_SC = len(INTEL)
MLY = "https://www.mapillary.com/app/?lat=%s&lng=%s&z=19&focus=map&mapFeatureId=%s"
INTEL.append({"road": "La Jolla Blvd", "city": "San Diego (Bird Rock)", "from_to_segment_if_known": "Loring St - Colima St: posted 35 \u2014 Mapillary sign photos Jan 8 2025; city voted 25 in Mar 2026 (R-316675), new signs not confirmed",
              "speed_mph": 35, "lsv_ok": True, "source_url": MLY % ("32.810455", "-117.266100", "9238952249552002"), "confidence": "high"})
INTEL.append({"road": "Mission Blvd", "city": "San Diego (Pacific Beach)", "from_to_segment_if_known": "Santa Clara Pl - Loring St: posted 30 \u2014 Mapillary sign photos Jan 8 2025; city lowering to 25 (R-316675), new signs not confirmed",
              "speed_mph": 30, "lsv_ok": True, "source_url": MLY % ("32.803837", "-117.257860", "960076746257679"), "confidence": "high"})
INTEL.append({"road": "Lomas Santa Fe Dr", "city": "Solana Beach", "from_to_segment_if_known": "at Hwy 101: city lists 35, OpenStreetMap says 50 \u2014 check posted signs",
              "speed_mph": 35, "lsv_ok": True, "source_url": "https://cityofsolanabeach.ca.gov/sites/default/files/Solana%20Beach/Meetings/City%20Council/2023/07-12-23/07-12-23%20Reg/A.3.%20Report%20-%2007-12-23%20-%20O.pdf", "confidence": "high"})
RULES[_SC] = (r"^La Jolla Boulevard$", (32.80, -117.275, 32.815, -117.25), r"^Loring Street$", r"^Colima Street$", "lat")
RULES[_SC + 1] = (r"^Mission Boulevard$", PB, r"Santa Clara Place", r"Loring Street", "lat")   # replaces rule 0 (25, KPBS Feb 2025)
RULES[_SC + 2] = (r"^Lomas Santa Fe Drive$", SB, r"(Highway 101|Coast Highway)", r"__LSF101E__", "lon")  # the 4 short ways OSM tags 50
RULES.pop(0, None)
FIXED["__LSF101E__"] = -117.2712  # east end of the OSM-50 ways at Hwy 101 (next way east is tagged 35)

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
