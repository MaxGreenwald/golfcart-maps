#!/usr/bin/env python3
"""San Diego ground truth: cross-check every road on the top-route list against independent sources.

Inputs:  research/sd_ground_truth/route_legs.json (export_routes.py), routes.json (blockers), the OSM cache, the
         official-source overrides (scripts/overrides.py), Mapillary signs (scripts/mapillary_signs.py), the
         Street View sheet export (research/sd_ground_truth/streetview.csv, optional) and research/sd_flip_hold.json.
Outputs: segments.csv / segments.md (per-segment table), accuracy.json (per-market figure),
         verified_ways.json (ways where 2 independent sources agree; build_data.py turns it into the map badge
         and fails the build if a verified way's speed ever changes).
Rule: VERIFIED = an official source (city/county code, council resolution, E&TS, ordinance) and an independent
second source (OSM maxspeed tag, a Mapillary sign, or a Street View check) give the same posted limit."""
import csv, glob, json, math, os, re, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import overrides, mapillary_signs
TODAY = os.environ.get("VERIFIED_DATE", datetime.date.today().isoformat())

# ---- the same way set build_data.py uses ----
ways = {}
for f in sorted(glob.glob(os.path.join(ROOT, "cache", "v2_tile*.json"))):
    for el in json.load(open(f)).get("elements", []):
        if el["type"] == "way" and "geometry" in el:
            el["nodes"] = [f'{q["lat"]:.7f},{q["lon"]:.7f}' for q in el["geometry"]]; ways[el["id"]] = el
def border_lat(lon): return 32.5343 + (lon + 117.1235) * 0.0367
POLY = [(-117.46, 33.27), (-117.30, 33.27), (-117.24, 33.15), (-117.19, 33.05), (-117.15, 32.95), (-117.14, 32.85), (-117.12, 32.75), (-117.06, 32.68), (-117.03, 32.60), (-117.03, 32.53), (-117.46, 32.53)]
def inpoly(x, y, P=POLY):
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
wl = [w for w in ways.values() if not any(q["lat"] < border_lat(q["lon"]) - 0.0002 for q in w["geometry"])
      and inpoly(w["geometry"][len(w["geometry"]) // 2]["lon"], w["geometry"][len(w["geometry"]) // 2]["lat"])]
ov, _ = overrides.build([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]], w["nodes"]) for w in wl])
mly, _ = mapillary_signs.match([(w["tags"], [[q["lon"], q["lat"]] for q in w["geometry"]]) for w in wl])
HOLD = {h["way"]: h for h in json.load(open(os.path.join(ROOT, "research", "sd_flip_hold.json")))} if os.path.exists(os.path.join(ROOT, "research", "sd_flip_hold.json")) else {}
def mph(v):
    m = re.match(r"\s*(\d+)", v or ""); return int(m.group(1)) if m else None
OFFICIAL = re.compile(r"docs\.sandiego\.gov|sandiego\.gov|ecode360\.com|gocodebook\.com|municipal\.codes|cityofsolanabeach|delmar\.ca\.us|imperialbeach|escribemeetings|carlsbadca\.gov|ci\.oceanside|coronado\.ca\.us|dot\.ca\.gov")
def kind(url):
    if OFFICIAL.search(url or ""): return "official"
    if "mapillary.com" in (url or ""): return "mapillary"
    if "google.com/maps" in (url or ""): return "streetview"
    return "news"
def way_key(w): return f'{w["tags"].get("name", "")}|{w["nodes"][0]}|{w["nodes"][-1]}'
def wlen(w):
    g = w["geometry"]; return sum(math.hypot((g[k+1]["lon"]-g[k]["lon"])*93500, (g[k+1]["lat"]-g[k]["lat"])*110540) for k in range(len(g)-1))
