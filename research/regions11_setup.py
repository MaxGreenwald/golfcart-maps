#!/usr/bin/env python3
"""Greenwich + next 10 (Max, Oct 28 2026: "add greenwich ct and the next 10 cities to the map").
Idempotent upsert into public/data/regions.json, public/data/rules.json (CT),
research/regions/<id>.json, research/access_sources.json, research/validation_baseline.json and
content/region_resources.json. Rerun after a rebase to resolve conflicts in those shared files.
Ranking and why: research/regions11_ranking_2026-10-28.md. Polys: research/regions11_polys/<id>.json.
Sarasota / Lido / Longboat is skipped: it sits inside the live siesta bbox. Cocoa Beach replaces it.
"""
import json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
def W(p, d, indent=1):
    fp = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    json.dump(d, open(fp, "w"), indent=indent, ensure_ascii=False)
    open(fp, "a").write("\n")
DAY = "2026-10-28"
FLS = "https://www.flsenate.gov/Laws/Statutes/2025/"
FL2122 = "https://www.flsenate.gov/Laws/Statutes/2025/316.2122"
FL212 = "https://www.flsenate.gov/Laws/Statutes/2025/316.212"
FLHSMV = "https://www.flhsmv.gov/safety-center/consumer-education/low-speed-vehicles/"
CTLSV = "https://www.cga.ct.gov/current/pub/chap_248.htm#sec_14-289m"
CTGC = "https://www.cga.ct.gov/current/pub/chap_249.htm#sec_14-300g"
OCGA = "https://law.justia.com/codes/georgia/title-40/chapter-6/article-13/part-3/section-40-6-331/"
OCGA_LSV = "https://law.justia.com/codes/georgia/title-40/chapter-6/article-13/part-6/section-40-6-362/"

STATES = {
 "CT": {"name": "Connecticut",
        "lsv": {"max_posted": 25, "cross": True, "who": "street-legal LSVs",
                "note": "A town traffic authority or the Office of State Traffic Administration can prohibit LSVs on a road under its control",
                "cite": "Conn. Gen. Stat. Sec. 14-289m (P.A. 24-20, effective Oct. 1, 2024): LSVs on highways with an established speed limit of 25 mph or less, unless the local traffic authority or OSTA prohibits them",
                "url": CTLSV},
        "golf_cart": {"not_street_legal": True, "max_posted": 0, "cross": False,
                      "note": "Plain golf carts are not street-legal unless that town's traffic authority permits them. Switch to LSV if yours is registered.",
                      "cite": "Conn. Gen. Stat. Sec. 14-300g: a traffic authority may permit golf carts in daylight only, on roads posted 25 mph or less, with a horn, flag, and a licensed driver",
                      "url": CTGC}},
}

def rect(s, w, n, e): return [[w, s], [e, s], [e, n], [w, n], [w, s]]
def poly_path(rid): return os.path.join(ROOT, "research/regions11_polys", rid + ".json")
def poly(rid):
    p = poly_path(rid)
    return json.load(open(p)) if os.path.exists(p) else None
def src(label, url): return {"label": label, "url": url}
def boxes_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

# ---------------------------------------------------------------- the 11 regions (ranked order)
R = []
def add(**k): R.append(k)

# Match a state-route ref even when OSM joins several refs with a semicolon ("GA 85;GA 92", "I 20;US 278").
HW = r"(^|;)((I[- ]?\d+)|(Interstate \d+)|(US \d+[A-Z]?)|(GA \d+)|(SR \d+)|(State (Route|Road|Highway) \d+))($|;| )"
CR = r"^(CR \d+[A-Z]?|County Road \d+[A-Z]?)$"

