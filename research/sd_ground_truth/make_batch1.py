#!/usr/bin/env python3
"""Street View batch 1 (see /workspace/gcm/engineer/sd_verification_plan.md): the 70 'disagree' ways plus the
30 most-used 'one official source' arterials from segments.csv, in the volunteer sheet's column layout plus the
comparison columns (our GIS/survey value, its source + link, agree Y/N formula, resolved value) and a Summary tab.
Writes streetview-batch1.xlsx and streetview-batch1.csv next to this file."""
import csv, glob, json, math, os, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
ways = {}
for f in sorted(glob.glob(os.path.join(ROOT, "cache", "v2_tile*.json"))):
    for el in json.load(open(f)).get("elements", []):
        if el["type"] == "way" and "geometry" in el: ways[el["id"]] = el
node_names = collections.defaultdict(set)
for w in ways.values():
    n = w["tags"].get("name")
    if n and w["tags"].get("highway"):
        for q in w["geometry"]: node_names[(round(q["lat"], 6), round(q["lon"], 6))].add(n)
PFX = {"Oceanside": "OCN", "Carlsbad": "CBD", "Encinitas": "ENC", "Solana Beach": "SOL", "Del Mar": "DMR", "La Jolla": "LJA",
       "Pacific Beach / Mission Beach": "PBC", "Coronado": "COR", "Imperial Beach": "IMB"}
key = lambda q: (round(q["lat"], 6), round(q["lon"], 6))
by_node = collections.defaultdict(list)
for w0 in ways.values():
    if w0["tags"].get("highway"):
        for q in (w0["geometry"][0], w0["geometry"][-1]): by_node[key(q)].append(w0)
def cross(w, end, name, other=""):
    """Nearest differently-named road met walking outward from one end of w along same-name ways (max ~25 hops)."""
    seen = {w["id"]}; cur = w; at = cur["geometry"][0] if end == 0 else cur["geometry"][-1]
    g = w["geometry"]   # first, a cross street at the end node itself or on interior nodes near it
    for _ in range(25):
        o = sorted(node_names.get(key(at), set()) - {name} - {other})
        if o: return o[0]
        nxt = [x for x in by_node[key(at)] if x["id"] not in seen and x["tags"].get("name") == name]
        if not nxt: break
        cur = nxt[0]; seen.add(cur["id"]); cg = cur["geometry"]
        # interior nodes of the next piece can carry the cross street too
        pts = cg if key(cg[0]) == key(at) else cg[::-1]
        for q in pts[1:-1]:
            o = sorted(node_names.get(key(q), set()) - {name} - {other})
            if o: return o[0]
        at = pts[-1]
    return ""
