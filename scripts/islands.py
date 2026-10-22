"""Same-road red islands: ONE implementation shared by both builders (heal) and validate_data.py (detect).

A same-road red island is a short run (< ISLAND_M, about 0.5 mi) of one road drawn red (limit over 35 mph, or none) while the
SAME road continues on both ends at 35 mph or less. Real limits almost never go 35 -> 45 -> 35 over a few hundred metres, so an
island is nearly always a data problem: an untagged split piece, an unnamed carriageway of a divided road (Soledad Mountain Rd,
Oct 18 2026), one stray OSM tag, or a DOT speed line bleeding onto a side street at a junction.

Works on the built segment format [nameIdx, hw, mph, code, oneway, fromNode, toNode, [[lon,lat]...], srcIdx?, flag?].
Unnamed pieces borrow the name of the road that continues at two or more of their ends, so they count as part of that road.
Explicit bans (code 'v' with no limit = an ordinance/designated-only rule) are legal statements, not speed data, and are skipped.
"""
import math, re
ISLAND_M = 805            # 0.5 mi
SINGLE_M = 300            # one disagreeing source is only overruled on short stretches; a longer 40+ run may be a real zone
CAP = 35                  # LSV cap; "red" here means over 35 mph or no limit
KNOWN = set("tvmdrkno")   # o = trusted OSM (scripts/trusted_osm.py)    # codes that carry a real posted limit (tag, official, Mapillary, designated, inherited, same-road)
SKIP_HW = ("motorway", "trunk")   # freeways/expressways: red is expected
NOT_ROAD = {"path", "footway", "cycleway", "track", "pedestrian", "steps", "bridleway"}

def seg_len(s):
    p = s[7]; return sum(math.hypot((p[k+1][0]-p[k][0]) * 111320 * math.cos(math.radians(p[k][1])), (p[k+1][1]-p[k][1]) * 110540) for k in range(len(p) - 1))

def is_red(s): return s[2] is None or s[2] > CAP
def is_ban(s): return s[3] == "v" and (s[2] is None or s[2] == 99)

