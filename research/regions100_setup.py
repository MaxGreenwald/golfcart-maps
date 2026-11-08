#!/usr/bin/env python3
"""24 more US golf cart / LSV towns, so public/data/regions.json reaches at least 100.
Idempotent upsert into public/data/regions.json, research/regions/<id>.json,
research/access_sources.json, research/validation_baseline.json and content/region_resources.json.
Ranking: research/regions100_ranking_2026-11-06.md.
A town is included only with a statute or ordinance URL. Where the street list is not digitized,
plain golf carts stay off public streets (designated_only or not_street_legal).
"""
import json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def J(p): return json.load(open(os.path.join(ROOT, p)))
def W(p, d, indent=1):
    fp = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    json.dump(d, open(fp, "w"), indent=indent, ensure_ascii=False)
    open(fp, "a").write("\n")
DAY = "2026-11-06"
FL212 = "https://www.flsenate.gov/Laws/Statutes/2025/316.212"
FL2122 = "https://www.flsenate.gov/Laws/Statutes/2025/316.2122"
FLHSMV = "https://www.flhsmv.gov/safety-center/consumer-education/low-speed-vehicles/"
NCLSV = "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_20/GS_20-121.1.html"
NC160 = "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160A/GS_160A-300.6.html"
NC153 = "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_153A/GS_153A-245.html"
SC90 = "https://www.scstatehouse.gov/code/t56c002.php"
SCDPS = "https://scdps.sc.gov/DrivinginSC/golf-cart-law"
TX551 = "https://texas.public.law/statutes/tex._transp._code_section_551.404"
VA9163 = "https://law.lis.virginia.gov/vacode/title46.2/chapter8/section46.2-916.3/"
VA9083 = "https://law.lis.virginia.gov/vacode/title46.2/chapter8/section46.2-908.3/"
CVC = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum="
ARS966 = "https://www.azleg.gov/ars/28/00966.htm"
OH214 = "https://codes.ohio.gov/ohio-revised-code/section-4511.214"

FAIR = "https://www.fairhopeal.gov/DocumentCenter/View/601/Fairhopesap-Final-Safe-Roads-Web-PDF"
OCR = "https://ocracokeobserver.com/2026/08/01/july-safety-report-on-ocracoke/"
DADE = "https://www.dadecityfl.com/Documents/Government/Departments/Finance/Apply%20for%20Golf%20Cart%20Registration.pdf"
MTD = "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10266/1298003/pdf"
PINE = "https://codelibrary.amlegal.com/codes/pinehurst/latest/pinehurst_nc/0-0-0-601"
BEAU = "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10399/1396567/pdf"
HSB = "https://www.horseshoe-bay-tx.gov/Archive.aspx?ADID=376"
SURF = "https://library.municode.com/tx/surfside_beach/codes/code_of_ordinances?nodeId=COOR_CH46TRVE"
SURFWEB = "https://www.surfsidetx.org/page/Golfcart"
COL = "https://colonialbeachva.gov/DocumentCenter/View/1830/Golf-Cart-Ordinance"
FLAG = "https://www.cityofflaglerbeach.com/DocumentCenter/View/6750/Golf-Cart-Info-Packet-2026"
ORI = "https://townoforiental.com/vertical/sites/%7B8227B748-6F08-4124-B0ED-02789B9A2F82%7D/uploads/6-9-26_CHAPTER_F.pdf"
CEL = "https://codelibrary.amlegal.com/codes/celina/latest/celina_oh/0-0-0-29408"
CAPE = "https://www.capecharles.org/media/13461"
CAPEDEC = "https://www.capecharles.org/treasurer/page/golf-cart-decals"
SUN = "https://sunlakessplash.com/sun-lakes-sheriffs-posse-golf-carts/"
HOWEY = "https://www.howey.org/DocumentCenter/View/507/Golf-Cart-Letter-2026"
APAL = "https://www.cityofapalachicola.com/wp-content/uploads/2022/09/2022-23-Fee-Schedule.pdf"
CEDAR = "https://www.myfloridalegal.com/ag-opinions/municipalities-operation-of-golf-carts"
CRCODE = "https://library.municode.com/fl/crystal_river/codes/code_of_ordinances?nodeId=PTIICOOR_CH15TR"
CRRES = "https://www.crystalriverfl.org/media/12356"

def rect(s, w, n, e): return [[w, s], [e, s], [e, n], [w, n], [w, s]]
def src(label, url): return {"label": label, "url": url}
def boxes_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

R = []
def add(**k): R.append(k)