add(id="greenwich", name="Greenwich, CT", short="Greenwich", state="CT", slug="greenwich",
    bbox=[41.00, -73.66, 41.12, -73.57], zoom=13,
    cover="Greenwich, Connecticut only. Pick another city in the menu above.",
    bans=[{"names": r"(^|;)I[- ]?95($|;)|^Merritt Parkway$|(^|;)CT 15($|;)", "url": CTLSV,
           "label": "I-95 and the Merritt Parkway (CT 15) are limited-access highways posted well above 25 mph (no LSVs)"}],
    state_law=dict(text="state law, no local ordinance found",
                   law="Conn. Gen. Stat. Sec. 14-289m (LSVs on roads posted 25 mph or less unless the traffic authority or OSTA prohibits them) and Sec. 14-300g (golf carts only where the town traffic authority permits them). Greenwich's Board of Selectmen, acting as traffic authority, has not permitted golf carts.",
                   law_url=CTLSV,
                   searched="Town of Greenwich charter and code index; Board of Selectmen traffic-ordinance packets (2025-2026); web search 'Greenwich CT golf cart ordinance' and 'Greenwich CT low-speed vehicle'. The Greenwich, Ohio golf-cart chapter is a different town."),
    enf=[src("Conn. Gen. Stat. Sec. 14-289m (LSVs)", CTLSV), src("Conn. Gen. Stat. Sec. 14-300g (golf carts)", CTGC)],
    unverified=["No Greenwich list of LSV-prohibited roads was found, so only the state 25 mph cap and the I-95 / Merritt Parkway ban are applied. Untagged residential streets are assumed 25 mph."],
    towns=[("greenwich", "Greenwich", 41.0262, -73.6282)],
    res=[("Connecticut lets registered LSVs use roads posted 25 mph or less unless a traffic authority closes the road.", "Connecticut LSV law, Sec. 14-289m", CTLSV)])

TYR = "https://tyronega.gov/paths"
add(id="tyrone", name="Tyrone, GA", short="Tyrone", state="GA", slug="tyrone",
    bbox=[33.461, -84.63, 33.515, -84.55], zoom=14,
    cover="Tyrone, Georgia only (north of Peachtree City). Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "designated_only": True, "cross": True,
                        "note": "Town permit. The designated street list is not digitized, so plain carts show on tagged paths only.",
                        "cite": "Town of Tyrone: golf carts on designated streets posted 35 mph or less, and on paved multi-use paths (Chapter 36, Article III). Highway 74 is not a cart route.",
                        "url": TYR}},
    bans=[], cart_only=[{"names": r"^(GA 74|SR 74|State Route 74|Highway 74|Joel Cowan Parkway)$", "url": TYR,
                         "label": "Town of Tyrone: Highway 74 is not a golf cart route (designated streets and paths only)"}],
    access=dict(kind="town paths page (designated streets not digitized)", url=TYR,
                label="Town of Tyrone: carts on designated streets posted 35 mph or less and on multi-use paths",
                applied="public/data/regions.json rule.golf_cart (designated only, 35 mph) + research/regions/tyrone.json cart_only_bans"),
    enf=[src("Town of Tyrone multi-use paths and golf carts", TYR), src("O.C.G.A. 40-6-331", OCGA)],
    unverified=["Tyrone's designated street list is not digitized. The town site says most streets posted 35 mph or less are share-the-road; until that list is drawn, plain golf carts show red except tagged cart paths."],
    towns=[("tyrone", "Tyrone", 33.4715, -84.5916)],
    res=[("Tyrone publishes where golf carts may use paths and share-the-road streets.", "Tyrone multi-use paths and golf carts", TYR)])

