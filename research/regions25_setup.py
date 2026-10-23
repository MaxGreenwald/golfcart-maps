#!/usr/bin/env python3
"""regions-25-batch (Max, Oct 22 2026: "let's also add another 25 top neighborhoods/cities").
Idempotent upsert of the 25 new regions into public/data/regions.json, public/data/rules.json (NJ/DE/VA),
research/regions/<id>.json, research/access_sources.json, research/validation_baseline.json and
content/region_resources.json. Rerun after a rebase to resolve conflicts in those shared files.
Ranking and why: research/regions25_ranking_2026-10-22.md. Polys: research/regions25_polys/<id>.json."""
import json, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
def W(p, d, indent=1): json.dump(d, open(os.path.join(ROOT, p), "w"), indent=indent, ensure_ascii=False); open(os.path.join(ROOT, p), "a").write("\n")
DAY = "2026-10-22"
FLS = "https://www.flsenate.gov/Laws/statutes/2025/"
FLHSMV = "https://www.flhsmv.gov/safety-center/consumer-education/low-speed-vehicles/"
NJMVC = "https://www.nj.gov/mvc/vehicletopics/lowspeed.htm"
NCLSV = "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_20/GS_20-121.1.html"
SCDPS = "https://scdps.sc.gov/DrivinginSC/golf-cart-law"
TX551 = "https://texas.public.law/statutes/tex._transp._code_section_551.404"
DE2113 = "https://delcode.delaware.gov/title21/c021/sc01/index.html"
DEDMV = "https://dmv.de.gov/VehicleServices/specialvehicles/index.shtml?dc=ve_reg_golf"
VA9163 = "https://law.lis.virginia.gov/vacode/title46.2/chapter8/section46.2-916.3/"
VA9083 = "https://law.lis.virginia.gov/vacode/title46.2/chapter8/section46.2-908.3/"
CVC = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum="

STATES = {
 "NJ": {"name": "New Jersey",
        "lsv": {"max_posted": 25, "cross": True, "who": "street-legal LSVs",
                "note": "NJ LSVs may use roads posted 25 mph or less; a town, county or NJDOT can open roads up to 35 mph or ban LSVs",
                "cite": "N.J.S.A. 39:4-31.1 / NJ MVC low-speed vehicles (roads posted 25 mph or less; may cross faster roads at intersections)", "url": NJMVC},
        "golf_cart": {"not_street_legal": True, "max_posted": 0, "cross": False,
                      "note": "plain golf carts aren't street-legal in New Jersey; only FMVSS 500 LSVs with NJ title, registration and insurance. Switch to LSV if yours is one",
                      "cite": "NJ MVC low-speed vehicles: an LSV must meet 49 CFR 571.500 and be titled, registered and insured; golf carts don't qualify", "url": NJMVC}},
 "DE": {"name": "Delaware",
        "lsv": {"max_posted": 35, "cross": True, "who": "street-legal LSVs",
                "note": "not on dual highways (Coastal Hwy) outside towns except to cross",
                "cite": "21 Del. C. \u00a72113A (LSVs on roads posted 35 mph or less; not on dual highways in unincorporated areas except to cross)", "url": DE2113},
        "golf_cart": {"not_street_legal": True, "max_posted": 0, "cross": False,
                      "note": "Delaware DMV: golf carts are not allowed on Delaware highways. Switch to LSV if yours is a registered LSV",
                      "cite": "Delaware DMV special vehicles: golf carts are not allowed to operate on Delaware highways", "url": DEDMV}},
 "VA": {"name": "Virginia",
        "lsv": {"max_posted": 35, "cross": True, "cite": "Va. Code \u00a746.2-908.3 (LSVs on highways posted 35 mph or less)", "url": VA9083},
        "golf_cart": {"max_posted": 25, "designated_only": True, "cross": True, "daylight_only": True,
                      "cite": "Va. Code \u00a746.2-916.3 (golf carts only on highways the locality designates, posted 25 mph or less; cross at intersections posted 35 or less; sunrise to sunset unless equipped)", "url": VA9163}},
}

def rect(s, w, n, e): return [[w, s], [e, s], [e, n], [w, n], [w, s]]
def poly(rid):
    p = os.path.join(ROOT, "research/regions25_polys", rid + ".json")
    return json.load(open(p)) if os.path.exists(p) else None
def src(label, url): return {"label": label, "url": url}

# ---------------------------------------------------------------- the 25 regions (ranked order)
R = []
def add(**k): R.append(k)

add(id="ocnj", name="Ocean City, NJ", short="Ocean City NJ", state="NJ", slug="oceancitynj", bbox=[39.19, -74.74, 39.30, -74.55], zoom=14,
    cover="Ocean City, NJ (the barrier island, the Gardens to Strathmere line) only. Pick another city in the menu above.",
    bans=[{"names": "^(Bay Avenue|West Avenue)$|^NJ 52$|^Roosevelt Boulevard$|^CR 623$", "url": "https://www.ocnj.us/media/Police/LSV%27s.pdf",
           "label": "Ocean City Police LSV facts (2021): no LSVs on roads above 25 mph such as Bay Ave, West Ave, Route 52, the 34th St bridge and Ocean Dr south of South Inlet Dr (cross at intersections only)"}],
    access=dict(kind="police LSV rules sheet (named roads)", url="https://www.ocnj.us/media/Police/LSV%27s.pdf", label="Ocean City Police: LSV need-to-know facts (banned roads list)", applied="research/regions/ocnj.json bans"),
    enf=[src("Ocean City Police LSV facts", "https://www.ocnj.us/media/Police/LSV%27s.pdf"), src("NJ MVC low-speed vehicles", NJMVC)],
    unverified=["Ocean Drive south of South Inlet Drive is in the police list; it's part of Bay Ave/CR 619 here and is covered by the Bay Ave ban."],
    towns=[("ocean-city", "Ocean City", 39.2776, -74.5746)],
    res=[("Ocean City's police department explains where LSVs can and can't drive.", "Ocean City Police LSV facts sheet", "https://www.ocnj.us/media/Police/LSV%27s.pdf")])