# Fairhope: city safety plan states the LSV rule. No plain-golf-cart street ordinance was found,
# so carts do not inherit the Gulf Shores 25 mph profile.
add(id="fairhope", name="Fairhope, AL", short="Fairhope", state="AL", slug="fairhope",
    bbox=[30.49, -87.94, 30.56, -87.86], zoom=14,
    cover="Fairhope, Alabama only. Pick another city in the menu above.",
    rule={"golf_cart": {"not_street_legal": True, "max_posted": 0, "cross": False,
                        "note": "No Fairhope ordinance allowing plain golf carts was found. The city's published rule is for low-speed vehicles.",
                        "cite": "City of Fairhope Safe Streets plan: LSVs may use streets posted 35 mph or less and may cross faster roads, but may not travel along Greeno Road (US 98). Plain golf carts are not that rule.",
                        "url": FAIR}},
    bans=[{"names": r"^(Greeno Road|Scenic Highway 98)$|(^|;)US[- ]?98($|;)", "url": FAIR,
           "label": "City of Fairhope Safe Streets plan: LSVs may not travel along Greeno Road (US 98), including shoulders and side paths. Crossings at Fairhope Avenue and Morphy Avenue are the named exceptions."}],
    access=dict(kind="city safety plan (LSV rule)", url=FAIR,
                label="City of Fairhope Safe Streets plan: LSVs on streets posted 35 mph or less; Greeno Road (US 98) prohibited except to cross",
                applied="public/data/regions.json rule.golf_cart not_street_legal; research/regions/fairhope.json bans"),
    enf=[src("City of Fairhope Safe Streets plan", FAIR)],
    unverified=["The plan names crossings of Greeno Road at Fairhope Avenue and Morphy Avenue. The road itself stays red, including short pieces, because the ban is explicit."],
    towns=[("fairhope", "Fairhope", 30.5228, -87.9033)],
    res=[("Fairhope's safety plan states where low-speed vehicles may drive, and that Greeno Road is closed to them.", "Fairhope Safe Streets plan", FAIR)])

add(id="ocracoke", name="Ocracoke, NC", short="Ocracoke", state="NC", slug="ocracoke",
    bbox=[35.104, -75.994, 35.120, -75.970], zoom=15,
    cover="Ocracoke Village only. The highway north of the village is outside this map. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True,
                        "cite": "Hyde County Ordinance 2009-09-01, as quoted by the Hyde County Sheriff (2026): golf carts on public streets in Hyde County where the speed limit is 35 mph or less. N.C.G.S. 153A-245 (operator at least 16).",
                        "url": OCR}},
    bans=[],
    access=dict(kind="county ordinance quoted by the sheriff", url=OCR,
                label="Hyde County Sheriff reminder of Ordinance 2009-09-01 (golf carts on streets posted 35 mph or less)",
                applied="public/data/regions.json rule.golf_cart max_posted 35; village bbox only"),
    enf=[src("Ocracoke Observer: Hyde County Sheriff golf cart reminder (Ordinance 2009-09-01)", OCR),
         src("N.C.G.S. 153A-245", NC153), src("N.C.G.S. 20-121.1", NCLSV)],
    unverified=["The sheriff's 2026 quotation of Ordinance 2009-09-01 is countywide at 35 mph. This map is only the village. NC 12 north of the village, the beach, and the ferry are outside the box. A rental company also tells riders to stay off Southpoint Road; that limit is not in the quoted ordinance, so Southpoint Road is not given an extra ban."],
    towns=[("ocracoke", "Ocracoke", 35.1146, -75.9810)],
    res=[("The Hyde County Sheriff's reminder quotes the county golf cart ordinance used on Ocracoke.", "Hyde County golf cart ordinance reminder", OCR)])

DADE_NAMES = ["Sumner Avenue", "Martin Luther King Boulevard", "Martin Luther King Jr Boulevard",
              "Ross Avenue", "Beauchamp Avenue", "Madill Avenue", "Robinson Avenue", "Carter Avenue",
              "Pineapple Avenue", "Edwinola Way", "Magnolia Avenue", "Live Oak Avenue", "Pasco Avenue",
              "Church Avenue", "McMinn Avenue", "Buford Avenue", "Howard Avenue",
              "12th Street", "11th Street", "10th Street", "9th Street", "8th Street", "7th Street",
              "6th Street", "5th Street", "4th Street", "3rd Street", "2nd Street"]
add(id="dadecity", name="Dade City, FL", short="Dade City", state="FL", slug="dadecity",
    bbox=[28.34, -82.22, 28.39, -82.16], zoom=15,
    cover="Dade City, Florida only. Pick another city in the menu above.",
    bans=[],
    cart_only=[{"names": r"^(US 301|US 98|SR 52|State Road 52|County Road \d+[A-Z]?)$|(^|;)(US 301|US 98|SR 52|FL 52|CR \d+[A-Z]?)($|;)", "url": DADE,
                "label": "Dade City Ordinance 2024-01: golf carts are not authorized on state or county roads. US 301, US 98, SR 52 and county roads stay closed to golf carts. An LSV still follows the posted speed."}],
    designated=[{"names": DADE_NAMES, "bbox": [28.34, -82.22, 28.39, -82.16], "url": DADE,
                 "label": "Dade City resolution under Ordinance 2024-01: registered golf carts on the listed city streets"}],
    access=dict(kind="city ordinance and street resolution", url=DADE,
                label="Dade City Ordinance 2024-01 and the registration packet street list",
                applied="research/regions/dadecity.json designated_names and bans"),
    enf=[src("Dade City golf cart registration packet (Ordinance 2024-01 street list)", DADE), src("F.S. 316.212", FL212)],
    unverified=["The resolution street list is matched by name. A listed street that OpenStreetMap also tags as US 301, US 98 or SR 52 stays red."],
    towns=[("dade-city", "Dade City", 28.3647, -82.1959)],
    res=[("Dade City publishes the city streets where a registered golf cart may drive.", "Dade City golf cart registration packet", DADE)])