FAY = "https://www.fayetteville-ga.gov/413/Permits-Licenses"
FAYCODE = "https://library.municode.com/ga/fayetteville/codes/code_of_ordinances?nodeId=PTIICOOR_CH82TRVE_ARTIXMOCA_S82-260DE"
add(id="fayetteville", name="Fayetteville, GA", short="Fayetteville", state="GA", slug="fayetteville",
    bbox=[33.40, -84.499, 33.52, -84.40], zoom=13,
    cover="Fayetteville, Georgia only (east of Peachtree City). Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "designated_only": True, "cross": True,
                        "note": "City permit. Authorized streets are not digitized, so plain carts show on tagged paths only.",
                        "cite": "City of Fayetteville Code Sec. 82-262: motorized carts only on authorized streets and recreation paths, not on major or collector streets except approved crossings",
                        "url": FAYCODE}},
    bans=[], cart_only=[{"names": r"(^|;)GA (54|85|92|314)($|;)|^Glynn Street|^Stonewall Avenue|^Jimmie Mayfield Boulevard|^Highway 54|^State Route (85|92)|^East Lanier Avenue|^West Lanier Avenue",
                         "url": FAYCODE,
                         "label": "City of Fayetteville Sec. 82-262: no motorized carts on major or collector streets (GA 54, GA 85, GA 92, Glynn Street, Lanier Avenue, Stonewall Avenue) except approved crossings"}],
    access=dict(kind="city code (authorized streets not digitized)", url=FAYCODE,
                label="Fayetteville Code Sec. 82-260 to 82-262 (motorized carts on authorized streets and paths)",
                applied="public/data/regions.json rule.golf_cart (designated only) + research/regions/fayetteville.json cart_only_bans"),
    enf=[src("Fayetteville motorized cart permits", FAY), src("Fayetteville Code Sec. 82-262", FAYCODE)],
    unverified=["The city's authorized-street list is not digitized. Plain golf carts show red except tagged cart paths. Major-road names above are banned for carts even if a path tag is missing."],
    towns=[("fayetteville", "Fayetteville", 33.4487, -84.4549)],
    res=[("Fayetteville explains motorized cart permits and the streets carts may use.", "Fayetteville motorized cart permits", FAY)])

SEN = "https://library.municode.com/ga/senoia/codes/code_of_ordinances?nodeId=COOR_CH66TRVE"
add(id="senoia", name="Senoia, GA", short="Senoia", state="GA", slug="senoia",
    bbox=[33.27, -84.62, 33.329, -84.50], zoom=14,
    cover="Senoia, Georgia only (south of Peachtree City). Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True,
                        "cite": "Senoia Code Sec. 66-103: motorized carts on streets posted 35 mph or less; not on State Highway 85 or 16 except authorized crossings",
                        "url": SEN}},
    bans=[], cart_only=[{"names": r"(^|;)GA (16|85)($|;)|^Wells Street$|^State Route (16|85)|^Highway 85 Connector", "url": SEN,
                         "label": "Senoia Code Sec. 66-103: no motorized carts on State Highway 16 (Wells Street) or State Highway 85 except authorized crossings"}],
    access=dict(kind="city code (named highways)", url=SEN,
                label="Senoia Code Ch. 66: carts on streets posted 35 mph or less, not SR 16 or SR 85",
                applied="public/data/regions.json rule.golf_cart (35 mph) + research/regions/senoia.json cart_only_bans"),
    enf=[src("Senoia Code Chapter 66", SEN), src("Senoia Police golf cart registration", "https://senoiapd.com/golf-cart-lsmv-registration/")],
    unverified=["State Route 16 is tagged Wells Street in OpenStreetMap. Broad Street is a separate 25 mph city street and is not part of this ban."],
    towns=[("senoia", "Senoia", 33.3018, -84.5534)],
    res=[("Senoia's city code sets where motorized carts may drive.", "Senoia traffic code, golf carts", SEN)])

CON = "https://www.conyersga.com/residents/golf-cart-district"
add(id="conyers", name="Conyers, GA", short="Conyers", state="GA", slug="conyers",
    bbox=[33.63, -84.07, 33.71, -83.96], zoom=13,
    cover="Conyers, Georgia only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "designated_only": True, "cross": True,
                        "note": "The motorized cart district map is not digitized, so plain carts show on tagged paths only.",
                        "cite": "City of Conyers Ord. 962 (2014), Title 10 Chapter 4: motorized carts only on designated public roads inside the cart district",
                        "url": CON}},
    bans=[{"names": r"(^|;)I[- ]?20($|;)|^Purple Heart Highway$", "url": CON,
           "label": "Interstate 20 (Purple Heart Highway) through Conyers is a freeway posted well above 35 mph (no carts or LSVs)"}],
    access=dict(kind="city district page (street list not digitized)", url=CON,
                label="City of Conyers golf cart district (designated roads; map not digitized)",
                applied="public/data/regions.json rule.golf_cart (designated only)"),
    enf=[src("City of Conyers golf cart district", CON), src("O.C.G.A. 40-6-331", OCGA)],
    unverified=["Conyers publishes a district map, not a street list we could digitize. Plain golf carts show red except tagged cart paths."],
    towns=[("conyers", "Conyers", 33.6676, -84.0177)],
    res=[("Conyers describes its motorized cart district and registration.", "Conyers golf cart district", CON)])