def heading(g):
    k = max(0, len(g) // 2 - 1); a, b = g[k], g[min(k + 1, len(g) - 1)]
    return round(math.degrees(math.atan2((b["lon"] - a["lon"]) * math.cos(math.radians(a["lat"])), b["lat"] - a["lat"])) % 360)
R = list(csv.DictReader(open(os.path.join(HERE, "segments.csv"))))
nroutes = lambda r: len([x for x in r["routes"].split(";") if x.strip()])
def permissive(r):   # the map allows more than a posted-sign or OSM reading says: check these first (safety)
    m = int(r["map_mph"]) if r["map_mph"].isdigit() else 99
    return any(v.isdigit() and m != 99 and int(v) > m for v in (r["osm"], r["mapillary"], r["streetview"]))
dis = sorted([r for r in R if r["status"] == "disagree"], key=lambda r: (not permissive(r), -nroutes(r), -int(r["length_m"])))[:100]
one = sorted([r for r in R if r["status"] == "one official source" and r["highway"] not in ("residential", "service", "unclassified", "living_street")],
             key=lambda r: (-nroutes(r), -int(r["length_m"])))[:100 - len(dis)]
pick = sorted(dis + one, key=lambda r: (r["city"], r["road"], float(r["lat"])))
COLS = ["check_id", "city", "road_name", "from_cross_street", "to_cross_street", "osm_way_id", "our_speed_mph", "our_speed_source",
        "cart_legal_per_map", "street_view_link", "map_link", "posted_speed_seen_mph", "sign_location_note", "imagery_date", "confidence",
        "status", "checker_initials", "notes",
        "our_gis_survey_mph", "gis_survey_source", "source_link", "agree_YN", "resolved_mph", "why_in_batch", "routes_using", "length_m"]
rows, n = [], collections.Counter()
for r in pick:
    w = ways.get(int(r["osm_way"])); g = w["geometry"] if w else None; name = r["road"]
    n[r["city"]] += 1; mph = int(r["map_mph"]) if r["map_mph"].isdigit() else None
    lat, lon = (g[len(g) // 2]["lat"], g[len(g) // 2]["lon"]) if g else (float(r["lat"]), float(r["lon"]))
    src = "city/county" if r["official"] else ("tag" if r["osm"] else "inferred")
    rows.append({"check_id": f'{PFX.get(r["city"], "SDX")}-B1-{n[r["city"]]:03d}', "city": r["city"], "road_name": name,
                 "from_cross_street": (fc := cross(w, 0, name)) if w else "", "to_cross_street": (cross(w, 1, name, fc) or cross(w, 1, name)) if w else "",
                 "osm_way_id": r["osm_way"], "our_speed_mph": mph if mph is not None and mph != 99 else (int(r["official"]) if r["official"].isdigit() else ""), "our_speed_source": src,
                 "cart_legal_per_map": "no" if mph == 99 else "cart+LSV" if mph is not None and mph <= 25 else "LSV" if mph is not None and mph <= 35 else "no",
                 "street_view_link": f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat:.6f},{lon:.6f}&heading={heading(g) if g else 0}",
                 "map_link": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}", "status": "pending",
                 "our_gis_survey_mph": r["official"], "gis_survey_source": r["official_source"], "source_link": r["official_url"],
                 "why_in_batch": (("SAFETY: map allows more than a sign/OSM reading; " if permissive(r) else "sources disagree: ") + r["fix"]) if r["status"] == "disagree" else "one official source; most-used arterial",
                 "routes_using": nroutes(r), "length_m": r["length_m"]})
wb = Workbook(); ws = wb.active; ws.title = "Roads"; ws.append(COLS)
ci = {c: i + 1 for i, c in enumerate(COLS)}; L = lambda c: ws.cell(1, ci[c]).column_letter
for i, r in enumerate(rows, start=2):
    for c in COLS: ws.cell(i, ci[c], r.get(c, ""))
    P, S, A = f"{L('posted_speed_seen_mph')}{i}", f"{L('our_gis_survey_mph')}{i}", f"{L('agree_YN')}{i}"
    ws[A] = f'=IF(OR({P}="",{S}=""),"",IF(VALUE({P})=VALUE({S}),"Y","N"))'
    ws[f"{L('resolved_mph')}{i}"] = f'=IF({A}="Y",{S},"")'
head = Font(bold=True); fill = PatternFill("solid", fgColor="FFF4CC"); vol = PatternFill("solid", fgColor="E6FBFC")
for c in range(1, len(COLS) + 1):
    ws.cell(1, c).font = head; ws.cell(1, c).fill = vol if COLS[c - 1] in ("posted_speed_seen_mph", "sign_location_note", "imagery_date", "confidence", "status", "checker_initials", "notes") else fill
ws.freeze_panes = "D2"
dv = DataValidation(type="list", formula1='"pending,done,can\'t tell"'); ws.add_data_validation(dv); dv.add(f"{L('status')}2:{L('status')}{len(rows)+1}")
dc = DataValidation(type="list", formula1='"high,medium,low"'); ws.add_data_validation(dc); dc.add(f"{L('confidence')}2:{L('confidence')}{len(rows)+1}")
for c, wdt in {"road_name": 24, "from_cross_street": 20, "to_cross_street": 20, "street_view_link": 18, "map_link": 14, "gis_survey_source": 40, "source_link": 30, "why_in_batch": 40, "notes": 30}.items():
    ws.column_dimensions[L(c)].width = wdt
h = wb.create_sheet("How to check")
guide = open("/workspace/gcm/gtm/streetview-checker-guide.md").read().splitlines()
h.append(["Street View batch 1: the 70 roads where our sources disagree, plus the 30 busiest main roads that have only a city source. Your reading is the deciding second source."])
h.append(["Fill only the blue columns (posted_speed_seen_mph … notes). The yellow columns are ours: our_gis_survey_mph is what the city code/survey says; agree_YN and resolved_mph fill themselves."])
h.append([""])
for line in guide: h.append([line])
h.column_dimensions["A"].width = 160
s = wb.create_sheet("Summary"); N = len(rows) + 1
P, S, A, ST = L("posted_speed_seen_mph"), L("our_gis_survey_mph"), L("agree_YN"), L("status")
for k, f in [("metric", "value"), ("total roads", f"=COUNTA(Roads!A2:A{N})"), ("done", f'=COUNTIF(Roads!{ST}2:{ST}{N},"done")'),
             ("can't tell", f"=COUNTIF(Roads!{ST}2:{ST}{N},\"can't tell\")"), ("pending", f'=COUNTIF(Roads!{ST}2:{ST}{N},"pending")'),
             ("percent done", f"=IF(B2=0,0,(B3+B4)/B2)"),
             ("compared (sign read and we have a GIS/survey value)", f'=COUNTIF(Roads!{A}2:{A}{N},"Y")+COUNTIF(Roads!{A}2:{A}{N},"N")'),
             ("agreed (Y)", f'=COUNTIF(Roads!{A}2:{A}{N},"Y")'), ("disagreed (N)", f'=COUNTIF(Roads!{A}2:{A}{N},"N")'),
             ("% agreed", "=IF(B7=0,\"\",B8/B7)"),
             ("mismatched vs our map (done rows)", f"=SUMPRODUCT((Roads!{ST}2:{ST}{N}=\"done\")*(Roads!{P}2:{P}{N}<>\"\")*(Roads!{P}2:{P}{N}<>Roads!G2:G{N}))")]:
    s.append([k, f])
s["B6"].number_format = "0.0%"; s["B10"].number_format = "0.0%"; s.column_dimensions["A"].width = 55; s["A1"].font = head; s["B1"].font = head
out = os.path.join(HERE, "streetview-batch1.xlsx"); wb.save(out)
with open(os.path.join(HERE, "streetview-batch1.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=COLS); wr.writeheader(); [wr.writerow({c: r.get(c, "") for c in COLS}) for r in rows]
print(out, len(rows), dict(n), "blank cross streets:", sum(1 for r in rows if not r["from_cross_street"] or not r["to_cross_street"]))
