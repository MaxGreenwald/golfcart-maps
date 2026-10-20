#!/usr/bin/env python3
"""Street View batch 2 (1000 stretches, all regions, San Diego first). Same Roads columns as batch 1 plus region + gcm_ref.
Priority: (A) same-road red islands not checked by a person (scripts/islands.py), (B) coastal-SD ground-truth ways not in
batch 1 (disagree > one official > one unofficial > no source; arterials first), (C) unverified limits (OSM tag, inferred,
one Mapillary sign) at the cart/LSV thresholds (25/30 and 35/40 mph) or unknown limits on main roads, most-used road classes
and longest first, region weight SD > Villages > the rest. One row per stretch (connected run of one named road with one
limit + source). Usage: make_batch2.py DATA_DIR SCRIPTS_DIR (defaults: master tree public/data, scripts)."""
import csv, glob, json, math, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "public", "data")
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "scripts")); import islands
N_TOTAL = 1000
REG = {r["id"]: r for r in json.load(open(os.path.join(DATA, "regions.json")))}
AP = next((q for q in (os.path.join(DATA, "..", "..", "research", "red_island_allowlist.json"), os.path.join(ROOT, "research", "red_island_allowlist.json")) if os.path.exists(q)), None)
ALLOW = json.load(open(AP))["islands"] if AP else []
B1 = list(csv.DictReader(open(os.path.join(HERE, "streetview.csv"))))
B1_WAYS = {r["osm_way_id"] for r in B1}
B1_PTS = [tuple(map(float, r["street_view_link"].split("viewpoint=")[1].split("&")[0].split(","))) for r in B1]
GT = {r["osm_way"]: r for r in csv.DictReader(open(os.path.join(HERE, "segments.csv")))}
# SD: OSM way id by node coordinate (cache/v2_tile*.json, the build input)
NODE_WAY = {}
for f in glob.glob(os.path.join(ROOT, "cache", "v2_tile*.json")):
    for el in json.load(open(f)).get("elements", []):
        if el["type"] == "way" and "geometry" in el and el["tags"].get("highway"):
            for q in el["geometry"][1:-1] or el["geometry"]: NODE_WAY.setdefault((round(q["lat"], 5), round(q["lon"], 5)), el["id"])