add(id="mountdora", name="Mount Dora, FL", short="Mount Dora", state="FL", slug="mountdora",
    bbox=[28.77, -81.68, 28.83, -81.62], zoom=14,
    cover="Mount Dora, Florida only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 30, "designated_only": False, "daylight_only": False, "cross": True,
                        "cite": "City of Mount Dora Ordinance 2024-12, Sec. 42-201: a registered golf cart on a city right of way posted 30 mph or less, unless posted no golf carts. Not on a county, state or federal roadway. LSVs follow F.S. 316.2122 (35 mph) and the same state-road ban.",
                        "url": MTD}},
    bans=[{"names": r"^(Donnelly Street|County Road .+|CR Old 441|Old (US |Highway )?441)$|(^|;)(US 441|SR 19|FL 19|SR 46|FL 46|CR \d+[A-Z]?|CR Old 441)($|;)", "url": MTD,
           "label": "Mount Dora Ordinance 2024-12 Sec. 42-201(D): this article does not allow a golf cart or LSV on a county, state or federal roadway"}],
    access=dict(kind="city ordinance", url=MTD, label="Mount Dora Ordinance 2024-12 (golf carts on city streets posted 30 mph or less; no state or county roads)",
                applied="public/data/regions.json rule.golf_cart; research/regions/mountdora.json bans"),
    enf=[src("Mount Dora Ordinance 2024-12", MTD), src("F.S. 316.2122", FL2122)],
    unverified=["Streets posted over 30 mph stay red for golf carts even when they are city streets. A sign that says no golf carts is not in the road data."],
    towns=[("mount-dora", "Mount Dora", 28.8025, -81.6445)],
    res=[("Mount Dora's ordinance sets the 30 mph city-street rule for registered golf carts.", "Mount Dora Ordinance 2024-12", MTD)])

add(id="pinehurst", name="Pinehurst, NC", short="Pinehurst", state="NC", slug="pinehurst",
    bbox=[35.17, -79.50, 35.22, -79.44], zoom=14,
    cover="Pinehurst, North Carolina only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True,
                        "cite": "Village of Pinehurst Code Sec. 71.17: golf carts on village streets posted 35 mph or less, not on or alongside NC 211 or US 15-501 except to cross at a signal, and not on NC 5, NC 2, Morganton Road, Page Road or Linden Road except to cross.",
                        "url": PINE}},
    bans=[],
    cart_only=[{"names": r"^(Morganton Road|Page Road|Linden Road|Page Drive|Aviemore Drive|Memorial Drive|Regional Drive)$|(^|;)(NC 211|NC 2|NC 5|US 15|US 501|US 15-501)($|;)",
                "url": PINE,
                "label": "Pinehurst Sec. 71.17: no golf carts on NC 211 or US 15-501 except a signalized crossing, and no golf carts on NC 5, NC 2, Morganton Road, Page Road, Linden Road, or Page Drive, Aviemore Drive, Memorial Drive and Regional Drive"}],
    access=dict(kind="village code", url=PINE, label="Village of Pinehurst Code Sec. 71.17",
                applied="public/data/regions.json rule.golf_cart; research/regions/pinehurst.json cart_only_bans"),
    enf=[src("Pinehurst Code Sec. 71.17", PINE), src("N.C.G.S. 160A-300.6", NC160)],
    unverified=["The hospital zoning district ban is applied by the named streets in Sec. 71.17 (Page Drive, Aviemore Drive, Memorial Drive, Regional Drive), not by the zoning polygon."],
    towns=[("pinehurst", "Pinehurst", 35.1954, -79.4695)],
    res=[("Pinehurst posts the streets where a permitted golf cart may and may not drive.", "Pinehurst Code Sec. 71.17", PINE)])

add(id="beaufort", name="Beaufort, SC", short="Beaufort", state="SC", slug="beaufort",
    bbox=[32.405, -80.72, 32.455, -80.64], zoom=14,
    cover="Beaufort, South Carolina only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "radius_mi": 4, "daylight_only": True, "cross": True,
                        "cite": "City of Beaufort Ordinance 2025/28 and S.C. Code 56-2-90: permitted golf carts on secondary roads posted 35 mph or less, within 4 miles of the registration address. Night driving needs headlights, taillights and turn signals.",
                        "url": BEAU}},
    bans=[],
    cart_only=[{"names": r"^(Ribaut Road|Boundary Street|Carteret Street|Trask Parkway|Parris Island Gateway)$|(^|;)US 21($|;)",
                "url": BEAU,
                "label": "Beaufort Ordinance 2025/28: golf carts only on secondary roads posted 35 mph or less. Ribaut Road, Boundary Street and Carteret Street (US 21) are primary roads."}],
    access=dict(kind="city ordinance", url=BEAU, label="City of Beaufort Ordinance 2025/28 (golf carts)",
                applied="public/data/regions.json rule.golf_cart; research/regions/beaufort.json cart_only_bans"),
    enf=[src("City of Beaufort Ordinance 2025/28", BEAU), src("S.C. Code 56-2-90", SC90)],
    unverified=["The 4 mile radius is a note, not a geometry limit. The ordinance allows night use when the cart has headlights, taillights and turn signals; the map keeps the state daylight flag."],
    towns=[("beaufort", "Beaufort", 32.4316, -80.6698)],
    res=[("Beaufort's 2025 ordinance is the city rule for golf carts on secondary roads.", "Beaufort Ordinance 2025/28", BEAU)])