AUG = "https://www.augustaga.gov/DocumentCenter/View/11417/PERSONAL-TRANSPORTATION-VEHICLE--APPLICATION-PTV"
AUGORD = "https://library.municode.com/ga/augusta-richmond_county/ordinances/code_of_ordinances?nodeId=1416145"
add(id="augusta", name="Augusta, GA", short="Augusta", state="GA", slug="augusta",
    bbox=[33.45, -82.10, 33.52, -81.94], zoom=13,
    cover="Augusta's PTV area (downtown and the named west-side streets) only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "designated_only": True, "cross": True, "daylight_only": True,
                        "note": "Permit required. Downtown streets that are not in the named allow-list stay red.",
                        "cite": "Augusta Code Sec. 3-5-86 (Ord. 7850): PTVs only on listed streets and inside the downtown area, daylight for private carts",
                        "url": AUG}},
    designated=[{"names": ["J Dewey Gray Circle", "J. Dewey Gray Circle", "Dewey Gray Circle", "Wainbrook Drive", "Wainbrook",
                           "Devore Place", "Interstate Parkway", "Heath Drive", "Pine Needle Road"],
                 "bbox": [33.45, -82.10, 33.52, -81.94], "url": AUG,
                 "label": "Augusta PTV list: J. Dewey Gray Circle, Wainbrook, Devore Place, Interstate Parkway between Wainbrook and Devore, Heath Drive, and Pine Needle Road"}],
    bans=[{"names": r"^(I-20|I 20|Interstate 20|I-520|I 520|Interstate 520)$", "url": AUG,
           "label": "Interstates in Augusta are freeways posted well above 35 mph (no carts or LSVs)"}],
    cart_only=[{"names": r"^(John C Calhoun Expressway|Calhoun Expressway|15th Street|St\.? Sebastian Way|Saint Sebastian Way|13th Street|R\.? ?A\.? Dent Boulevard|RA Dent Boulevard|Walton Way|Laney Walker Boulevard|Gordon Highway|East Boundary Street|Reynolds Street|Jones Street)$",
                "bbox": [33.45, -82.00, 33.50, -81.94], "url": AUG,
                "label": "Augusta PTV ordinance: these downtown streets are not PTV routes (Reynolds and Jones only between 15th and 13th; the whole downtown stretch is shown red to be safe)"}],
    access=dict(kind="city PTV sheet (named streets)", url=AUG,
                label="Augusta PTV requirements: named streets plus downtown, with a banned-street list",
                applied="research/regions/augusta.json designated_names + cart_only_bans; downtown side streets not in the named list stay red"),
    enf=[src("Augusta PTV requirements", AUG), src("Augusta Ord. 7850", AUGORD), src("O.C.G.A. 40-6-331", OCGA)],
    unverified=["The ordinance allows every street inside the downtown boundary except the named bans. Those extra downtown streets are not digitized, so they stay red. Reynolds and Jones are red for their whole downtown stretch, not only between 15th and 13th."],
    towns=[("augusta", "Augusta", 33.476, -81.975)],
    res=[("Augusta lists the streets where a permitted PTV may drive.", "Augusta personal transportation vehicle rules", AUG)])