def find(segs, names):
    """Islands as dicts: idx (segment indices), name, borrowed, m, hw, codes, mph_in, mph_out, known_out, ends, at [lat, lon]."""
    bynode = {}
    for i, s in enumerate(segs):
        for n in (s[5], s[6]): bynode.setdefault(n, []).append(i)
    def road(i): s = segs[i]; return s[3] != "c" and s[1] not in NOT_ROAD
    cand = [i for i, s in enumerate(segs) if is_red(s) and road(i) and not s[1].startswith(SKIP_HW) and not is_ban(s)]
    cs_ = set(cand); seen = set(); out = []
    for i0 in cand:
        if i0 in seen: continue
        key = segs[i0][0]; comp, st = [], [i0]; seen.add(i0)
        while st:   # same name, red, connected
            k = st.pop(); comp.append(k)
            for n in (segs[k][5], segs[k][6]):
                for j in bynode[n]:
                    if j in cs_ and j not in seen and segs[j][0] == key: seen.add(j); st.append(j)
        C = set(comp); m = sum(seg_len(segs[k]) for k in comp)
        if m >= ISLAND_M: continue
        bnodes = {n for k in comp for n in (segs[k][5], segs[k][6]) if any(j not in C and road(j) for j in bynode[n])}
        nm, borrowed = key, False
        if not names[key]:   # unnamed piece: borrow the one name that continues at 2+ of its ends
            cnt = {}
            for n in bnodes:
                for x in {segs[j][0] for j in bynode[n] if j not in C and road(j) and names[segs[j][0]]}: cnt[x] = cnt.get(x, 0) + 1
            best = [x for x, c in cnt.items() if c >= 2]
            if len(best) != 1: continue
            nm, borrowed = best[0], True
        ends = {n: [j for j in bynode[n] if j not in C and road(j) and segs[j][0] == nm] for n in bnodes}
        ends = {n: v for n, v in ends.items() if v}
        if len(ends) < 2: continue
        conts = [j for v in ends.values() for j in v]
        if any(is_red(segs[j]) for j in conts): continue   # red on a side too: a real change of limit, not an island
        p = segs[comp[0]][7][len(segs[comp[0]][7]) // 2]
        out.append({"idx": sorted(comp), "name": names[nm], "nidx": nm, "borrowed": borrowed, "m": round(m), "hw": segs[comp[0]][1],
                    "codes": "".join(sorted({segs[k][3] for k in comp})), "mph_in": sorted({segs[k][2] or 0 for k in comp}),
                    "mph_out": sorted({segs[j][2] for j in conts}), "known_out": all(segs[j][3] in KNOWN for j in conts),
                    "ends": ends, "at": [round(p[1], 5), round(p[0], 5)]})
    return out

def _mly_signs(s, sources):
    try: return int(re.search(r"Mapillary: (\d+) posted", sources[s[8]][1]).group(1))
    except Exception: return 1

def kind(isl, segs, sources=None):
    """'gap' = no limit of its own; 'single' = one unconfirmed source (OSM tag only, or Mapillary with 1 sign);
    'confirmed' = an official/verified source, two agreeing sources, or 2+ Mapillary signs."""
    c = set(isl["codes"])
    if c <= {"i"} and all(segs[k][2] in (None, 99) for k in isl["idx"]): return "gap"
    if c <= {"t", "o", "i"}: return "single"
    if c <= {"m", "i"} and sources is not None and all(_mly_signs(segs[k], sources) < 2 for k in isl["idx"] if segs[k][3] == "m"): return "single"
    return "confirmed"

def heal(segs, names, sources):
    """Pipeline rule, run by every builder after all speed sources (and the roundabout/turn-lane passes) are applied.
    Only acts when the same road is posted <= 35 on both sides by a REAL source (KNOWN codes), and never lowers below the
    highest neighbour.
    - gap:    no limit of its own (untagged split piece / unnamed carriageway) -> inherits that limit, code 'n'.
    - single: one source (an OSM tag, or one Mapillary sign) disagrees with BOTH sides. One source can't turn a road red on its
              own when the stretch is <= SINGLE_M: it inherits the neighbour limit as code 'q' = caution ("sources disagree, check posted signs"; drawn dashed
              orange, penalised in routing, warned in route steps). An official/verified source or a second agreeing source
              ('confirmed') keeps it red.
    Returns the list of changes for the build log."""
    sidx = {tuple(x): i for i, x in enumerate(sources)}
    def src_i(url, label):
        k = (url, label)
        if k not in sidx: sidx[k] = len(sources); sources.append([url, label])
        return sidx[k]
    changes = []
    for _ in range(2):   # 2nd pass: an unnamed piece next to a just-healed named piece
        n0 = len(changes)
        for isl in find(segs, names):
            if not isl["known_out"]: continue
            kd = kind(isl, segs, sources); new = max(isl["mph_out"])
            if kd == "gap":
                code, url, lab = "n", "", f"No limit of its own; {isl['name']} is posted {new} mph on both sides"
            elif kd == "single" and isl["m"] <= SINGLE_M:
                old = "/".join(str(x) for x in isl["mph_in"] if x not in (0, 99)) or "no limit"
                who = "OpenStreetMap" if "t" in isl["codes"] else "one Mapillary sign"
                k0 = next((k for k in isl["idx"] if segs[k][3] == "m" and len(segs[k]) > 8 and segs[k][8] >= 0), None)
                url = sources[segs[k0][8]][0] if k0 is not None else ""
                code, lab = "q", f"Sources disagree: {who} says {old} mph on this short stretch, but {isl['name']} is posted {new} mph on both sides. Check posted signs."
            else: continue
            si = src_i(url, lab)
            for k in isl["idx"]:
                s = segs[k]; s[2] = new; s[3] = code
                if isl["borrowed"]: s[0] = isl["nidx"]   # unnamed carriageway/piece: show the road it belongs to
                if len(s) > 8: s[8] = si
                else: s.append(si)
            changes.append({"road": isl["name"], "m": isl["m"], "at": isl["at"], "was": isl["mph_in"], "codes": isl["codes"], "now": new, "code": code, "segs": len(isl["idx"])})
        if len(changes) == n0: break
    return changes

def sync_ws(out, WOUT, WS):
    """After heal: ways whose every segment was healed count as posted for the roundabout/turn-lane passes (src 'sameroad')."""
    for wi, idxs in WOUT.items():
        if idxs and all(out[i][3] in ("n", "q") for i in idxs): WS[wi] = (max(out[i][2] for i in idxs), "sameroad")