add(id="portroyal", name="Port Royal, SC", short="Port Royal", state="SC", slug="portroyal",
    bbox=[32.355, -80.72, 32.400, -80.64], zoom=14,
    cover="Port Royal, South Carolina only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "radius_mi": 4, "daylight_only": True, "cross": True,
                        "cite": "S.C. Code 56-2-90: without a different road list, a permitted golf cart may use secondary roads posted 35 mph or less, in daylight, within 4 miles of the registration address. Port Royal has allowed equipped carts at night; that does not open a faster road.",
                        "url": SC90}},
    bans=[],
    cart_only=[{"names": r"^(Ribaut Road|Parris Island Gateway)$|(^|;)US 21($|;)", "url": SC90,
                "label": "S.C. Code 56-2-90: golf carts are not allowed on a primary highway. Ribaut Road (US 21) is a primary road."}],
    state_law=dict(text="state law, no local ordinance found",
                   law="S.C. Code 56-2-90 (secondary roads posted 35 mph or less, daylight unless the town allows equipped night use, within 4 miles). No Port Royal street list that differs from the statute was found.",
                   law_url=SC90,
                   searched="Town of Port Royal code index (portroyal.org code page); web search 'Port Royal SC golf cart ordinance'. News reports say the town allows night use with lights. The road rule used here is the state secondary-road rule."),
    enf=[src("S.C. Code 56-2-90", SC90), src("SCDPS golf cart law", SCDPS)],
    unverified=["A Port Royal night-use ordinance was reported in the press. The ordinance text naming streets was not found, so roads follow 56-2-90 and the map keeps the daylight flag."],
    towns=[("port-royal", "Port Royal", 32.3785, -80.6926)],
    res=[("South Carolina's golf cart statute is the road rule used for Port Royal.", "S.C. Code 56-2-90", SC90)])

add(id="georgetown", name="Georgetown, SC", short="Georgetown", state="SC", slug="georgetown",
    bbox=[33.355, -79.31, 33.395, -79.26], zoom=14,
    cover="Georgetown, South Carolina only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "radius_mi": 4, "daylight_only": True, "cross": True,
                        "cite": "S.C. Code 56-2-90: a permitted golf cart on a secondary road posted 35 mph or less, in daylight, within 4 miles of the registration address.",
                        "url": SC90}},
    bans=[],
    cart_only=[{"names": r"(^|;)(US 17|US 521|US 701)($|;)", "url": SC90,
                "label": "S.C. Code 56-2-90: golf carts are not allowed on a primary highway. US 17, US 521 and US 701 are primary roads."}],
    state_law=dict(text="state law, no local ordinance found",
                   law="S.C. Code 56-2-90. No City of Georgetown golf cart street list that differs from the statute was found.",
                   law_url=SC90,
                   searched="City of Georgetown code index and web search 'Georgetown SC golf cart ordinance designated streets'."),
    enf=[src("S.C. Code 56-2-90", SC90), src("SCDPS golf cart law", SCDPS)],
    unverified=["US 17 is the bypass and also uses city street names in places. Those tagged US 17, US 521 or US 701 stay red for golf carts."],
    towns=[("georgetown", "Georgetown", 33.3768, -79.2945)],
    res=[("South Carolina's golf cart statute is the road rule used for Georgetown.", "S.C. Code 56-2-90", SC90)])

add(id="horseshoebay", name="Horseshoe Bay, TX", short="Horseshoe Bay", state="TX", slug="horseshoebay",
    bbox=[30.51, -98.40, 30.58, -98.32], zoom=13,
    cover="Horseshoe Bay, Texas only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="city golf cart brochure", url=HSB,
                label="City of Horseshoe Bay golf cart brochure: Tex. Transp. Code 551.404, streets in the city posted 35 mph or less",
                applied="Texas golf cart profile in public/data/rules.json (roads posted 35 mph or less)"),
    enf=[src("City of Horseshoe Bay golf cart brochure", HSB), src("Tex. Transp. Code 551.404", TX551)],
    unverified=["The city brochure states the state 35 mph municipal rule. It does not name a separate banned-street list. RM 2147 and SH 71 stay red where they are posted over 35 or untagged as major roads."],
    towns=[("horseshoe-bay", "Horseshoe Bay", 30.5446, -98.3681)],
    res=[("Horseshoe Bay's city brochure states the Texas golf cart rule it applies inside the city.", "Horseshoe Bay golf cart brochure", HSB)])

add(id="surfside", name="Surfside Beach, TX", short="Surfside Beach", state="TX", slug="surfside",
    bbox=[28.93, -95.34, 28.98, -95.27], zoom=14,
    cover="Surfside Beach, Texas only. Pick another city in the menu above.",
    bans=[],
    cart_only=[{"names": r"^(Bluewater Highway|Fort Velasco Boulevard|Surfside Bridge|CR 257|County Road 257)$|(^|;)CR[- ]?257($|;)",
                "url": SURF,
                "label": "Surfside Beach Code Sec. 46-171: golf carts may use village streets except Surfside Bridge, Bluewater Highway (CR 257) and Fort Velasco Boulevard, which they may only cross at an intersection"}],
    access=dict(kind="village code", url=SURF, label="Surfside Beach Code Sec. 46-171 (golf carts and utility vehicles)",
                applied="research/regions/surfside.json cart_only_bans"),
    enf=[src("Surfside Beach Code Sec. 46-171", SURF), src("Village of Surfside Beach golf cart page", SURFWEB), src("Tex. Transp. Code 551.404", TX551)],
    unverified=["The pedestrian beach is not a road in this data. A beach driving lane is not mapped as a golf cart route."],
    towns=[("surfside-beach", "Surfside Beach", 28.9522, -95.2888)],
    res=[("Surfside Beach's code lists the roads golf carts must stay off.", "Surfside Beach Code Sec. 46-171", SURF)])