# street view checks from the volunteer sheet (optional): way_id, posted_mph
SV = {}
svp = os.path.join(HERE, "streetview.csv")
if os.path.exists(svp):
    for r in csv.DictReader(open(svp)):
        v = (r.get("street_view_mph") or r.get("posted_mph") or r.get("posted_speed_seen_mph") or "").strip()
        if r.get("status", "done").strip().lower() not in ("done", ""): continue   # 'can't tell' / 'pending' rows are not a source
        if r.get("osm_way_id") and v.isdigit(): SV[int(r["osm_way_id"])] = (int(v), r.get("street_view_link", ""))

# ---- map route legs to OSM ways ----
pt = {}
for i, w in enumerate(wl):
    for q in w["geometry"]: pt.setdefault((round(q["lon"], 5), round(q["lat"], 5)), set()).add(i)
legs = json.load(open(os.path.join(HERE, "route_legs.json"))); R = json.load(open(os.path.join(HERE, "routes.json")))
use = {}   # wi -> {"routes": set, "city": str, "shown": mph}
miss = 0
for r in legs:
    for l in r["legs"]:
        a, z = tuple(l["a"]), tuple(l["z"]); c = (pt.get(a, set()) & pt.get(z, set())) or pt.get(a, set()) | pt.get(z, set())
        c = [i for i in c if (wl[i]["tags"].get("name") or wl[i]["tags"].get("ref") or "") == l["name"]] or list(c)
        if not c: miss += 1; continue
        wi = c[0]; u = use.setdefault(wi, {"routes": set(), "city": r["city"], "shown": l["mph"], "risky": False})
        u["routes"].add(f'{r["from"]}->{r["to"]}'); u["risky"] |= l["risky"]