EUH = "https://euharlee.com/wp-content/uploads/2024/04/Ordinance-2025-03-Golf-Cart-Amended-5-6-2025-1.pdf"
add(id="euharlee", name="Euharlee, GA", short="Euharlee", state="GA", slug="euharlee",
    bbox=[34.12, -84.98, 34.18, -84.90], zoom=14,
    cover="Euharlee, Georgia only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 25, "cross": True,
                        "note": "Sunrise to sunset unless the cart has headlights and taillights.",
                        "cite": "Euharlee Ord. 2025-03: golf carts on public streets posted 25 mph or less; not on state or county highways except to cross at a designated intersection",
                        "url": EUH}},
    bans=[], cart_only=[{"names": HW, "url": EUH, "label": "Euharlee Ord. 2025-03: no golf carts on state highways except to cross"},
                        {"names": CR, "url": EUH, "label": "Euharlee Ord. 2025-03: no golf carts on county roads except to cross"},
                        {"names": r"^Euharlee Road( Southwest)?$", "url": EUH, "label": "Euharlee Road is the state highway through town (GA 113); carts may cross, not drive along it"}],
    access=dict(kind="city ordinance", url=EUH, label="Euharlee Ord. 2025-03 golf carts and low-speed vehicles",
                applied="public/data/regions.json rule.golf_cart (25 mph) + research/regions/euharlee.json cart_only_bans"),
    enf=[src("Euharlee Ordinance 2025-03", EUH), src("O.C.G.A. 40-6-362", OCGA_LSV)],
    unverified=["County roads that are not tagged CR or County Road in OpenStreetMap are not in the ban regex. State route refs are."],
    towns=[("euharlee", "Euharlee", 34.1465, -84.933)],
    res=[("Euharlee's 2025 ordinance sets golf cart and LSV street rules.", "Euharlee golf cart ordinance 2025-03", EUH)])

STM = "https://cms3.revize.com/revize/stmarysnew/department/community_development/PTVs.20210419.v1.pdf"
add(id="stmarys", name="St. Marys, GA", short="St. Marys", state="GA", slug="stmarys",
    bbox=[30.715, -81.63, 30.82, -81.485], zoom=13,
    cover="St. Marys, Georgia only (north of Amelia Island). Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True,
                        "cite": "St. Marys PTV ordinance Sec. 94-102: PTVs on streets posted 35 mph or less, except Winding Road; state highways only at a marked crossing",
                        "url": STM}},
    bans=[], cart_only=[{"names": r"^Winding Road$", "url": STM, "label": "St. Marys PTV ordinance: no PTV on any portion of Winding Road"},
                        {"names": HW, "url": STM, "label": "St. Marys PTV ordinance: PTVs may not drive along a state highway except at a designated crossing"}],
    access=dict(kind="city ordinance (named road)", url=STM, label="St. Marys PTV ordinance (35 mph, not Winding Road)",
                applied="public/data/regions.json rule.golf_cart (35 mph) + research/regions/stmarys.json cart_only_bans"),
    enf=[src("St. Marys PTV ordinance", STM), src("O.C.G.A. 40-6-331", OCGA)],
    unverified=["A later news report said Dilworth Street was also banned. That sentence is not in the 2021 ordinance PDF, so Dilworth is not banned here."],
    towns=[("st-marys", "St. Marys", 30.7305, -81.5465)],
    res=[("St. Marys publishes the PTV rules, including the Winding Road ban.", "St. Marys personal transportation vehicle ordinance", STM)])