add(id="lbi", name="Long Beach Island, NJ", short="Long Beach Island", state="NJ", slug="lbi", bbox=[39.48, -74.32, 39.78, -74.08], zoom=13,
    cover="Long Beach Island (Barnegat Light to Holgate, plus the Route 72 causeway) only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="police LSV page", url="https://surfcitypdnj.org/lsv/", label="Surf City Police LSV page; NJ MVC 25 mph rule", applied="NJ LSV rule (roads posted 25 mph or less) in public/data/rules.json"),
    enf=[src("Surf City Police LSV page", "https://surfcitypdnj.org/lsv/"), src("NJ MVC low-speed vehicles", NJMVC)],
    unverified=["Long Beach Blvd is posted 30 to 40 mph in most places and shows red for LSVs; untagged stretches follow the road class. Beach Haven and Ship Bottom local LSV orders weren't found online."],
    towns=[("surf-city", "Surf City", 39.6621, -74.1663), ("beach-haven", "Beach Haven", 39.5593, -74.2432)],
    res=[("Surf City's police department covers LSV registration and road rules on the island.", "Surf City Police LSV rules", "https://surfcitypdnj.org/lsv/")])

add(id="fmb", name="Fort Myers Beach, FL", short="Fort Myers Beach", state="FL", slug="fortmyersbeach", bbox=[26.38, -81.97, 26.48, -81.85], zoom=14,
    cover="Fort Myers Beach (Estero Island) only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="town ordinance", url="https://www.fortmyersbeachfl.gov/DocumentCenter/View/24451/25-03-Beach-Bicycle-and-Vehicle-Safety", label="Town of Fort Myers Beach Ord. 25-03 (beach, bicycle and vehicle safety)", applied="no designated golf cart streets: golf carts follow F.S. 316.212 (designated roads only); LSVs F.S. 316.2122"),
    enf=[src("Town of Fort Myers Beach Ord. 25-03", "https://www.fortmyersbeachfl.gov/DocumentCenter/View/24451/25-03-Beach-Bicycle-and-Vehicle-Safety"), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["No town designation of golf cart streets was found, so plain golf carts show red on public roads (F.S. 316.212)."],
    towns=[("fort-myers-beach", "Fort Myers Beach", 26.4520, -81.9480)],
    res=[("The town's 2025 ordinance covers beach, bicycle and vehicle safety rules.", "Fort Myers Beach Ordinance 25-03 vehicle safety", "https://www.fortmyersbeachfl.gov/DocumentCenter/View/24451/25-03-Beach-Bicycle-and-Vehicle-Safety")])

add(id="sanibel", name="Sanibel & Captiva, FL", short="Sanibel", state="FL", slug="sanibel", bbox=[26.41, -82.27, 26.56, -82.00], zoom=13,
    cover="Sanibel and Captiva islands (plus the Sanibel Causeway) only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 30, "designated_only": True, "cite": "City of Sanibel Ord. 19-011 and F.S. 316.212: golf carts only on designated roads posted 30 mph or less", "url": "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10937/994063/pdf"}},
    bans=[],
    access=dict(kind="city ordinance", url="https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10937/994063/pdf", label="City of Sanibel Ord. 19-011 (golf carts and LSVs)", applied="public/data/regions.json rule.golf_cart (designated roads posted 30 or less)"),
    enf=[src("City of Sanibel Ord. 19-011", "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10937/994063/pdf"), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["Sanibel's designated golf cart road list isn't digitized, so plain golf carts show red except on tagged cart roads."],
    towns=[("sanibel", "Sanibel", 26.4434, -82.1110), ("captiva", "Captiva", 26.5280, -82.1890)],
    res=[("Sanibel's city code covers where golf carts and LSVs may drive on the island.", "City of Sanibel golf cart ordinance", "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10937/994063/pdf")])

add(id="capemay", name="Cape May & the Wildwoods, NJ", short="Cape May", state="NJ", slug="capemay", bbox=[38.92, -74.97, 39.13, -74.68], zoom=13,
    cover="Cape May, the Wildwoods, Stone Harbor and Avalon (plus the mainland roads between them) only. Pick another city in the menu above.",
    bans=[{"names": "^Garden State Parkway$", "url": NJMVC, "label": "Garden State Parkway: limited-access toll road, posted well above 25 mph (no LSVs)"}],
    access=dict(kind="borough ordinances", url="https://ecode360.com/10814440", label="Stone Harbor code (LSVs); Avalon Ord. 799-2020 (LSV rules)", applied="NJ LSV rule (25 mph) + region config; Avalon/Stone Harbor rules checked"),
    enf=[src("Stone Harbor borough code", "https://ecode360.com/10814440"), src("Avalon Ord. 799-2020", "https://avalonboro.net/wp-content/uploads/2020/02/ORD-799-2020-TAXICABS-LOW-SPEED-VEHICLES-WITHOUT-EDITS.pdf"), src("NJ MVC low-speed vehicles", NJMVC)],
    unverified=["The region box includes mainland Cape May Court House roads; those follow the plain NJ 25 mph LSV rule."],
    towns=[("cape-may", "Cape May", 38.9351, -74.9060), ("wildwood", "Wildwood", 38.9918, -74.8149), ("stone-harbor", "Stone Harbor", 39.0526, -74.7579), ("avalon", "Avalon", 39.0965, -74.7182)],
    res=[("Stone Harbor's borough code is the official source for local LSV rules.", "Stone Harbor borough code LSV chapter", "https://ecode360.com/10814440")])

add(id="topsail", name="Topsail Island, NC", short="Topsail Island", state="NC", slug="topsail", bbox=[34.33, -77.75, 34.55, -77.40], zoom=13,
    cover="Topsail Island (Topsail Beach, Surf City and North Topsail Beach) only. Pick another city in the menu above.",
    bans=[{"names": "^(North|South) Anderson Boulevard$", "url": "https://topsailbeachnc.gov/Departments/Police/Golf-Cart-Low-Speed-Vehicles",
           "label": "Town of Topsail Beach: LSVs may only cross North or South Anderson Blvd (except the 25 mph business-district zone on S. Anderson; shown red to be safe)"}],
    access=dict(kind="town police rules (named roads)", url="https://topsailbeachnc.gov/Departments/Police/Golf-Cart-Low-Speed-Vehicles", label="Town of Topsail Beach golf cart / LSV rules", applied="research/regions/topsail.json bans"),
    enf=[src("Town of Topsail Beach golf cart/LSV rules", "https://topsailbeachnc.gov/Departments/Police/Golf-Cart-Low-Speed-Vehicles"), src("N.C.G.S. 20-121.1", NCLSV)],
    unverified=["The 25 mph business-district stretch of S. Anderson Blvd is LSV-legal per the town but is shown red with the rest of Anderson Blvd.",
                "Surf City and North Topsail Beach golf cart permit rules weren't confirmed; plain golf carts use the NC default (roads posted 25 or less)."],
    towns=[("surf-city-nc", "Surf City, NC", 34.4271, -77.5461), ("topsail-beach", "Topsail Beach", 34.3654, -77.6305), ("north-topsail-beach", "North Topsail Beach", 34.4932, -77.4319)],
    res=[("Topsail Beach police list where LSVs may drive and which roads are crossing-only.", "Topsail Beach golf cart and LSV rules", "https://topsailbeachnc.gov/Departments/Police/Golf-Cart-Low-Speed-Vehicles")])

KURE = "https://www.townofkurebeach.org/golf-cart-rules"
ABNC = "https://atlanticbeach-nc.com/departments/police-department/golfcarts/"
HBNC = "https://hbtownhall.com/ordinance-summary"
MHOH = "https://codelibrary.amlegal.com/codes/marblehead/latest/marblehead_oh/0-0-0-112451"
NAVB = "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/12483/400831/pdf"
add(id="carolinabeach", name="Carolina Beach & Kure Beach, NC", short="Carolina Beach", state="NC", slug="carolinabeach", bbox=[33.95, -77.95, 34.08, -77.87], zoom=14,
    cover="Carolina Beach and Kure Beach (Pleasure Island) only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True, "note": "town cart permit and insurance; plain golf cart permits end Dec 31 2027 (LSVs continue)", "cite": "Town of Carolina Beach golf cart/LSV rules: carts only on roads posted 35 mph or less; may cross faster roads at intersections", "url": "https://www.carolinabeach.gov/324/Golf-Cart-LSV-Rules-Regulations"}},
    bans=[], cart_only=[{"names": "^", "poly": "kure_beach.json", "url": KURE,
                         "label": "Town of Kure Beach: golf carts must be tagged, licensed and meet the LSV standard (49 CFR 571.500) to use town streets; plain golf carts aren't street-legal"}],
    access=dict(kind="town rules", url="https://www.carolinabeach.gov/324/Golf-Cart-LSV-Rules-Regulations", label="Town of Carolina Beach golf cart / LSV rules and regulations", applied="public/data/regions.json rule.golf_cart (35 mph)"),
    enf=[src("Town of Carolina Beach golf cart/LSV rules", "https://www.carolinabeach.gov/324/Golf-Cart-LSV-Rules-Regulations"), src("WECT: golf carts phased out of Carolina Beach streets by 2028", "https://www.wect.com/2023/03/15/golf-carts-disappear-carolina-beach-streets-by-2028/"), src("Town of Kure Beach golf cart rules (street-legal LSV standard only)", KURE)],
    unverified=["South of Kure Beach (Fort Fisher) golf carts use Carolina Beach's 35 mph rule; no separate county rule was found."],
    towns=[("carolina-beach", "Carolina Beach", 34.0352, -77.8936), ("kure-beach", "Kure Beach", 33.9968, -77.9072)],
    res=[("Carolina Beach's town page lists the golf cart and LSV permit rules.", "Carolina Beach golf cart and LSV rules", "https://www.carolinabeach.gov/324/Golf-Cart-LSV-Rules-Regulations")])

EIDOC = "https://www.emeraldisle-nc.org/DocumentCenter/View/511/Golf-Cart-Safety-Presentation-PDF?bidId="
add(id="emeraldisle", name="Emerald Isle & Atlantic Beach, NC", short="Emerald Isle", state="NC", slug="emeraldisle", bbox=[34.64, -77.16, 34.73, -76.68], zoom=13,
    cover="Bogue Banks: Emerald Isle, Indian Beach, Pine Knoll Shores and Atlantic Beach only. Pick another city in the menu above.",
    bans=[], cart_only=[{"names": "^(Emerald Drive|Coast Guard Road)$|^NC 58$", "bbox": [34.64, -77.16, 34.70, -76.97], "url": EIDOC,
                         "label": "Town of Emerald Isle: golf carts may not drive on NC 58 (Emerald Dr) or Coast Guard Rd; cross straight over only"},
                        {"names": "^((East |West )?Fort Macon Road|Atlantic Beach Causeway)$|^NC 58$", "bbox": [34.68, -76.80, 34.71, -76.68], "url": ABNC,
                         "label": "Town of Atlantic Beach: golf carts may not drive on NC 58 / Fort Macon Rd or the Atlantic Beach Causeway (limited direct crossings only)"}],
    access=dict(kind="town ordinance summary (named roads)", url=EIDOC, label="Town of Emerald Isle golf cart rules (NC 58 and Coast Guard Rd off limits)", applied="research/regions/emeraldisle.json cart_only_bans"),
    enf=[src("Town of Emerald Isle golf cart safety rules", EIDOC), src("Atlantic Beach Police golf carts", ABNC)],
    unverified=["Pine Knoll Shores and Indian Beach cart rules weren't confirmed, and Atlantic Beach allows registered carts up to 35 mph; the map uses the NC default for golf carts (roads posted 25 mph or less) outside Emerald Isle, which is stricter."],
    towns=[("emerald-isle", "Emerald Isle", 34.6650, -77.0280), ("atlantic-beach", "Atlantic Beach", 34.6991, -76.7400)],
    res=[("Emerald Isle's golf cart safety guide lists the roads carts must stay off.", "Emerald Isle golf cart safety guide", EIDOC)])

DUN = "https://www.dunedingov.com/files/assets/city/v/1/live-work-play/documents/golf-cart-map.pdf"
add(id="clearwater", name="Clearwater Beach & Dunedin, FL", short="Clearwater Beach", state="FL", slug="clearwater", bbox=[27.94, -82.85, 28.07, -82.765], zoom=13,
    cover="Clearwater Beach, downtown Clearwater and Dunedin only. Pick another city in the menu above.", poly_rect=True,
    bans=[],
    access=dict(kind="city golf cart map", url=DUN, label="City of Dunedin golf cart map (designated streets)", applied="golf carts: F.S. 316.212 designated roads only; Dunedin designations not yet digitized"),
    enf=[src("City of Dunedin golf cart map", DUN), src("Pinellas County golf cart communities", "https://pinellas.gov/golf-cart-communities/"), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["Dunedin's designated golf cart streets are on a PDF map that isn't digitized yet, so plain golf carts show red outside tagged cart roads."],
    towns=[("clearwater-beach", "Clearwater Beach", 27.9780, -82.8270), ("dunedin", "Dunedin", 28.0190, -82.7870)],
    res=[("Pinellas County lists the cities that allow golf carts on designated streets.", "Pinellas County golf cart communities", "https://pinellas.gov/golf-cart-communities/")])

SPB = "https://www.spblibrary.com/498/Golf-Carts"
add(id="stpete", name="St. Pete Beach & Treasure Island, FL", short="St. Pete Beach", state="FL", slug="stpetebeach", bbox=[27.68, -82.82, 27.82, -82.70], zoom=13,
    cover="St. Pete Beach, Treasure Island and Madeira Beach only. Pick another city in the menu above.",
    bans=[], cart_only=[{"names": "^(Gulf Boulevard|Pinellas Bayway|Blind Pass Road)$|^SR (699|682|666)$|^CR 150$", "url": SPB,
                         "label": "City of St. Pete Beach: registered golf carts only on designated city streets, not on state or county roads (Gulf Blvd, Pinellas Bayway)"}],
    access=dict(kind="city golf cart rules", url=SPB, label="City of St. Pete Beach golf cart rules (city streets only, not state/county roads)", applied="research/regions/stpete.json cart_only_bans"),
    enf=[src("City of St. Pete Beach golf carts", SPB), src("F.S. 316.212", FLS + "316.212")],
    unverified=["St. Pete Beach's designated street list isn't digitized; plain golf carts show red except on tagged cart roads. Treasure Island and Madeira Beach cart rules weren't confirmed."],
    towns=[("st-pete-beach", "St. Pete Beach", 27.7253, -82.7412), ("treasure-island", "Treasure Island", 27.7692, -82.7690)],
    res=[("St. Pete Beach explains golf cart registration and the streets carts may use.", "St. Pete Beach golf cart rules", SPB)])

PATCH = "https://patch.com/california/newportbeach/golf-carts-not-street-legal-newport-beach-cops-say"
add(id="newport", name="Newport Beach & Balboa, CA", short="Newport Beach", state="CA", slug="newportbeach", bbox=[33.585, -117.935, 33.635, -117.85], zoom=14,
    cover="Newport Beach's coast (Balboa Peninsula, Balboa Island, Lido, Newport Heights and Corona del Mar) only. Pick another city in the menu above.", poly_rect=True,
    bans=[{"names": "^(Pacific Coast Highway|West Coast Highway|East Coast Highway)$|^CA 1$", "url": PATCH,
           "label": "Newport Beach Police: golf carts and LSVs stay off Pacific Coast Highway (posted 40+ mph)"}],
    state_law=dict(text="state law, no local ordinance found", law="CVC 21716 (golf carts on highways posted 25 mph or less in a business or residence district) and CVC 21260 (LSVs on roads posted 35 mph or less). Newport Beach has no golf cart transportation plan.",
                   law_url=CVC + "21716", searched="Newport Beach Municipal Code (Title 12 Vehicles and Traffic) and web search 'Newport Beach golf cart ordinance'; police guidance in Patch (PCH off limits)"),
    enf=[src("Patch: Newport Beach police on golf carts", PATCH), src("CVC 21716", CVC + "21716")],
    unverified=["Newport Beach has no city golf cart ordinance; the CA state rules apply."],
    towns=[("balboa-island", "Balboa Island", 33.6070, -117.8910), ("balboa-peninsula", "Balboa Peninsula", 33.6010, -117.9010)],
    res=[("Balboa Island's community site explains golf cart rules on the island's narrow streets.", "Balboa Island golf cart guide", "https://www.balboaisland.com/golf-carts/")])

SRIA = "https://visitpensacolabeach.com/beach-rules/"
add(id="pensacola", name="Pensacola Beach & Navarre Beach, FL", short="Pensacola Beach", state="FL", slug="pensacolabeach", bbox=[30.31, -87.20, 30.41, -86.84], zoom=13,
    cover="Pensacola Beach and Navarre Beach (Santa Rosa Island) only. Pick another city in the menu above.",
    bans=[{"names": "^Bob Sikes Bridge$", "url": SRIA, "label": "Santa Rosa Island Authority beach rules: golf carts and LSVs may not use the Bob Sikes Bridge"}],
    access=dict(kind="island authority rules", url=SRIA, label="Santa Rosa Island Authority beach rules (LSVs on Via de Luna, Fort Pickens Rd, Pensacola Beach Blvd; no bridges)", applied="research/regions/pensacola.json bans"),
    enf=[src("Santa Rosa Island Authority beach rules", SRIA), src("FLHSMV low-speed vehicles", FLHSMV), src("Santa Rosa County golf cart ordinance (Navarre Beach designated county roads; not the Navarre Bridge)", NAVB)],
    unverified=["J Earle Bowden Way (Gulf Islands National Seashore) is shown at its posted 35 mph; National Park Service rules may differ.", "Golf cart designated roads on the island aren't digitized; plain golf carts show red outside tagged cart roads."],
    towns=[("pensacola-beach", "Pensacola Beach", 30.3330, -87.1420), ("navarre-beach", "Navarre Beach", 30.3800, -86.8630)],
    res=[("The Santa Rosa Island Authority posts Pensacola Beach rules, including golf carts.", "Pensacola Beach rules from the island authority", SRIA)])

OIB = "https://www.oibgov.com/20855/golf-carts-low-speed-electric-vehicles"
add(id="brunswick", name="Brunswick Islands, NC", short="Brunswick Islands", state="NC", slug="brunswickislands", bbox=[33.85, -78.56, 33.94, -78.25], zoom=13,
    cover="Sunset Beach, Ocean Isle Beach and Holden Beach only. Pick another city in the menu above.",
    rule={"golf_cart": {"not_street_legal": True, "max_posted": 0, "cross": False, "note": "Ocean Isle Beach: only registered, inspected, insured LSVs may use town streets. Switch to LSV if yours is one", "cite": "Town of Ocean Isle Beach: golf carts must be registered, tagged and insured LSVs to use public streets (N.C.G.S. 20-121.1)", "url": OIB}},
    bans=[],
    access=dict(kind="town police rules", url=OIB, label="Town of Ocean Isle Beach golf cart / LSEV rules", applied="public/data/regions.json rule.golf_cart (LSVs only)"),
    enf=[src("Town of Ocean Isle Beach LSEV rules", OIB), src("Town of Sunset Beach police", "https://sunsetbeachnc.gov/index.asp?DE=EA023C5C-7CAA-427E-96DC-6A30EF38F028&SEC=C21FDBC1-4AB6-4837-B0E8-75EC6E7A2D70"), src("Town of Holden Beach ordinance summary: golf carts not allowed on roads; registered LSVs only", HBNC)],
    unverified=["Sunset Beach's own golf cart rule wasn't confirmed; Ocean Isle's and Holden Beach's LSV-only rule is applied to the whole region (stricter)."],
    towns=[("ocean-isle-beach", "Ocean Isle Beach", 33.8930, -78.4400), ("sunset-beach", "Sunset Beach", 33.8710, -78.5070), ("holden-beach", "Holden Beach", 33.9140, -78.3030)],
    res=[("Ocean Isle Beach explains the registration rules for street-legal carts.", "Ocean Isle Beach low-speed vehicle rules", OIB)])

CB = "https://crystalbeach.com/area-information/information/golf-carts-atvs/"
add(id="crystalbeach", name="Bolivar Peninsula, TX", short="Crystal Beach", state="TX", slug="crystalbeach", bbox=[29.36, -94.80, 29.60, -94.35], zoom=13,
    cover="Bolivar Peninsula (Port Bolivar, Crystal Beach, Gilchrist and High Island) only. Pick another city in the menu above.",
    bans=[{"names": "^TX 87$|^State Highway 87$", "url": CB, "label": "Golf carts prohibited on highways (SH 87, posted 50 to 60 mph); cross at intersections only"}],
    state_law=dict(text="state law, no local ordinance found", law="Tex. Transp. Code \u00a7551.404 (golf carts on roads posted 35 mph or less within 2 mi of the master-planned community/beach or where the county allows) and \u00a7551.304 (LSVs on roads posted 35 or less). Galveston County unincorporated peninsula; SH 87 is crossing only.",
                   law_url=TX551, searched="Galveston County code and commissioners court orders; web search 'Bolivar Peninsula golf cart ordinance'; community page crystalbeach.com"),
    enf=[src("CrystalBeach.com golf cart rules", CB), src("Tex. Transp. Code 551.404", TX551)],
    unverified=["Galveston County hasn't published a peninsula golf cart ordinance; the state rules apply."],
    towns=[("crystal-beach", "Crystal Beach", 29.4630, -94.6420)],
    res=[("The peninsula's community site sums up local golf cart rules.", "Crystal Beach golf cart rules", CB)])

CC = "https://corpuschristi.legistar.com/LegislationDetail.aspx?GUID=ED4B9361-1F41-4640-8B25-2E6A5E99FBAA&ID=4216695&Options=&Search="
add(id="padre", name="North Padre & Mustang Island, TX", short="North Padre Island", state="TX", slug="padreisland", bbox=[27.48, -97.30, 27.695, -97.15], zoom=13,
    cover="North Padre Island and southern Mustang Island (Corpus Christi) only. Pick another city in the menu above.",
    bans=[{"names": "^TX 361$|^State Highway 361$|^John F Kennedy Memorial Causeway$", "url": CC, "label": "City of Corpus Christi golf cart ordinance (File 19-1512): carts on island streets posted 35 mph or less, not SH 361 or the JFK Causeway"}],
    access=dict(kind="city ordinance (area map)", url=CC, label="City of Corpus Christi golf cart/NEV ordinance, File 19-1512 (island streets posted 35 or less)", applied="research/regions/padre.json bans; TX state rule (35 mph)"),
    enf=[src("Corpus Christi golf cart ordinance (File 19-1512)", CC), src("Corpus Christi Island Mobility Plan (2026)", "https://www.corpuschristitx.gov/media/iluhulk2/2026-02-17-island-mobility-plan-low-res.pdf")],
    unverified=["South Padre Island Drive (PR 22) is posted 55 mph and shows red; its untagged stretches follow the road class."],
    towns=[("north-padre-island", "North Padre Island", 27.6000, -97.2200)],
    res=[("Corpus Christi's Island Mobility Plan covers walking, biking and golf cart travel on the island.", "Corpus Christi Island Mobility Plan", "https://www.corpuschristitx.gov/media/iluhulk2/2026-02-17-island-mobility-plan-low-res.pdf")])

GICIA = "https://thegicia.org/bike-path/"
add(id="bocagrande", name="Boca Grande, FL", short="Boca Grande", state="FL", slug="bocagrande", bbox=[26.71, -82.29, 26.84, -82.24], zoom=14,
    cover="Boca Grande (Gasparilla Island) only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="county ordinance", url="https://www.leegov.com/bocc/Ordinances/25-16.pdf", label="Lee County Ord. 25-16; GICIA bike path rules (electric carts on the path, 15 mph)", applied="golf carts: F.S. 316.212 designated roads only; the bike path is drawn where OSM tags it"),
    enf=[src("Lee County Ord. 25-16", "https://www.leegov.com/bocc/Ordinances/25-16.pdf"), src("GICIA bike path rules", GICIA)],
    unverified=["Electric golf carts may use the Boca Grande bike path (15 mph, 50 in wide max); the path is drawn only where OpenStreetMap tags it for golf carts."],
    towns=[("boca-grande", "Boca Grande", 26.7490, -82.2620)],
    res=[("The Gasparilla Island Conservation and Improvement Association runs the bike path and posts its cart rules.", "Boca Grande bike path rules (GICIA)", GICIA)])

PAW = "https://www.townofpawleysisland.com/golf-cart-restrictions/"
add(id="pawleys", name="Pawleys Island & Litchfield, SC", short="Pawleys Island", state="SC", slug="pawleysisland", bbox=[33.40, -79.18, 33.549, -79.00], zoom=13,
    cover="Pawleys Island, Litchfield Beach and Murrells Inlet only. Pick another city in the menu above.",
    bans=[{"names": "^(Atlantic Avenue|Myrtle Avenue|Springs Avenue|Shell Road|Pavilion Lane|Doyle Avenue|Frazier Street|Hazard Avenue|Hazard Street|Pearce Street|Pritchard Street|Salt Creek Place|Scarborough Avenue|1st Street|2nd Street|3rd Street|North Causeway Road|South Causeway Road)$", "bbox": [33.40, -79.136, 33.46, -79.10], "url": PAW,
           "label": "Town of Pawleys Island: LSVs prohibited on all town roads; golf carts need SCDMV and town permits (address within 2 mi). One rule per road here, so the island is shown red to be safe"}],
    access=dict(kind="town rules", url=PAW, label="Town of Pawleys Island golf cart and LSV rules", applied="research/regions/pawleys.json bans (island roads)"),
    enf=[src("Town of Pawleys Island golf cart and LSV rules", PAW), src("Georgetown County Sheriff: golf cart rules", "https://www.gcsheriff.org/blog/21210525-gcso-know-the-rules-for-golf-carts-and-the-beach/")],
    unverified=["The town of Pawleys Island allows permitted golf carts but bans LSVs; the map can only show one rule per road there, so island roads are red for both (safer). Golf cart owners with a town permit may still use them."],
    towns=[("pawleys-island", "Pawleys Island", 33.4330, -79.1210), ("murrells-inlet", "Murrells Inlet", 33.5400, -79.0450)],
    res=[("Pawleys Island's town page covers golf cart permits and the LSV ban.", "Pawleys Island golf cart restrictions", PAW)])

DI = "https://www.townofdauphinisland.org/faq"
add(id="dauphin", name="Dauphin Island, AL", short="Dauphin Island", state="AL", slug="dauphinisland", bbox=[30.23, -88.35, 30.28, -88.07], zoom=13,
    cover="Dauphin Island only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 25, "cross": True, "note": "golf carts need a license plate from their home state to use public roads", "cite": "Town of Dauphin Island FAQ: golf carts need a state-issued license plate for public roadways; app keeps the Alabama ≤25 mph cap (UNCONFIRMED for Dauphin)", "url": DI}},
    bans=[],
    access=dict(kind="town FAQ", url=DI, label="Town of Dauphin Island FAQ (golf carts need a license plate for public roads)", applied="public/data/regions.json rule.golf_cart"),
    enf=[src("Town of Dauphin Island FAQ", DI)],
    unverified=["Dauphin Island doesn't publish a cart speed cap; the app keeps the Alabama ≤25 mph cap. Bienville Blvd's 35 and 40 mph stretches show red for carts."],
    towns=[("dauphin-island", "Dauphin Island", 30.2550, -88.1100)],
    res=[("The town FAQ explains what a golf cart needs to drive on Dauphin Island roads.", "Town of Dauphin Island FAQ", DI)])

FC = "https://library.municode.com/fl/franklin_county/codes/code_of_ordinances?nodeId=COLAOR_CH12MOVETR_ARTIIGOCA_SS12-39--12-60RE"
add(id="stgeorge", name="St. George Island, FL", short="St. George Island", state="FL", slug="stgeorgeisland", bbox=[29.58, -85.00, 29.70, -84.70], zoom=13,
    cover="St. George Island only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "designated_only": False, "cite": "Franklin County Code ch. 12, art. II: golf carts on St. George Island county roads, except Gulf Beach Dr; Franklin Blvd at crossings only (F.S. 316.212)", "url": FC}},
    bans=[], cart_only=[{"names": "^(East |West )?Gulf Beach Drive( East| West)?$|^Franklin Boulevard$|^CR 300$|^SR 300$", "url": FC,
                         "label": "Franklin County Code ch. 12: no golf carts on Gulf Beach Dr; Franklin Blvd at crossings only"}],
    access=dict(kind="county ordinance (named roads)", url=FC, label="Franklin County Code ch. 12 art. II golf carts (St. George Island)", applied="research/regions/stgeorge.json cart_only_bans + regions.json rule.golf_cart"),
    enf=[src("Franklin County Code ch. 12 art. II", FC)],
    unverified=["The St. George Island State Park road is shown by its posted speed; park rules may differ."],
    towns=[("st-george-island", "St. George Island", 29.6600, -84.8600)],
    res=[])

MB = "https://mexicobeachfl.gov/uploads/2025/01/Ordinance-569-Amending-Ordinance-516-Traffic-Code-and-Golf-Carts.pdf"
add(id="capesanblas", name="Cape San Blas & Mexico Beach, FL", short="Cape San Blas", state="FL", slug="capesanblas", bbox=[29.66, -85.43, 29.96, -85.28], zoom=12,
    cover="Cape San Blas, Indian Pass, Port St. Joe and Mexico Beach only. Pick another city in the menu above.",
    bans=[], cart_only=[{"names": "^US 98$|^SR 30A$|^SR 30E$|^SR 71$", "url": MB, "label": "Mexico Beach Ord. 569 / Gulf County: no golf carts on US 98 or the state roads (cross only)"}],
    access=dict(kind="city ordinance", url=MB, label="City of Mexico Beach Ord. 569 (traffic code and golf carts)", applied="research/regions/capesanblas.json cart_only_bans"),
    enf=[src("Mexico Beach Ord. 569", MB), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["Gulf County's own golf cart ordinance wasn't opened; county road designations aren't digitized, so plain golf carts show red outside tagged cart roads."],
    towns=[("mexico-beach", "Mexico Beach", 29.9480, -85.4200), ("port-st-joe", "Port St. Joe", 29.8120, -85.3030)],
    res=[("Mexico Beach's 2025 ordinance sets local golf cart rules.", "Mexico Beach golf cart ordinance 569", MB)])

FEN = "https://fenwickisland.delaware.gov/files/2022/02/Chapter-153.pdf"
_de = "21 Del. C. \u00a72113A: LSVs may not drive on dual highways (Coastal Hwy, DE 1) in unincorporated areas, only cross"
add(id="delbeaches", name="Rehoboth, Dewey & Bethany Beach, DE", short="Delaware beaches", state="DE", slug="delawarebeaches", bbox=[38.45, -75.12, 38.74, -75.04], zoom=13,
    cover="Rehoboth Beach, Dewey Beach, Bethany Beach, South Bethany and Fenwick Island only. Pick another city in the menu above.",
    bans=[{"names": "^DE 1$|^Coastal Highway$", "north_of": 38.705, "url": DE2113, "label": _de},
          {"names": "^DE 1$|^Coastal Highway$", "bbox": [38.545, -75.2, 38.683, -75.0], "url": DE2113, "label": _de},
          {"names": "^DE 1$|^Coastal Highway$", "bbox": [38.47, -75.2, 38.505, -75.0], "url": DE2113, "label": _de},
          {"names": "^", "bbox": [38.452, -75.062, 38.47, -75.045], "url": FEN, "label": "Town of Fenwick Island Code ch. 153: low-speed vehicles are prohibited on town streets"}],
    access=dict(kind="town code", url=FEN, label="Town of Fenwick Island Code ch. 153 (LSVs prohibited); 21 Del. C. 2113A", applied="research/regions/delbeaches.json bans"),
    enf=[src("Fenwick Island Code ch. 153", FEN), src("Delaware DMV: golf carts", DEDMV), src("21 Del. C. 2113A", DE2113)],
    unverified=["Coastal Highway inside Dewey Beach, Bethany Beach and South Bethany is shown by its posted speed; those towns' LSV rules weren't found online."],
    towns=[("rehoboth-beach", "Rehoboth Beach", 38.7210, -75.0760), ("dewey-beach", "Dewey Beach", 38.6930, -75.0750), ("bethany-beach", "Bethany Beach", 38.5390, -75.0560)],
    res=[("Delaware DMV explains which special vehicles may use public roads.", "Delaware DMV special vehicle rules", DEDMV)])

EDI = "https://www.townofedistobeach.com/police/golf-cart-and-low-speed-vehicle-use"
add(id="edisto", name="Edisto Beach, SC", short="Edisto Beach", state="SC", slug="edisto", bbox=[32.46, -80.37, 32.54, -80.27], zoom=14,
    cover="Edisto Beach only. Pick another city in the menu above.",
    bans=[], cart_only=[{"names": "^Palmetto Boulevard$|^SC 174$", "url": EDI, "label": "Town of Edisto Beach: golf carts may not drive on Palmetto Blvd (SC 174, a primary highway); cross straight over only"}],
    access=dict(kind="town police rules (named roads)", url=EDI, label="Town of Edisto Beach golf cart and LSV use", applied="research/regions/edisto.json cart_only_bans"),
    enf=[src("Town of Edisto Beach golf cart and LSV use", EDI), src("SCDPS golf cart law", SCDPS)],
    unverified=[],
    towns=[("edisto-beach", "Edisto Beach", 32.4990, -80.3070)],
    res=[("Edisto Beach police explain golf cart permits and the roads carts can use.", "Edisto Beach golf cart and LSV rules", EDI)])

HTN = "https://www.hometownnewsvolusia.com/news/golf-carts-are-not-for-all-roadways/article_0e592c76-c4c5-11ec-a74c-136b4cb9db2f.html"
add(id="nsb", name="New Smyrna Beach, FL", short="New Smyrna Beach", state="FL", slug="newsmyrnabeach", bbox=[28.95, -80.95, 29.08, -80.84], zoom=13,
    cover="New Smyrna Beach (beachside and mainland) only. Pick another city in the menu above.",
    bans=[{"names": "^(North |South )?Atlantic Avenue$|^(CR|SR) A1A$|^3rd Avenue$|^Third Avenue$", "url": HTN,
           "label": "New Smyrna Beach Police (Hometown News, 2022): LSVs prohibited on A1A/Atlantic Ave and 3rd Ave; cross at intersections only"}],
    access=dict(kind="police guidance (news report, named roads)", url=HTN, label="New Smyrna Beach Police via Hometown News: no LSVs on A1A/Atlantic Ave or 3rd Ave", applied="research/regions/nsb.json bans"),
    enf=[src("Hometown News: New Smyrna Beach golf cart rules", HTN), src("FLHSMV TL-63 golf carts and LSVs", "https://www.flhsmv.gov/pdf/proc/tl/tl-63.pdf")],
    unverified=["The banned-roads list comes from a 2022 news report quoting NSB police, not the city code itself."],
    towns=[("new-smyrna-beach", "New Smyrna Beach", 29.0260, -80.9270)],
    res=[])

KI = "https://kelleysisland.us/departments-2/kelleys-island-police-dept/"
add(id="kelleys", name="Kelleys Island & Marblehead, OH", short="Kelleys Island", state="OH", slug="kelleysisland", bbox=[41.50, -82.80, 41.62, -82.66], zoom=13,
    cover="Kelleys Island, Marblehead and Lakeside only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="village police rules", url=KI, label="Kelleys Island Police: golf carts titled, inspected and plated for public roads", applied="OH state rule (public/data/rules.json)"),
    enf=[src("Kelleys Island Police golf cart inspection", KI), src("Village of Marblehead Code: under-speed and low-speed vehicles", MHOH)],
    unverified=["Lakeside is a gated private community with its own 15 mph rules. Marblehead allows inspected, titled and registered carts on streets posted 35 mph or less (village code page blocks automated reads; confirmed via search listing and village police page)."],
    towns=[("kelleys-island", "Kelleys Island", 41.6020, -82.7080), ("marblehead", "Marblehead", 41.5380, -82.7330)],
    res=[("The Kelleys Island police page explains golf cart inspections for plates.", "Kelleys Island Police golf cart inspections", KI)])

CHT = "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10527/1231701/pdf"
add(id="chincoteague", name="Chincoteague, VA", short="Chincoteague", state="VA", slug="chincoteague", bbox=[37.88, -75.43, 37.97, -75.33], zoom=14,
    cover="Chincoteague Island only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 25, "designated_only": True, "cite": "Town of Chincoteague Sec. 8-2-13: golf carts only on streets the Town Council designates, posted 25 mph or less; never on Main St or Second St (cross at listed streets); town registration", "url": CHT}},
    bans=[], cart_only=[{"names": "^(Main|Second|North Main|South Main|2nd) Street$", "url": CHT, "label": "Town of Chincoteague Sec. 8-2-13: golf carts not allowed on Main Street or Second Street (crossings at Sycamore, Fifth, Third, Marshall and Endly only)"}],
    access=dict(kind="town code (named roads)", url=CHT, label="Town of Chincoteague Sec. 8-2-13 golf carts", applied="research/regions/chincoteague.json cart_only_bans + regions.json rule.golf_cart"),
    enf=[src("Town of Chincoteague Sec. 8-2-13", CHT), src("Va. Code 46.2-916.3", VA9163)],
    unverified=["The Town Council's list of designated golf cart streets isn't online; plain golf carts show red except on tagged cart roads."],
    towns=[("chincoteague", "Chincoteague", 37.9330, -75.3790)],
    res=[("Chincoteague's town code sets golf cart registration and the streets carts may use.", "Chincoteague golf cart ordinance", CHT)])

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
    elif r.get("poly_rect"): c["poly"] = rect(*r["bbox"])
    c["bans"] = r.get("bans", [])
    if r.get("cart_only"): c["cart_only_bans"] = r["cart_only"]
    c["unverified"] = r.get("unverified", [])
    c["sources"] = [f'{x["label"]} {x["url"]}' for x in r["enf"]] + ["OpenStreetMap", "FHWA HPMS speed limits"]
    c["enforcement"] = {"checked": DAY, "result": "local rules recorded" if "access" in r else "state law only", "sources": r["enf"],
                        "note": "Golf Cart Maps regions-25-batch research (Oct 22 2026). Posted signs never lift a ban."}
    c["status"] = f"Added (regions-25-batch, {DAY})"
    return c

def main():
    regs = J("public/data/regions.json"); ids = {r["id"] for r in R}
    regs = [x for x in regs if x["id"] not in ids]
    old = {x["id"]: x for x in J("public/data/regions.json")}
    for r in R:
        e = region_entry(r)
        if r["id"] in old and old[r["id"]].get("beta"): e["beta"] = True   # apply_beta_bar owns this flag
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
    print(len(R), "regions upserted")
if __name__ == "__main__": main()