add(id="colonialbeach", name="Colonial Beach, VA", short="Colonial Beach", state="VA", slug="colonialbeach",
    bbox=[38.24, -76.98, 38.27, -76.95], zoom=14,
    cover="Colonial Beach, Virginia only. Pick another city in the menu above.",
    bans=[],
    cart_only=[{"names": r"^(State Route 205)$|(^|;)(VA 205|SR 205)($|;)",
                "url": COL,
                "label": "Colonial Beach Code Sec. 14-95: golf carts may not be operated on State Route 205, and may cross it only at a designated golf cart crossing"}],
    access=dict(kind="town ordinance", url=COL, label="Town of Colonial Beach golf cart ordinance (Secs. 14-90 through 14-95)",
                applied="research/regions/colonialbeach.json cart_only_bans; Virginia designated-street rule"),
    enf=[src("Colonial Beach golf cart ordinance", COL), src("Va. Code 46.2-916.3", VA9163)],
    unverified=["Virginia allows golf carts only on designated streets posted 25 mph or less. Colonial Beach's designated-street list is not digitized, so plain golf carts stay red except tagged cart paths. State Route 205 is banned on top of that."],
    towns=[("colonial-beach", "Colonial Beach", 38.2532, -76.9597)],
    res=[("Colonial Beach publishes its golf cart ordinance, including the State Route 205 ban.", "Colonial Beach golf cart ordinance", COL)])

add(id="flaglerbeach", name="Flagler Beach, FL", short="Flagler Beach", state="FL", slug="flaglerbeach",
    bbox=[29.46, -81.14, 29.49, -81.11], zoom=15,
    cover="Flagler Beach, Florida only. Pick another city in the menu above.",
    bans=[],
    cart_only=[{"names": r"^(Oceanshore Boulevard|Moody Boulevard|State Road A1A|State Road 100)$|(^|;)(A1A|SR A1A|FL A1A|SR 100|FL 100)($|;)",
                "url": FLAG,
                "label": "Flagler Beach golf cart packet: golf carts are not permitted on SR A1A (Oceanshore Boulevard) or SR 100 (Moody Boulevard). The packet allows a crossing of SR 100 at Flagler Avenue only."}],
    access=dict(kind="city golf cart packet", url=FLAG,
                label="City of Flagler Beach golf cart information packet (2026), Code Secs. 19-57 to 19-64",
                applied="research/regions/flaglerbeach.json cart_only_bans; Florida designated-street rule"),
    enf=[src("Flagler Beach golf cart information packet", FLAG), src("F.S. 316.212", FL212)],
    unverified=["The designated city-street list is not digitized, so plain golf carts stay red except tagged cart paths. SR A1A and SR 100 are banned for golf carts even where the posted limit is low."],
    towns=[("flagler-beach", "Flagler Beach", 29.4749, -81.1276)],
    res=[("Flagler Beach's golf cart packet states the registration rule and the A1A and SR 100 bans.", "Flagler Beach golf cart packet", FLAG)])

add(id="oriental", name="Oriental, NC", short="Oriental", state="NC", slug="oriental",
    bbox=[35.015, -76.71, 35.035, -76.68], zoom=15,
    cover="Oriental, North Carolina only. Pick another city in the menu above.",
    rule={"golf_cart": {"max_posted": 35, "cross": True,
                        "cite": "Town of Oriental traffic code, Chapter F, Section 16: a licensed driver may operate a golf cart on public streets in Oriental. N.C.G.S. 160A-300.6 allows that ordinance only on streets posted 35 mph or less.",
                        "url": ORI}},
    bans=[],
    access=dict(kind="town code", url=ORI, label="Town of Oriental Chapter F, Section 16 (operation of golf carts)",
                applied="public/data/regions.json rule.golf_cart max_posted 35"),
    enf=[src("Town of Oriental Chapter F, Section 16", ORI), src("N.C.G.S. 160A-300.6", NC160)],
    unverified=["Section 16 does not name a banned street. Streets posted over 35 mph stay red because that is the ceiling in N.C.G.S. 160A-300.6."],
    towns=[("oriental", "Oriental", 35.0254, -76.6938)],
    res=[("Oriental's traffic code is the local golf cart rule.", "Oriental Chapter F, Section 16", ORI)])