KEYS = "https://keysweekly.com/42/council-says-golf-carts-are-a-go/"
add(id="lowerkeys", name="Lower Keys / Marathon, FL", short="Lower Keys", state="FL", slug="lowerkeys",
    bbox=[24.605, -81.58, 24.78, -80.95], zoom=12,
    cover="The Lower Keys from Big Pine Key through Marathon only (north of Key West). Pick another city in the menu above.",
    bans=[],
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.2122 (LSVs on roads posted 35 mph or less) and F.S. 316.212 (golf carts only on roads a county or city designates). Marathon discussed LSVs in 2011 and adopted no extra cart-street list.",
                   law_url=FL2122,
                   searched="Monroe County Code Ch. 25 (speed zones, not a golf-cart street list); Marathon City Council April 2011 (keysweekly.com); web search 'Marathon FL golf cart ordinance designated streets'"),
    enf=[src("Marathon City Council on LSVs (Keys Weekly, 2011)", KEYS), src("FLHSMV low-speed vehicles", FLHSMV), src("F.S. 316.2122", FL2122)],
    unverified=["No designated golf-cart street list was found for Marathon or the unincorporated Lower Keys in this box, so plain golf carts show red except tagged cart paths. US 1 is red wherever it is posted over 35 mph."],
    towns=[("marathon", "Marathon", 24.7261, -81.0514), ("big-pine-key", "Big Pine Key", 24.67, -81.36)],
    res=[("Marathon's council treated registered LSVs as legal on roads posted 35 mph or less and did not adopt a golf-cart street list.", "Marathon council on golf carts and LSVs", KEYS)])

CBB = "https://cocoabeach.granicus.com/MetaViewer.php?clip_id=4536&meta_id=240956&view_id=4"
CBO = "https://cocoabeach.granicus.com/MetaViewer.php?clip_id=4213&meta_id=225018&view_id=4"
add(id="cocoabeach", name="Cocoa Beach, FL", short="Cocoa Beach", state="FL", slug="cocoabeach",
    bbox=[28.28, -80.64, 28.37, -80.59], zoom=14,
    cover="Cocoa Beach, Florida only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 30, "designated_only": True, "cross": True,
                        "note": "The Golf Cart Network Map is not digitized, so plain carts show on tagged paths only. Night driving needs lights.",
                        "cite": "Cocoa Beach Code Sec. 15-47 and Resolution 2023-07: golf carts only on streets the commission designates, posted 30 mph or less",
                        "url": CBO}},
    bans=[], cart_only=[{"names": r"^(SR A1A|FL A1A|State Road A1A|Atlantic Avenue|North Atlantic Avenue|South Atlantic Avenue)$", "url": CBO,
                         "label": "Cocoa Beach Sec. 15-47: golf carts only on city streets the commission designates. SR A1A is a state road and is not treated as a cart street (cross where the network map allows)."}],
    access=dict(kind="city resolution (map not digitized)", url=CBB,
                label="Cocoa Beach Resolution 2023-07 Golf Cart Network Map; Ord. 1660 / Code Sec. 15-47",
                applied="public/data/regions.json rule.golf_cart (designated only, 30 mph) + research/regions/cocoabeach.json cart_only_bans"),
    enf=[src("Cocoa Beach Resolution 2023-07", CBB), src("Cocoa Beach Ordinance 1660", CBO), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["The green streets on the 2023 network map are not digitized, so plain golf carts show red except tagged cart paths. SR A1A is banned for carts."],
    towns=[("cocoa-beach", "Cocoa Beach", 28.3200, -80.6076)],
    res=[("Cocoa Beach Resolution 2023-07 is the current golf cart network map.", "Cocoa Beach golf cart network map", CBB)])

VEN = "https://library.municode.com/fl/venice/codes/code_of_ordinances"
add(id="venice", name="Venice, FL", short="Venice", state="FL", slug="venice",
    bbox=[27.05, -82.48, 27.155, -82.39], zoom=13,
    cover="Venice, Florida only (south of Siesta Key). Pick another city in the menu above.",
    bans=[],
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.212 (golf carts only on roads a city or county designates and signs) and F.S. 316.2122 (LSVs on roads posted 35 mph or less). No Venice designation of golf cart streets was found.",
                   law_url=FL212,
                   searched="City of Venice code of ordinances (library.municode.com/fl/venice); web search 'Venice Florida golf cart ordinance designated streets'"),
    enf=[src("F.S. 316.212", FL212), src("F.S. 316.2122", FL2122), src("City of Venice code", VEN)],
    unverified=["No designated golf cart streets were found, so plain golf carts show red on public roads. LSVs follow the posted speed."],
    towns=[("venice", "Venice", 27.0990, -82.4543)],
    res=[("Venice's city code is the place a golf cart street designation would be adopted.", "City of Venice code of ordinances", VEN)])