UNVER = set("itm")   # OSM tag only / inferred / Mapillary
MAIN = ("primary", "secondary", "tertiary", "unclassified", "residential")
RW = lambda rid: 3.0 if rid == "sd" else 2.0 if rid == "villages" else 1.0
def L(p): return sum(math.hypot((p[k+1][0]-p[k][0]) * 111320 * math.cos(math.radians(p[k][1])), (p[k+1][1]-p[k][1]) * 110540) for k in range(len(p)-1))
def hd(p):
    k = max(0, len(p)//2 - 1); a, b = p[k], p[min(k+1, len(p)-1)]
    return round(math.degrees(math.atan2((b[0]-a[0]) * math.cos(math.radians(a[1])), b[1]-a[1])) % 360)
def near_b1(lat, lon): return any(abs(lat-a) < 0.0006 and abs(lon-b) < 0.0007 for a, b in B1_PTS)
cands = []
for rid in REG:
    idx = json.load(open(os.path.join(DATA, rid, "index.json"))); names, sources = idx["names"], idx.get("sources", [])
    segs = [s for t in idx["meta"]["tiles"] for s in json.load(open(os.path.join(DATA, rid, "tiles", t + ".json")))]
    bynode = collections.defaultdict(list)
    for i, s in enumerate(segs):
        for n in (s[5], s[6]): bynode[n].append(i)
    def cross(nodes, nm):
        for n in nodes:
            o = sorted({names[segs[j][0]] for j in bynode[n] if names[segs[j][0]] and segs[j][0] != nm})
            if o: return o[0]
        return ""
    used = set()
    def stretch(comp, tier, score, why, nm=None):
        nm = segs[comp[0]][0] if nm is None else nm
        C = set(comp); ends = [n for k in comp for n in (segs[k][5], segs[k][6]) if any(j not in C for j in bynode[n])]
        mid = max(comp, key=lambda k: L(segs[k][7])); p = segs[mid][7]; lon, lat = p[len(p)//2]
        if p and len(p) == 2: lon, lat = (p[0][0]+p[1][0])/2, (p[0][1]+p[1][1])/2
        s = segs[mid]; src = sources[s[8]] if len(s) > 8 and isinstance(s[8], int) and 0 <= s[8] < len(sources) else None
        way = ""
        if rid == "sd":
            for q in p: way = way or str(NODE_WAY.get((round(q[1], 5), round(q[0], 5)), ""))
        if way in B1_WAYS or near_b1(lat, lon): return
        used.update(C); fc = cross(ends[:1], nm); tc = cross(ends[1:][::-1], nm) if len(ends) > 1 else ""
        fc = fc or "(see map link)"; tc = tc or "(see map link)"
        if tc == fc: tc = cross([e for e in ends[1:] if cross([e], nm) != fc], nm) or tc
        mph = s[2] if s[2] not in (None, 99) else ""
        g = GT.get(way, {})
        cands.append({"tier": tier, "score": score, "region": rid, "city": g.get("city") or ("San Diego area" if rid == "sd" else REG[rid]["name"]), "road_name": names[nm],
            "from_cross_street": fc, "to_cross_street": tc, "osm_way_id": way, "our_speed_mph": mph,
            "our_speed_source": {"t": "tag", "i": "inferred", "m": "mapillary", "v": "city/county", "q": "sources disagree", "n": "same road"}.get(s[3], s[3]),
            "cart_legal_per_map": "no" if mph == "" else "cart+LSV" if mph <= 25 else "LSV" if mph <= 35 else "no",
            "street_view_link": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}&heading={hd(p)}",
            "map_link": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}", "status": "pending",
            "our_gis_survey_mph": g.get("official", ""), "gis_survey_source": g.get("official_source", "") or (src[1] if src else ""),
            "source_link": g.get("official_url", "") or (src[0] if src else ""), "why_in_batch": why,
            "routes_using": len([x for x in g.get("routes", "").split(";") if x.strip()]) if g else "", "length_m": round(sum(L(segs[k][7]) for k in comp)),
            "gcm_ref": f"{rid}|{lat:.5f},{lon:.5f}"})
    # A: red islands
    ok = {(a["region"], a["road"], round(a["at"][0], 2), round(a["at"][1], 2)) for a in ALLOW if a["status"] == "real"}
    for isl in islands.find(segs, names):
        if (rid, isl["name"], round(isl["at"][0], 2), round(isl["at"][1], 2)) in ok: continue
        kd = islands.kind(isl, segs, sources)
        stretch(isl["idx"], 0, RW(rid) * (3 if kd != "confirmed" else 1),
                f"RED ISLAND: {isl['m']} m of {isl['name']} at {'/'.join(str(x) + ' mph' for x in isl['mph_in'] if x not in (0, 99)) or 'no limit'} between {'/'.join(map(str, isl['mph_out']))} mph on both sides ({kd}); is the posted limit really higher here?", isl["nidx"])
    # B + C: walk named runs with one limit + code
    for i0, s0 in enumerate(segs):
        if i0 in used or not names[s0[0]] or not s0[1].startswith(MAIN) or s0[1].endswith("_link"): continue
        comp, st, seen = [], [i0], {i0}
        while st:
            k = st.pop(); comp.append(k)
            for n in (segs[k][5], segs[k][6]):
                for j in bynode[n]:
                    if j not in seen and j not in used and segs[j][0] == s0[0] and segs[j][2] == s0[2] and segs[j][3] == s0[3]: seen.add(j); st.append(j)
        m = sum(L(segs[k][7]) for k in comp); mph, code, hw = s0[2], s0[3], s0[1]
        if m < 80: used.update(comp); continue
        if code not in UNVER: used.update(comp); continue
        main = hw.startswith(("primary", "secondary", "tertiary"))
        thr = mph in (25, 30, 35, 40)
        if hw == "residential" and not (code in "tm" and mph in (30, 35, 40)): used.update(comp); continue   # residential: only a posted 30-40 claim matters
        if not thr and not (main and mph in (None, 99, 45)): used.update(comp); continue
        cls = {"primary": 3, "secondary": 2.5, "tertiary": 2, "unclassified": 1.2, "residential": 1}[hw.split("_")[0]]
        side = "is it 25 (carts OK) or 30+?" if mph in (25, 30) else "is it 35 (LSV OK) or 40+?" if mph in (35, 40) else "main road: what is posted? 35 or lower opens it to LSVs"
        srcw = {"i": 1.3, "t": 1.0, "m": 0.8}[code]
        score = RW(rid) * cls * srcw * min(m, 1500) / 100
        why = f"unverified: map has {str(mph) + ' mph' if mph not in (None, 99) else 'no limit'} ({ {'i': 'guessed from road type', 't': 'OSM tag only', 'm': 'one Mapillary sign'}[code] }); {side}"
        stretch(comp, 1, score, why)
cands.sort(key=lambda r: (r["tier"], -r["score"]))
# SD first: islands everywhere, then the SD quota, then the rest by score
pick = [r for r in cands if r["tier"] == 0][:300]
rest = [r for r in cands if r["tier"] == 1]
sd = [r for r in rest if r["region"] == "sd"][:450]
pick += sd; pick += [r for r in rest if r not in sd][:N_TOTAL - len(pick)]
pick = pick[:N_TOTAL]
pick.sort(key=lambda r: (r["region"] != "sd", r["region"], r["tier"], -r["score"]))
cnt = collections.Counter()
for r in pick:
    cnt[r["region"]] += 1; r["check_id"] = f'{r["region"].upper()}-B2-{cnt[r["region"]]:03d}'
COLS = ["check_id", "city", "road_name", "from_cross_street", "to_cross_street", "osm_way_id", "our_speed_mph", "our_speed_source",
        "cart_legal_per_map", "street_view_link", "map_link", "posted_speed_seen_mph", "sign_location_note", "imagery_date", "confidence",
        "status", "checker_initials", "notes", "our_gis_survey_mph", "gis_survey_source", "source_link", "agree_YN", "resolved_mph",
        "why_in_batch", "routes_using", "length_m", "region", "gcm_ref"]
with open(os.path.join(HERE, "streetview-batch2.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader(); [w.writerow(r) for r in pick]
print(len(pick), "islands", sum(r["tier"] == 0 for r in pick), dict(cnt.most_common()), "blank cross:", sum(1 for r in pick if not r["from_cross_street"] or not r["to_cross_street"]))