add(id="celina", name="Celina, OH", short="Celina", state="OH", slug="celina",
    bbox=[40.53, -84.59, 40.57, -84.54], zoom=14,
    cover="Celina, Ohio only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="city code", url=CEL, label="Celina Code Chapter 345: under-speed vehicles, including golf carts, on city streets posted 35 mph or less after a police inspection and Ohio title",
                applied="Ohio golf cart profile in public/data/rules.json"),
    enf=[src("Celina Code Chapter 345", CEL), src("Ohio Revised Code 4511.214", OH214)],
    unverified=["Chapter 345 requires an Ohio title and a Celina police inspection. Out-of-state carts are not allowed on city streets. That is a paperwork rule, not a road ban."],
    towns=[("celina", "Celina", 40.5489, -84.5702)],
    res=[("Celina's code allows inspected, titled golf carts on city streets posted 35 mph or less.", "Celina Code Chapter 345", CEL)])

add(id="capecharles", name="Cape Charles, VA", short="Cape Charles", state="VA", slug="capecharles",
    bbox=[37.25, -76.03, 37.29, -75.99], zoom=14,
    cover="Cape Charles, Virginia only. Pick another city in the menu above.",
    bans=[],
    access=dict(kind="town resolution and decal", url=CAPE,
                label="Town of Cape Charles Resolution 20250515: golf carts only in 25 mph zones; town golf cart decal required on public roads",
                applied="Virginia designated-street rule (posted 25 mph or less). The designated list is not digitized."),
    enf=[src("Cape Charles Resolution 20250515", CAPE), src("Cape Charles golf cart decals", CAPEDEC), src("Va. Code 46.2-916.3", VA9163)],
    unverified=["The town's designated-street list is not digitized, so plain golf carts stay red except tagged cart paths. Old Cape Charles Road between Bayshore Road and Cassatt Parkway was still posted 35 mph in the May 2025 resolution, which is over the 25 mph golf cart cap."],
    towns=[("cape-charles", "Cape Charles", 37.2676, -76.0171)],
    res=[("Cape Charles requires a town decal and states that golf carts operate in 25 mph zones.", "Cape Charles golf cart resolution", CAPE)])

add(id="sunlakes", name="Sun Lakes, AZ", short="Sun Lakes", state="AZ", slug="sunlakes",
    bbox=[33.19, -111.89, 33.24, -111.83], zoom=14,
    cover="Sun Lakes, Arizona only. Pick another city in the menu above.",
    bans=[{"names": r"^(North |South |East |West )?Alma School Road$", "url": SUN,
           "label": "Sun Lakes Sheriff's Posse (Maricopa County Sheriff's Office): Alma School Road at the 45 mph zone is not a golf cart road"}],
    access=dict(kind="sheriff posse notice", url=SUN,
                label="Sun Lakes Sheriff's Posse: golf carts are not allowed on roads posted over 35 mph; Alma School Road's 45 mph zone is enforced",
                applied="research/regions/sunlakes.json bans; Arizona LSV and golf cart profiles"),
    enf=[src("Sun Lakes Sheriff's Posse on golf carts", SUN), src("A.R.S. 28-966", ARS966)],
    unverified=["The posse notice is about the 45 mph stretch of Alma School Road. The whole named road inside this box is red so an untagged piece cannot show as legal."],
    towns=[("sun-lakes", "Sun Lakes", 33.2148, -111.8756)],
    res=[("The Sun Lakes Sheriff's Posse states that golf carts may not use the 45 mph part of Alma School Road.", "Sun Lakes Sheriff's Posse notice", SUN)])

add(id="morrobay", name="Morro Bay, CA", short="Morro Bay", state="CA", slug="morrobay",
    bbox=[35.35, -120.87, 35.39, -120.84], zoom=14,
    cover="Morro Bay, California only. Pick another city in the menu above.",
    bans=[{"names": r"^(US 101|U\.S\. 101)$|(^|;)US 101($|;)", "url": CVC + "21260",
           "label": "US 101 is a freeway posted well above 35 mph (no golf carts or LSVs)"}],
    state_law=dict(text="state law, no local ordinance found",
                   law="CVC 21716 (golf carts on highways posted 25 mph or less in a business or residence district) and CVC 21260 (LSVs on roads posted 35 mph or less). No Morro Bay golf cart transportation plan was found.",
                   law_url=CVC + "21716",
                   searched="City of Morro Bay municipal code index and web search 'Morro Bay golf cart ordinance' and 'Morro Bay golf cart transportation plan'."),
    enf=[src("CVC 21716", CVC + "21716"), src("CVC 21260", CVC + "21260")],
    unverified=["No city golf cart transportation plan was found, so the California state speed caps apply."],
    towns=[("morro-bay", "Morro Bay", 35.3658, -120.8499)],
    res=[("California's vehicle code is the golf cart and LSV rule used for Morro Bay.", "California golf cart rule, CVC 21716", CVC + "21716")])

add(id="pismo", name="Pismo Beach, CA", short="Pismo Beach", state="CA", slug="pismo",
    bbox=[35.13, -120.66, 35.16, -120.62], zoom=14,
    cover="Pismo Beach, California only. Pick another city in the menu above.",
    bans=[{"names": r"^(US 101|U\.S\. 101)$|(^|;)US 101($|;)", "url": CVC + "21260",
           "label": "US 101 is a freeway posted well above 35 mph (no golf carts or LSVs)"}],
    state_law=dict(text="state law, no local ordinance found",
                   law="CVC 21716 (golf carts on highways posted 25 mph or less in a business or residence district) and CVC 21260 (LSVs on roads posted 35 mph or less). No Pismo Beach golf cart transportation plan was found.",
                   law_url=CVC + "21716",
                   searched="City of Pismo Beach municipal code index and web search 'Pismo Beach golf cart ordinance' and 'Pismo Beach golf cart transportation plan'."),
    enf=[src("CVC 21716", CVC + "21716"), src("CVC 21260", CVC + "21260")],
    unverified=["No city golf cart transportation plan was found, so the California state speed caps apply. Price Street (CA 1) is not given a separate ban; it stays red where the posted or inferred limit is over the cap."],
    towns=[("pismo-beach", "Pismo Beach", 35.1428, -120.6413)],
    res=[("California's vehicle code is the golf cart and LSV rule used for Pismo Beach.", "California golf cart rule, CVC 21716", CVC + "21716")])