for b in R.get("blockers", []):
    rx = re.compile(b["name"]); bb = b["bbox"]
    for i, w in enumerate(wl):
        m = w["geometry"][len(w["geometry"]) // 2]
        if rx.search(w["tags"].get("name", "")) and bb[0] <= m["lat"] <= bb[2] and bb[1] <= m["lon"] <= bb[3]:
            use.setdefault(i, {"routes": set(), "city": "", "shown": None, "risky": True})["routes"].add("blocker: " + b["why"])
print("route legs matched to", len(use), "OSM ways;", miss, "legs unmatched")

def city_of(lat, lon):
    for nm, (s, w_, n, e) in [("Oceanside", (33.1725, -117.42, 33.30, -117.2)), ("Carlsbad", (33.082, -117.37, 33.1725, -117.2)), ("Encinitas", (33.0, -117.33, 33.082, -117.2)),
                             ("Solana Beach", (32.9815, -117.29, 33.0, -117.2)), ("Del Mar", (32.935, -117.29, 32.9815, -117.2)), ("La Jolla", (32.808, -117.30, 32.935, -117.2)),
                             ("Pacific Beach / Mission Beach", (32.755, -117.30, 32.808, -117.2)), ("Coronado", (32.62, -117.25, 32.71, -117.15)), ("Imperial Beach", (32.53, -117.25, 32.62, -117.08))]:
        if s <= lat < n and w_ <= lon < e: return nm
    return "San Diego"

def classify(src):
    """Max's rule (Oct 20 2026): a real source (city/official data, a posted sign seen in Street View or Mapillary, a survey)
    overrides OSM. OSM disagreeing alone never blocks 'verified' or makes a way 'disagree'. Real sources that conflict with
    each other stay unresolved ('disagree'). OSM still counts as the second source only when it is the ONLY other source
    (Batch 0 rule: official + OSM agree, no sign reading)."""
    off = [s for s in src if s[0] == "official"]; signs = [s for s in src if s[0] in ("mapillary", "streetview")]
    osm = [s for s in src if s[0] == "osm"]; real = off + signs; rv = {s[1] for s in real}
    if len(rv) > 1: return "disagree", "medium", off, signs + osm, real
    ind = signs if signs else osm
    if off and any(i[1] == off[0][1] for i in ind): return "verified", "high", off, ind, real
    if off: return "one official source", "medium", off, ind, real
    if len(signs) >= 2 or (signs and osm and osm[0][1] == signs[0][1]): return "OSM + imagery agree (no official source)", "medium", off, ind, real
    if signs or osm: return "one unofficial source", "low", off, ind, real
    return "no posted-limit source (state default assumed)", "low", off, ind, real

rows = []
for wi, u in use.items():
    w = wl[wi]; t = w["tags"]; g = w["geometry"]; mid = g[len(g) // 2]
    src = []   # (kind, mph, label, url)
    if mph(t.get("maxspeed")) is not None: src.append(("osm", mph(t["maxspeed"]), "OSM maxspeed tag", f"https://www.openstreetmap.org/way/{w['id']}"))
    if wi in ov: src.append((kind(ov[wi][2]), ov[wi][0], ov[wi][3], ov[wi][2]))
    if w["id"] in HOLD: h = HOLD[w["id"]]; src.append(("official", h["source_mph"], h["source"] + " (held: OSM says %d)" % h["osm_mph"], h["url"]))
    if wi in mly: src.append(("mapillary", mly[wi][0], f"Mapillary: {mly[wi][2]} sign(s)", mly[wi][1]))
    if w["id"] in SV: src.append(("streetview", SV[w["id"]][0], "Street View check (volunteer sheet)", SV[w["id"]][1]))
    status, conf, off, ind, real = classify(src)
    agree = [(o, i) for o in off for i in ind if o[1] == i[1]]
    shown = u["shown"]
    if status == "disagree" and not off:
        fix = "sources disagree (" + ", ".join(f"{i[0]} {i[1]}" for i in src) + f"); map shows {u['shown']}"
    elif status == "disagree":
        o = off[0]
        fix = (f"held blocked: city code says {o[1]}, OSM says {HOLD[w['id']]['osm_mph']}; needs Street View" if w["id"] in HOLD else
               f"map uses the official {o[1]} mph" + (" (OSM/imagery: " + ", ".join(f"{i[0]} {i[1]}" for i in ind) + ")"))
    else: fix = ""
    rows.append({"city": city_of(mid["lat"], mid["lon"]), "road": t.get("name") or t.get("ref") or "(unnamed)", "osm_way": w["id"], "highway": t.get("highway"),
                 "length_m": round(wlen(w)), "map_mph": shown, "status": status, "confidence": conf,
                 "osm": next((s[1] for s in src if s[0] == "osm"), ""), "official": next((s[1] for s in off), ""), "official_source": next((s[2] for s in off), ""), "official_url": next((s[3] for s in off), ""),
                 "mapillary": next((s[1] for s in src if s[0] == "mapillary"), ""), "streetview": next((s[1] for s in src if s[0] == "streetview"), ""),
                 "agree": "Y" if status == "verified" else ("N" if status == "disagree" else ""), "verified_mph": agree[0][0][1] if status == "verified" else "",
                 "fix": fix, "routes": "; ".join(sorted(u["routes"])), "key": way_key(w), "lat": round(mid["lat"], 5), "lon": round(mid["lon"], 5),
                 "sources": [[s[0], s[1], s[2], s[3]] for s in src]})
rows.sort(key=lambda r: (r["city"], r["road"], r["lat"]))
F = ["city", "road", "osm_way", "highway", "length_m", "map_mph", "osm", "official", "official_source", "official_url", "mapillary", "streetview", "agree", "verified_mph", "status", "confidence", "fix", "routes", "lat", "lon"]
with open(os.path.join(HERE, "segments.csv"), "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=F, extrasaction="ignore"); wr.writeheader(); wr.writerows(rows)
# named stretches (road + city) for the readable table
st = {}
for r in rows:
    k = (r["city"], r["road"]); s = st.setdefault(k, {"ways": 0, "m": 0, "vm": 0, "osm": set(), "off": set(), "mly": set(), "sv": set(), "status": set(), "fix": set(), "src": set()})
    s["ways"] += 1; s["m"] += r["length_m"]; s["vm"] += r["length_m"] if r["status"] == "verified" else 0
    for a, b in (("osm", "osm"), ("off", "official"), ("mly", "mapillary"), ("sv", "streetview")):
        if r[b] != "": s[a].add(r[b])
    s["status"].add(r["status"]); r["fix"] and s["fix"].add(r["fix"]); r["official_url"] and s["src"].add(r["official_url"])
def fmt(x): return "/".join(str(v) for v in sorted(x)) or "–"
md = [f"# Coastal San Diego ground truth: top-route segments ({TODAY})", "",
      "Rule: **verified** = an official source (city code / council resolution / engineering & traffic survey / ordinance) and an independent source (OSM maxspeed tag, Mapillary sign or Street View) give the same posted limit. Per-way detail: segments.csv.", "",
      "| City | Road | OSM ways | Length (m) | OSM | Official | Mapillary | Street View | Verified share | Status | Fix applied | Official source |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for (c, rd), s in sorted(st.items()):
    md.append(f"| {c} | {rd} | {s['ways']} | {s['m']} | {fmt(s['osm'])} | {fmt(s['off'])} | {fmt(s['mly'])} | {fmt(s['sv'])} | {round(100*s['vm']/max(1,s['m']))}% | {', '.join(sorted(s['status']))} | {'; '.join(sorted(s['fix']))[:180]} | {' '.join(f'[link]({u})' for u in sorted(s['src']))} |")
# accuracy: share of top-route road length (and ways) verified by two sources
tot_m = sum(r["length_m"] for r in rows); ver_m = sum(r["length_m"] for r in rows if r["status"] == "verified")
by = {}
for r in rows:
    b = by.setdefault(r["city"], [0, 0, 0, 0]); b[0] += 1; b[1] += r["status"] == "verified"; b[2] += r["length_m"]; b[3] += r["length_m"] if r["status"] == "verified" else 0
acc = {"market": "Coastal San Diego", "date": TODAY, "ways": len(rows), "verified_ways": sum(r["status"] == "verified" for r in rows),
       "length_m": tot_m, "verified_length_m": ver_m, "share_verified_by_length": round(ver_m / max(1, tot_m), 3),
       "share_verified_by_ways": round(sum(r["status"] == "verified" for r in rows) / max(1, len(rows)), 3),
       "share_two_sources_any_kind_by_length": round(sum(r["length_m"] for r in rows if r["status"] in ("verified", "OSM + imagery agree (no official source)")) / max(1, tot_m), 3),
       "disagreements": sum(r["status"] == "disagree" for r in rows), "held_blocked": sum(1 for r in rows if r["fix"].startswith("held")),
       "by_status": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})},
       "by_city": {c: {"ways": v[0], "verified_ways": v[1], "share_by_length": round(v[3] / max(1, v[2]), 3)} for c, v in sorted(by.items())}}
json.dump(acc, open(os.path.join(HERE, "accuracy.json"), "w"), indent=1)
md[1:1] = ["", f"**Accuracy figure: {round(100*acc['share_verified_by_length'])}% of top-route road length ({acc['verified_ways']} of {acc['ways']} OSM ways) verified by two agreeing sources.** {acc['disagreements']} disagreements ({acc['held_blocked']} held blocked for a Street View check)."]
open(os.path.join(HERE, "segments.md"), "w").write("\n".join(md) + "\n")
ver = {r["key"]: {"mph": r["verified_mph"], "date": TODAY, "sources": [s for s in r["sources"] if s[1] == r["verified_mph"] and s[0] != "news"]} for r in rows if r["status"] == "verified"}
json.dump({"date": TODAY, "rule": "official source + independent source agree; a real source (official, sign photo, survey) overrides OSM (Max, Oct 20 2026)", "accuracy": {"share_by_length": acc["share_verified_by_length"], "ways": acc["ways"], "verified_ways": acc["verified_ways"]}, "ways": ver},
          open(os.path.join(HERE, "verified_ways.json"), "w"), indent=0)
print(json.dumps({k: v for k, v in acc.items() if k != "by_city"}, indent=1)); print(json.dumps(acc["by_city"], indent=1))