def region_entry(r):
    s, w, n, e = r["bbox"]
    t = r["towns"][0]
    o = {"id": r["id"], "name": r["name"], "short": r["short"], "state": r["state"], "center": [t[2], t[3]], "zoom": r["zoom"],
         "bbox": r["bbox"], "cover": r["cover"], "slug": r["slug"]}
    if r.get("rule"): o["rule"] = r["rule"]
    return o

def cfg_entry(r):
    c = {}
    p = poly(r["id"])
    if p: c["poly"] = p
    else: c["poly"] = rect(*r["bbox"])
    c["bans"] = r.get("bans", [])
    if r.get("cart_only"): c["cart_only_bans"] = r["cart_only"]
    if r.get("designated"): c["designated_names"] = r["designated"]
    c["unverified"] = r.get("unverified", [])
    c["sources"] = [f'{x["label"]} {x["url"]}' for x in r["enf"]] + ["OpenStreetMap", "FHWA HPMS speed limits"]
    applied = "access" in r
    c["enforcement"] = {"checked": DAY,
                        "result": "bans_applied" if applied or r.get("bans") or r.get("cart_only") else "none_found",
                        "sources": r["enf"],
                        "note": "Golf Cart Maps Greenwich and next-10 research (Oct 28 2026). Posted signs never lift a ban. Designated street lists that are not digitized stay red for plain golf carts."}
    c["status"] = f"Added (regions-11, {DAY})"
    return c

def check_boxes():
    live = [x for x in J("public/data/regions.json") if x["id"] not in {r["id"] for r in R}]
    bad = []
    for r in R:
        for o in live:
            if boxes_overlap(r["bbox"], o["bbox"]): bad.append((r["id"], o["id"]))
        for o in R:
            if o["id"] >= r["id"]: continue
            if boxes_overlap(r["bbox"], o["bbox"]): bad.append((r["id"], o["id"]))
    if bad: sys.exit("bbox overlap: " + ", ".join(f"{a}/{b}" for a, b in bad))

def main():
    check_boxes()
    os.makedirs(os.path.join(ROOT, "research/regions11_polys"), exist_ok=True)
    for r in R:
        W(f"research/regions11_polys/{r['id']}.json", rect(*r["bbox"]))  # bbox polys; reruns stay aligned with the box
    regs = J("public/data/regions.json"); ids = {r["id"] for r in R}
    old = {x["id"]: x for x in regs}
    regs = [x for x in regs if x["id"] not in ids]
    for r in R:
        e = region_entry(r)
        if r["id"] in old and old[r["id"]].get("beta"): e["beta"] = True
        regs.append(e)
    W("public/data/regions.json", regs)
    rules = J("public/data/rules.json"); rules.update(STATES); W("public/data/rules.json", rules)
    os.makedirs(os.path.join(ROOT, "research/regions"), exist_ok=True)
    for r in R: W(f"research/regions/{r['id']}.json", cfg_entry(r))
    acc = J("research/access_sources.json")
    for r in R:
        if "access" in r: acc["regions"][r["id"]] = r["access"]; acc["state_law"].pop(r["id"], None)
        else: acc["state_law"][r["id"]] = r["state_law"]; acc["regions"].pop(r["id"], None)
    W("research/access_sources.json", acc)
    vb = J("research/validation_baseline.json")
    for r in R: vb["red_islands"].setdefault(r["id"], 0)
    W("research/validation_baseline.json", vb)
    rr = J("content/region_resources.json")
    for r in R:
        if r["res"]: rr[r["slug"]] = [{"lead": a, "name": b, "url": c} for a, b, c in r["res"]]
    W("content/region_resources.json", rr)
    print(len(R), "regions upserted:", " ".join(x["id"] for x in R))
if __name__ == "__main__": main()