add(id="howey", name="Howey-in-the-Hills, FL", short="Howey-in-the-Hills", state="FL", slug="howey",
    bbox=[28.69, -81.80, 28.74, -81.74], zoom=14,
    cover="Howey-in-the-Hills, Florida only. Pick another city in the menu above.",
    access=dict(kind="police registration letter", url=HOWEY,
                label="Howey-in-the-Hills Police: town ordinance requires annual golf cart registration. The designated street list is not in the letter.",
                applied="Florida designated-street rule (F.S. 316.212). Street list not digitized, so plain golf carts stay red except tagged cart paths."),
    enf=[src("Howey-in-the-Hills Police golf cart registration letter (2026)", HOWEY), src("F.S. 316.212", FL212), src("F.S. 316.2122", FL2122)],
    unverified=["The police letter requires registration under the town ordinance and does not list streets. Plain golf carts stay red except tagged cart paths."],
    towns=[("howey-in-the-hills", "Howey-in-the-Hills", 28.7169, -81.7734)],
    res=[("Howey-in-the-Hills police publish the annual golf cart registration requirement.", "Howey-in-the-Hills golf cart letter", HOWEY)])

add(id="apalachicola", name="Apalachicola, FL", short="Apalachicola", state="FL", slug="apalachicola",
    bbox=[29.715, -85.04, 29.745, -84.97], zoom=15,
    cover="Apalachicola, Florida only. Pick another city in the menu above.",
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.212 (golf carts only on designated, signed streets) and F.S. 316.2122 (LSVs on roads posted 35 mph or less). The city fee schedule charges a golf cart registration under an ordinance. The street list was not found.",
                   law_url=FL212,
                   searched="City of Apalachicola fee schedule (golf cart registration per ordinance); web search 'Apalachicola golf cart ordinance designated streets'. The street list was not online."),
    enf=[src("F.S. 316.212", FL212), src("City of Apalachicola fee schedule (golf cart registration)", APAL), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["A registration fee is not a street list. Plain golf carts stay red except tagged cart paths."],
    towns=[("apalachicola", "Apalachicola", 29.7258, -84.9924)],
    res=[("Apalachicola charges a golf cart registration. The designated streets were not published with it.", "Apalachicola fee schedule", APAL)])

add(id="cedarkey", name="Cedar Key, FL", short="Cedar Key", state="FL", slug="cedarkey",
    bbox=[29.12, -83.06, 29.15, -83.02], zoom=15,
    cover="Cedar Key, Florida only. Pick another city in the menu above.",
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.212 (golf carts only on streets the city designates and signs) and F.S. 316.2122 (LSVs on roads posted 35 mph or less). A Florida Attorney General opinion discusses Cedar Key's questions about that statute. No current designated-street list was found.",
                   law_url=FL212,
                   searched="Florida Attorney General opinion on Cedar Key golf carts; web search 'Cedar Key golf cart ordinance designated streets'. No current street list was found."),
    enf=[src("F.S. 316.212", FL212), src("Florida Attorney General opinion, Cedar Key golf carts", CEDAR), src("F.S. 316.2122", FL2122)],
    unverified=["No current designated-street list was found, so plain golf carts stay red except tagged cart paths."],
    towns=[("cedar-key", "Cedar Key", 29.1386, -83.0351)],
    res=[("Florida's golf cart statute is the rule used for Cedar Key until a street list is published.", "Florida golf cart statute, F.S. 316.212", FL212)])

add(id="islamorada", name="Islamorada, FL", short="Islamorada", state="FL", slug="islamorada",
    bbox=[24.90, -80.70, 24.96, -80.55], zoom=13,
    cover="Islamorada (Upper Matecumbe and the nearby village islands in this box) only. Pick another city in the menu above.",
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.212 (golf carts only on designated, signed streets) and F.S. 316.2122 (LSVs on roads posted 35 mph or less). No Village of Islamorada designated-street list was found on an official page.",
                   law_url=FL2122,
                   searched="Web search 'Islamorada golf cart ordinance designated streets'; village council materials. A street list on an official village page was not found."),
    enf=[src("F.S. 316.2122", FL2122), src("F.S. 316.212", FL212), src("FLHSMV low-speed vehicles", FLHSMV)],
    unverified=["Overseas Highway (US 1) is red where it is posted over 35 mph or untagged as a major road. Plain golf carts stay red except tagged cart paths."],
    towns=[("islamorada", "Islamorada", 24.9243, -80.6278)],
    res=[("Florida's LSV statute is the road rule used for Islamorada.", "Florida LSV statute, F.S. 316.2122", FL2122)])

