#!/usr/bin/env python3
"""Healdsburg, CA (Sonoma County). Idempotent upsert into public/data/regions.json, research/regions/healdsburg.json,
research/access_sources.json, and research/validation_baseline.json.

No Healdsburg golf cart transportation plan (CVC 21115 / Sts. & Hwys. Code 1950) or NEV plan (Sts. & Hwys. Code 1963)
was found, so the California state caps apply: CVC 21716 (golf carts, 25 mph or less in a business or residence
district) and CVC 21260 (LSVs, 35 mph or less). Road speeds inside the city come from Healdsburg Municipal Code
Chapter 10.50 (speed_names below, scoped to the city limits in research/city_limits/healdsburg.json).
Every street that chapter lists is posted 35 mph or less. US 101 is the one ban."""
import json, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
def W(p, d, indent=1):
    fp = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    json.dump(d, open(fp, "w"), indent=indent, ensure_ascii=False)
    open(fp, "a").write("\n")
DAY = "2026-11-22"
RID = "healdsburg"
CVC = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum="
HMC1050 = "https://ecode360.com/47365641"
HMCT10 = "https://ecode360.com/47365398"
BBOX = [38.59, -122.89, 38.652, -122.84]
ROADS = "^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)(_link)?$"

def rect(s, w, n, e): return [[w, s], [e, s], [e, n], [w, n], [w, s]]

def city_poly(tol=0.0002):
    """The city limits ring (research/city_limits/healdsburg.json), simplified. The map clips to it, so unposted
    county wine roads outside town (West Dry Creek Road, Los Amigos Road and others) are not drawn as 25 mph."""
    gj = J("research/city_limits/healdsburg.json")["geojson"]
    ring = gj["coordinates"][0] if gj["type"] == "Polygon" else max((p[0] for p in gj["coordinates"]), key=len)
    def dp(pts):
        if len(pts) < 3: return pts
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1; n = (dx * dx + dy * dy) ** 0.5 or 1e-12
        far, i = max((abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n, k) for k, (x, y) in enumerate(pts))
        return dp(pts[:i + 1])[:-1] + dp(pts[i:]) if far > tol else [pts[0], pts[-1]]
    pts = [[round(x, 5), round(y, 5)] for x, y in ring[:-1]]
    k = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    out = dp(pts[:k + 1])[:-1] + dp(pts[k:] + [pts[0]])
    return out
def src(label, url): return {"label": label, "url": url}

# Healdsburg Municipal Code 10.50.050 (engineering and traffic survey speed limits), 10.50.010 (alleys, 15 mph)
# and 10.50.060 (Healdsburg Avenue bridge, 15 mph). Each entry: street regex, mph, the code's segment text,
# and an optional box [S, W, N, E] that holds that segment. Inside the city limits only.
SEG = []
def seg(names, mph, text, box=None):
    SEG.append((names, mph, text, box))

from healdsburg_segments import SEGMENTS   # noqa: E402  (research/healdsburg_segments.py)
for s in SEGMENTS: seg(*s)

def speed_names():
    out = []
    for names, mph, text, box in SEG:
        o = {"names": names, "mph": mph, "url": HMC1050,
             "label": f"Healdsburg Municipal Code 10.50: {text} {mph} mph", "highway": ROADS,
             "poly": "healdsburg.json"}
        if box: o["bbox"] = box
        out.append(o)
    return out

REGION = {"id": RID, "name": "Healdsburg, CA", "short": "Healdsburg", "state": "CA", "center": [38.6105, -122.8692], "zoom": 14,
          "bbox": BBOX, "cover": "Healdsburg, California (Sonoma County), inside the city limits. The county wine roads outside town are not on this map. Pick another city in the menu above.",
          "slug": RID}   # beta flag follows the v3 bar (scripts/apply_beta_bar.py)
ENF = [src("CVC 21716", CVC + "21716"), src("CVC 21260", CVC + "21260"),
       src("Healdsburg Municipal Code Chapter 10.50 (speed limits)", HMC1050),
       src("Healdsburg Municipal Code Title 10 (no golf cart or LSV chapter)", HMCT10)]
CFG = {"poly": city_poly(),
       "bans": [{"names": r"^(US 101|U\.S\. 101|Redwood Highway)$|(^|;)US 101($|;)", "url": CVC + "21260",
                 "label": "US 101 is a freeway posted well above 35 mph (no golf carts or LSVs)"}],
       "unverified": ["No city golf cart or NEV transportation plan was found, so the California state speed caps apply.",
                      "Street speeds inside the city limits follow Healdsburg Municipal Code Chapter 10.50. The map is clipped to the city limits, so unposted Sonoma County roads outside town are not drawn. A road that crosses the line keeps its outside piece, using OpenStreetMap and federal speed data; an unposted secondary road there stays red.",
                      "The Healdsburg Avenue Memorial Bridge is posted 15 mph (HMC 10.50.060). It is drawn at 30 mph with its east approach, so plain golf carts see it red. That is stricter than the sign.",
                      "Kinley Drive (35 mph in HMC 10.50.050) and the Magnolia Drive area west of US 101 are outside the OpenStreetMap city line, so they are not drawn.",
                      "Where Healdsburg Avenue meets Old Redwood Highway at the southern city limit, a short piece picks up the federal US 101 speed (70 mph) and stays red. The city code posts that end of Healdsburg Avenue at 35 mph."],
       "speed_names": speed_names(),
       "sources": [f'{x["label"]} {x["url"]}' for x in ENF] + ["OpenStreetMap", "FHWA HPMS speed limits"],
       "enforcement": {"checked": DAY, "result": "bans_applied", "sources": ENF,
                       "note": "Posted signs do not lift a ban. No Healdsburg ordinance bans golf carts or LSVs from a named street; US 101 is closed by the state speed cap."},
       "status": f"Added (healdsburg, {DAY})"}
STATE_LAW = {"text": "state law, no local ordinance found",
             "law": "CVC 21716 (golf carts on highways posted 25 mph or less in a business or residence district) and CVC 21260 (LSVs on roads posted 35 mph or less). No Healdsburg golf cart or NEV transportation plan was found. City street speeds are from Healdsburg Municipal Code Chapter 10.50.",
             "law_url": CVC + "21716",
             "searched": "Healdsburg Municipal Code Title 10 index (https://ecode360.com/47365398), Chapter 10.36 and Chapter 12.04, and web search 'Healdsburg golf cart ordinance', 'Healdsburg neighborhood electric vehicle' and 'Healdsburg low-speed vehicle'."}

def main():
    regs = [r for r in J("public/data/regions.json") if r["id"] != RID]
    for r in regs:
        b = r["bbox"]
        assert not (BBOX[0] < b[2] and b[0] < BBOX[2] and BBOX[1] < b[3] and b[1] < BBOX[3]), r["id"]
    W("public/data/regions.json", regs + [REGION])
    W(f"research/regions/{RID}.json", CFG)
    acc = J("research/access_sources.json"); acc["state_law"][RID] = STATE_LAW; acc["regions"].pop(RID, None)
    W("research/access_sources.json", acc)
    vb = J("research/validation_baseline.json"); vb["red_islands"].setdefault(RID, 0)
    W("research/validation_baseline.json", vb)
    print(len(regs) + 1, "regions;", len(CFG["speed_names"]), "speed_names")

if __name__ == "__main__":
    main()