add(id="keylargo", name="Key Largo, FL", short="Key Largo", state="FL", slug="keylargo",
    bbox=[25.08, -80.47, 25.14, -80.39], zoom=13,
    cover="Key Largo town center only, not the whole island. Pick another city in the menu above.",
    state_law=dict(text="state law, no local ordinance found",
                   law="F.S. 316.212 (golf carts only on designated, signed streets) and F.S. 316.2122 (LSVs on roads posted 35 mph or less). Key Largo is unincorporated Monroe County. No county designated-street list for this area was found.",
                   law_url=FL2122,
                   searched="Monroe County code and web search 'Key Largo golf cart ordinance designated streets'. No street list for this area was found."),
    enf=[src("F.S. 316.2122", FL2122), src("F.S. 316.212", FL212)],
    unverified=["This box is the town center, not all of Key Largo. Overseas Highway stays red where it is posted over 35 mph."],
    towns=[("key-largo", "Key Largo", 25.0865, -80.4473)],
    res=[("Florida's LSV statute is the road rule used for Key Largo.", "Florida LSV statute, F.S. 316.2122", FL2122)])

add(id="crystalriver", name="Crystal River, FL", short="Crystal River", state="FL", slug="crystalriver",
    bbox=[28.87, -82.64, 28.93, -82.54], zoom=14,
    cover="Crystal River, Florida only. Pick another city in the menu above.",
    bans=[{"names": r"^(US 19|US Highway 19)$|(^|;)US 19($|;)", "url": CRRES,
           "label": "Crystal River's golf cart resolution allows carts up to a point east of US 19. It does not authorize driving along US 19."}],
    access=dict(kind="city code and resolution", url=CRCODE,
                label="Crystal River Code Secs. 15-80 to 15-82 (golf carts on streets designated by resolution). The resolution in hand names SE 8th Avenue between SE Governors Boulevard and 250 feet east of US 19.",
                applied="US 19 ban. The short SE 8th Avenue piece is not split out, so plain golf carts stay red except tagged cart paths."),
    enf=[src("Crystal River Code Chapter 15", CRCODE), src("Crystal River golf cart street resolution", CRRES), src("F.S. 316.212", FL212)],
    unverified=["The resolution designates SE 8th Avenue only between SE Governors Boulevard and 250 feet east of US 19. That piece is shorter than the whole street, so it is not painted green."],
    towns=[("crystal-river", "Crystal River", 28.9022, -82.5926)],
    res=[("Crystal River's code allows golf carts only on streets a resolution designates.", "Crystal River Code Chapter 15", CRCODE)])

def region_entry(r):
    t = r["towns"][0]
    o = {"id": r["id"], "name": r["name"], "short": r["short"], "state": r["state"], "center": [t[2], t[3]], "zoom": r["zoom"],
         "bbox": r["bbox"], "cover": r["cover"], "slug": r["slug"]}
    if r.get("rule"): o["rule"] = r["rule"]
    return o

def cfg_entry(r):
    c = {"poly": rect(*r["bbox"]), "bans": r.get("bans", []), "unverified": r.get("unverified", []),
         "sources": [f'{x["label"]} {x["url"]}' for x in r["enf"]] + ["OpenStreetMap", "FHWA HPMS speed limits"],
         "enforcement": {"checked": DAY,
                         "result": "bans_applied" if (r.get("bans") or r.get("cart_only") or r.get("designated")) else "none_found",
                         "sources": r["enf"],
                         "note": "Posted signs do not lift a ban. A designated street list that is not digitized stays red for plain golf carts."},
         "status": f"Added (regions-100, {DAY})"}
    if r.get("cart_only"): c["cart_only_bans"] = r["cart_only"]
    if r.get("designated"): c["designated_names"] = r["designated"]
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
    if len(R) < 24: sys.exit("need at least 24 regions")

def main():
    check_boxes()
    regs = J("public/data/regions.json"); ids = {r["id"] for r in R}
    old = {x["id"]: x for x in regs}
    regs = [x for x in regs if x["id"] not in ids]
    for r in R:
        e = region_entry(r)
        if r["id"] in old and old[r["id"]].get("beta"): e["beta"] = True
        regs.append(e)
    W("public/data/regions.json", regs)
    os.makedirs(os.path.join(ROOT, "research/regions"), exist_ok=True)
    for r in R: W(f"research/regions/{r['id']}.json", cfg_entry(r))
    acc = J("research/access_sources.json")
    for r in R:
        if "access" in r:
            acc["regions"][r["id"]] = r["access"]; acc.get("state_law", {}).pop(r["id"], None)
        else:
            acc.setdefault("state_law", {})[r["id"]] = r["state_law"]; acc["regions"].pop(r["id"], None)
    W("research/access_sources.json", acc)
    vb = J("research/validation_baseline.json")
    for r in R: vb["red_islands"].setdefault(r["id"], 0)
    W("research/validation_baseline.json", vb)
    rr = J("content/region_resources.json")
    for r in R:
        if r["res"]: rr[r["slug"]] = [{"lead": a, "name": b, "url": c} for a, b, c in r["res"]]
    W("content/region_resources.json", rr)
    print(len(regs), "regions total;", len(R), "upserted:", " ".join(x["id"] for x in R))

if __name__ == "__main__":
    main()
