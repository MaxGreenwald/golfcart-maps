"""Town-page profiles for the 24 regions added to reach 100. Imported by gen_town_pages.py.
Every rule line carries the official source. The same sources are in research/regions/<id>.json."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research"))
import regions100_setup as S
P, T, RID = {}, [], {}
def prof(rid, a, gc, lsv, rules, banned, faq, q="Can you drive a golf cart in {n}?"):
    r = next(x for x in S.R if x["id"] == rid)
    P[rid] = dict(q=q, a=a, gc=dict(zip(("allowed", "roads", "speed_line", "notes"), gc)),
                  lsv=dict(zip(("allowed", "roads", "speed_line", "notes"), lsv)),
                  rules=rules, banned=banned, faq=faq, sources=sorted({x["url"] for x in r["enf"]}), day="2026-11-06")
    RID[r["slug"]] = rid
    for slug, name, lat, lng in r["towns"]: T.append((r["slug"], slug, name, r["state"], lat, lng))

FLGC = ("Golf carts", "Plain golf carts only on roads a city or county has designated and signed for carts", "F.S. 316.212", S.FL212)
FLLSV = ("LSV roads", "Registered, insured LSVs on roads posted 35 mph or less; cross faster roads only at intersections", "F.S. 316.2122", S.FL2122)
NCLSVR = ("LSV roads", "Registered, insured LSVs on roads posted 35 mph or less; may cross faster roads at intersections", "N.C.G.S. 20-121.1", S.NCLSV)
SCGC = ("Golf carts", "Permitted golf carts on secondary roads posted 35 mph or less, in daylight, within 4 miles of the registration address or a gated-community entrance, unless the city sets different hours or roads. Night driving under an ordinance needs working headlights and taillights.", "S.C. Code 56-2-90", S.SC90)
TXGC = ("Golf carts", "Golf carts with the required plate and equipment on roads posted 35 mph or less where the city or county allows them, in daylight", "Tex. Transp. Code 551.404", S.TX551)
TXLSV = ("LSV roads", "A registered neighborhood electric vehicle may use a road posted 45 mph or less and may not travel faster than 35 mph. This map plans on 35 mph or less.", "Tex. Transp. Code 551.303", S.TX303)
VAGC = ("Golf carts", "Golf carts only on streets the town designates, posted 25 mph or less, sunrise to sunset unless equipped", "Va. Code 46.2-916.3", S.VA9163)
VALSV = ("LSV roads", "LSVs on highways posted 35 mph or less", "Va. Code 46.2-908.3", S.VA9083)
CAGC = ("Golf carts", "Golf carts on highways posted 25 mph or less in a business or residence district", "CVC 21716", S.CVC + "21716")
CALSV = ("LSV roads", "LSVs on roads posted 35 mph or less; they may cross faster roads at intersections", "CVC 21260", S.CVC + "21260")

prof("fairhope", "Street-legal LSVs yes, plain golf carts no. In {n}, the city's safety plan allows LSVs on streets posted 35 mph or less. They may cross Greeno Road (US 98). They may not drive along it.",
     ("no", "Not on public roads", "n/a", "No plain-golf-cart ordinance found"),
     ("yes", "Streets posted 35 mph or less", "35 mph", "Not along Greeno Road"),
     [("LSVs", "LSVs on streets posted 35 mph or less. They may cross faster roads. They may not travel along Greeno Road (US 98).", "City of Fairhope Safe Streets plan", S.FAIR),
      ("Golf carts", "No Fairhope ordinance allowing plain golf carts on public streets was found", "City of Fairhope Safe Streets plan", S.FAIR)],
     [("Greeno Road (US 98)", "No LSVs along the road; cross at Fairhope Avenue or Morphy Avenue", True)],
     [("Can I drive a regular golf cart in {n}?", "No. Fairhope's published rule is for low-speed vehicles, not plain golf carts."),
      ("Can I drive an LSV on Greeno Road?", "No. The city's safety plan says LSVs may not travel along Greeno Road. They may cross it.")])

prof("ocracoke", "Yes, inside the village. Hyde County's ordinance, as the sheriff quotes it, allows a golf cart on public streets posted 35 mph or less. The driver must be at least 16. This map is the village only.",
     ("yes", "Village streets posted 35 mph or less", "35 mph", "Driver at least 16; lights and a seat for each rider"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts on public streets in Hyde County where the speed limit is 35 mph or less", "Hyde County Ordinance 2009-09-01 (sheriff reminder)", S.OCR),
      ("Age", "No person under 16 may operate a golf cart on a public street", "N.C.G.S. 153A-245", S.NC153), NCLSVR],
     [("NC 12 north of the village", "Outside this map", False)],
     [("Can I take a golf cart up NC 12 to the ferry?", "This map covers the village. The highway north of the village is not in it."),
      ("How old do you have to be to drive a golf cart in {n}?", "At least 16, under the county statute the sheriff cites.")])

prof("dadecity", "Yes, on the city's list. {n} lets a registered golf cart use specific city streets under Ordinance 2024-01. State and county roads, including US 301, US 98 and SR 52, are not on that list. LSVs may use roads posted 35 mph or less.",
     ("limited", "The streets named in the city resolution", "n/a", "City registration and insurance"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not on a road the city has closed"),
     [("Golf carts", "Registered golf carts on the city streets listed in the resolution under Ordinance 2024-01. Not on state or county roads.", "Dade City golf cart packet", S.DADE), FLGC, FLLSV],
     [("US 301, US 98 and SR 52", "No golf carts", True)],
     [("Which streets allow a golf cart in {n}?", "The city's list includes Sumner Avenue, Martin Luther King Boulevard, the numbered streets from 2nd through 12th, and the avenues named in the registration packet."),
      ("Can I drive a golf cart on US 301 in {n}?", "No. Ordinance 2024-01 does not authorize golf carts on state or county roads.")])

prof("mountdora", "Yes, on city streets posted 30 mph or less. {n} lets a registered golf cart use those streets unless a sign says no golf carts. County, state and federal roads, including Donnelly Street (US 441), are closed to carts and LSVs.",
     ("yes", "City streets posted 30 mph or less", "30 mph", "Not on state or county roads"),
     ("limited", "City streets posted 35 mph or less, not state or county roads", "35 mph", "Registered and insured"),
     [("Golf carts", "Registered golf carts on a city right of way posted 30 mph or less, 24 hours, unless posted no golf carts", "Mount Dora Ordinance 2024-12", S.MTD),
      ("State roads", "The ordinance does not allow a golf cart or LSV on a county, state or federal roadway", "Mount Dora Ordinance 2024-12", S.MTD), FLLSV],
     [("Donnelly Street (US 441)", "State road; no golf carts or LSVs", True), ("SR 19 and SR 46", "State roads", True)],
     [("Can I drive a golf cart on Donnelly Street?", "No. Donnelly Street is US 441, a state road, and the ordinance does not allow carts or LSVs on state roads."),
      ("What is the golf cart speed cap in {n}?", "30 mph. A city street posted over 30 mph is closed to golf carts.")])

prof("pinehurst", "Yes, with a village sticker, except the named roads. In {n}, golf carts may use streets posted 35 mph or less. They may not drive on NC 211 or US 15-501 except to cross at a traffic signal, and they may not drive on NC 2, NC 5, Morganton Road, Page Road or Linden Road.",
     ("yes", "Village streets posted 35 mph or less, not the named roads", "35 mph", "Village sticker; driver's license"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Streets posted 35 mph or less. Not NC 211 or US 15-501 except a signalized crossing. Not NC 2, NC 5, Morganton Road, Page Road or Linden Road except to cross.", "Pinehurst Code Sec. 71.17", S.PINE),
      ("Hospital area", "No golf carts on Page Drive, Aviemore Drive, Memorial Drive or Regional Drive", "Pinehurst Code Sec. 71.17", S.PINE), NCLSVR],
     [("NC 211 and US 15-501", "Cross only at a signal", True), ("NC 2, NC 5, Morganton Road, Page Road, Linden Road", "Cross only", True),
      ("Page Drive, Aviemore Drive, Memorial Drive, Regional Drive", "No golf carts", False)],
     [("Can I drive a golf cart on NC 211 in {n}?", "No, except to cross it at a traffic signal."),
      ("Do I need a sticker in {n}?", "Yes. The village requires a registration sticker on the front and rear.")])

prof("beaufort", "Yes, on secondary roads. In {n}, a permitted golf cart may use secondary roads posted 35 mph or less, within 4 miles of the address on the registration. Ribaut Road, Boundary Street and Carteret Street are primary roads. At night the cart needs headlights, taillights and turn signals.",
     ("yes", "Secondary roads posted 35 mph or less", "35 mph", "Within 4 miles; night only if equipped"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [SCGC, ("City rule", "Secondary roads posted 35 mph or less. Night use requires headlights, taillights and turn signals. Seat belts are required.", "Beaufort Ordinance 2025/28", S.BEAU)],
     [("Ribaut Road, Boundary Street and Carteret Street (US 21)", "Primary roads; no golf carts", True)],
     [("Can I drive a golf cart on Ribaut Road?", "No. It is a primary road. Golf carts may cross a faster road at an intersection with a control."),
      ("Can I drive a golf cart at night in {n}?", "Yes, if the cart has working headlights, taillights and turn signals, on a secondary road posted 35 mph or less.")])

prof("portroyal", "Yes, under the state rule. In {n}, a permitted golf cart may use secondary roads posted 35 mph or less, within 4 miles of the registration address. Ribaut Road is a primary road. The town has allowed equipped carts at night; a faster road is still closed.",
     ("yes", "Secondary roads posted 35 mph or less", "35 mph", "Within 4 miles"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [SCGC, ("Primary roads", "Golf carts are not allowed on a primary highway such as US 21 (Ribaut Road)", "S.C. Code 56-2-90", S.SC90)],
     [("Ribaut Road (US 21)", "Primary road; no golf carts", True)],
     [("Can I drive a golf cart on Ribaut Road in {n}?", "No. It is a primary highway."),
      ("Can I drive a golf cart at night in {n}?", "The town has allowed night use when the cart has lights. The road still has to be a secondary road posted 35 mph or less.")])

prof("georgetown", "Yes, under the state rule. In {n}, a permitted golf cart may use secondary roads posted 35 mph or less, in daylight, within 4 miles of the registration address. US 17, US 521 and US 701 are primary highways.",
     ("yes", "Secondary roads posted 35 mph or less", "35 mph", "Daylight; within 4 miles"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [SCGC, ("Primary highways", "No golf carts on US 17, US 521 or US 701", "S.C. Code 56-2-90", S.SC90)],
     [("US 17, US 521 and US 701", "Primary highways; no golf carts", True)],
     [("Can I drive a golf cart on US 17 in {n}?", "No. US 17 is a primary highway."),
      ("How far can I drive from home?", "Within 4 miles of the address on the cart's registration, on a secondary road posted 35 mph or less.")])

prof("horseshoebay", "Yes, on streets posted 35 mph or less. {n} tells residents that Texas law lets a city allow a licensed driver to operate an equipped golf cart on a public road inside the city posted 35 mph or less.",
     ("yes", "City streets posted 35 mph or less", "35 mph", "Licensed driver; slow-moving emblem if under 25 mph"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "A municipality may allow golf carts on a public highway inside the city posted 35 mph or less. The driver must be licensed, and the cart needs lights, reflectors, a parking brake and mirrors.", "Horseshoe Bay golf cart brochure", S.HSB), TXGC],
     [("RM 2147 and SH 71 where posted over 35 mph", "Over the golf cart cap", True)],
     [("Can I drive a golf cart on RM 2147?", "Only where it is posted 35 mph or less. Much of it is posted higher."),
      ("Do I need a license to drive a golf cart in {n}?", "Yes. The city brochure says only a licensed driver may operate a golf cart on a public road.")])

prof("surfside", "Yes, except three roads. In {n}, golf carts may use village streets. They may not drive on the Surfside Bridge, Bluewater Highway (CR 257) or Fort Velasco Boulevard, except to cross at an intersection. The driver needs a license, and the cart needs a Texas golf cart plate.",
     ("yes", "Village streets, not the bridge, Bluewater Highway or Fort Velasco Boulevard", "35 mph", "License plate and a licensed driver"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "All village streets except Surfside Bridge, Bluewater Highway (CR 257) and Fort Velasco Boulevard, which may be crossed at an intersection", "Surfside Beach Code Sec. 46-171", S.SURF), TXGC],
     [("Bluewater Highway (CR 257)", "Cross only", True), ("Fort Velasco Boulevard", "Cross only", True), ("Surfside Bridge", "No golf carts", False)],
     [("Can I drive a golf cart on Bluewater Highway?", "No, except to cross it at an intersection."),
      ("Can I drive a golf cart on the beach in {n}?", "The pedestrian beach is closed to golf carts, with a narrow exception for a displayed disabled placard. A beach vehicle pass is a separate rule.")])

prof("colonialbeach", "Only on designated streets posted 25 mph or less. {n} bars golf carts from State Route 205 except a marked crossing. That street list is not on this map yet, so plain golf carts stay red except a tagged cart path.",
     ("limited", "Designated streets posted 25 mph or less", "25 mph", "Not on State Route 205; list not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [VAGC, ("State Route 205", "No golf carts on State Route 205. Cross only at a designated golf cart crossing.", "Colonial Beach Code Sec. 14-95", S.COL), VALSV],
     [("State Route 205", "No golf carts; designated crossing only", True)],
     [("Can I drive a golf cart on State Route 205?", "No. You may cross it only at a crossing the town and VDOT have marked."),
      ("Why are most streets red for a golf cart?", "Virginia requires a designated street posted 25 mph or less. That list is not digitized, so plain golf carts stay off streets that are not tagged cart paths.")])

prof("flaglerbeach", "Only on designated city streets. {n} requires registration, and golf carts may not travel on SR A1A (Oceanshore Boulevard) or SR 100 (Moody Boulevard). They may cross SR 100 at Flagler Avenue. The designated-street list is not drawn here yet, so plain golf carts stay red except tagged cart paths. LSVs may use roads posted 35 mph or less.",
     ("limited", "Designated city streets only", "n/a", "Not A1A or SR 100; list not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("A1A and SR 100", "Golf carts are not permitted on SR A1A or SR 100. They may cross SR 100 at Flagler Avenue.", "Flagler Beach golf cart packet", S.FLAG), FLGC, FLLSV],
     [("SR A1A (Oceanshore Boulevard)", "No golf carts", True), ("SR 100 (Moody Boulevard)", "No golf carts; cross at Flagler Avenue", True)],
     [("Can I drive a golf cart on A1A in {n}?", "No. The city packet says golf carts are not permitted on SR A1A."),
      ("Can I cross SR 100?", "Yes, at the Flagler Avenue intersection. Other crossings of SR 100 or A1A are not the city's exception.")])

prof("oriental", "Yes. {n} allows a licensed driver to operate a golf cart on public streets. State law lets the town do that on streets posted 35 mph or less. The cart needs a mirror and brake lights, and lights if you drive after dark.",
     ("yes", "Public streets posted 35 mph or less", "35 mph", "Licensed driver"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "A licensed driver may operate a golf cart on public streets in town. After dark the cart needs headlights, turn signals and brake lights.", "Oriental Chapter F, Section 16", S.ORI),
      ("Speed", "A city may allow golf carts on streets posted 35 mph or less", "N.C.G.S. 160A-300.6", S.NC160), NCLSVR],
     [("NC 55 where posted over 35 mph", "Over the golf cart cap", True)],
     [("Can I drive a golf cart on NC 55 in {n}?", "Only where it is posted 35 mph or less. Faster stretches stay closed."),
      ("Do I need lights?", "Yes, if you drive during the hours of darkness. A mirror and brake lights are required at all times.")])

prof("celina", "Yes, after an inspection. {n} allows an under-speed vehicle, including a golf cart, on city streets posted 35 mph or less once it passes a police inspection and has an Ohio title and registration. Out-of-state carts are not allowed on city streets.",
     ("yes", "City streets posted 35 mph or less", "35 mph", "Ohio title, police inspection, licensed driver"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Under-speed vehicles, including golf carts, on city streets posted 35 mph or less after inspection and Ohio registration", "Celina Code Chapter 345", S.CEL),
      ("State rule", "Under-speed vehicles on roads posted 35 mph or less where the local authority allows them", "Ohio Revised Code 4511.214", S.OH214)],
     [("Streets posted over 35 mph", "Closed to golf carts", True)],
     [("Can I bring an out-of-state golf cart to {n}?", "No. The code says out-of-state multi-use vehicles are not permitted on city streets."),
      ("Do I need a police inspection?", "Yes, before the cart is used on a city street, plus an Ohio title and registration.")])

prof("capecharles", "Only on designated streets posted 25 mph or less, with a town decal. {n} follows that Virginia cap. The street list is not on this map yet, so plain golf carts stay red except a tagged cart path. LSVs may use roads posted 35 mph or less.",
     ("limited", "Designated streets posted 25 mph or less", "25 mph", "Town decal; list not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [VAGC, ("Town decal", "A golf cart on a public road in town needs a current town decal", "Cape Charles golf cart decals", S.CAPEDEC),
      ("25 mph", "The town states that golf carts operate in 25 mph zones", "Cape Charles Resolution 20250515", S.CAPE), VALSV],
     [("Old Cape Charles Road where it is posted 35 mph", "Over the 25 mph golf cart cap", True)],
     [("Do I need a decal in {n}?", "Yes. The town requires a golf cart decal on carts driven on public roads."),
      ("Can I drive a golf cart on a 35 mph road?", "No. The town and Virginia law keep golf carts to streets posted 25 mph or less.")])

prof("sunlakes", "Yes, on roads posted 35 mph or less. The Sun Lakes Sheriff's Posse says golf carts are not allowed on a road posted over 35 mph, and it names the 45 mph zone of Alma School Road. That road is red on this map.",
     ("yes", "Streets posted 35 mph or less", "35 mph", "Not Alma School Road"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Alma School Road", "The 45 mph zone is not a golf cart road", "Sun Lakes Sheriff's Posse", S.SUN),
      ("LSVs", "Neighborhood electric vehicles on roads posted 35 mph or less", "A.R.S. 28-966", S.ARS966)],
     [("Alma School Road", "No golf carts or LSVs", True)],
     [("Can I drive a golf cart on Alma School Road?", "No. The posse says the 45 mph zone is enforced, and this map keeps the whole named road red."),
      ("What is the speed cap in {n}?", "35 mph. A road posted over 35 mph is closed.")])

prof("morrobay", "Yes, with the California caps. In {n}, a golf cart may use a street posted 25 mph or less in a business or residence district. An LSV may use a road posted 35 mph or less. US 101 is a freeway and is closed to both.",
     ("yes", "Streets posted 25 mph or less", "25 mph", "Business or residence district"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [CAGC, CALSV, ("US 101", "Freeway; no golf carts or LSVs", "CVC 21260", S.CVC + "21260")],
     [("US 101", "No golf carts or LSVs", False)],
     [("Can I drive a golf cart on a 25 mph street in {n}?", "Yes, in a business or residence district, under CVC 21716."),
      ("Can an LSV use a 35 mph road?", "Yes. California limits LSVs to roads posted 35 mph or less.")])

prof("pismo", "Yes, with the California caps. In {n}, a golf cart may use a street posted 25 mph or less in a business or residence district. An LSV may use a road posted 35 mph or less. US 101 is closed to both.",
     ("yes", "Streets posted 25 mph or less", "25 mph", "Business or residence district"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [CAGC, CALSV, ("US 101", "Freeway; no golf carts or LSVs", "CVC 21260", S.CVC + "21260")],
     [("US 101", "No golf carts or LSVs", False)],
     [("Can I drive a golf cart downtown in {n}?", "On a street posted 25 mph or less in a business or residence district, yes."),
      ("Can an LSV drive on Price Street?", "Only where it is posted 35 mph or less. Faster stretches are closed.")])

prof("howey", "Street-legal LSVs yes. Plain golf carts only on streets the town has designated, and that list is not drawn here. {n} police require every golf cart to be registered each year. Until the street list is on the map, plan on an LSV.",
     ("limited", "Designated streets only", "n/a", "Annual registration; list not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Registration", "The town ordinance and state law require golf carts to be registered each calendar year", "Howey-in-the-Hills Police", S.HOWEY), FLGC, FLLSV],
     [],
     [("Do I need a sticker in {n}?", "Yes. Police say registration opens January 1 and the sticker goes on the rear of the cart."),
      ("Why are the streets red for a golf cart?", "Florida allows golf carts only on designated streets. The town's list is not digitized, so those streets are not shown as golf cart roads.")])

prof("apalachicola", "Street-legal LSVs yes. Plain golf carts only on streets the city designates, and that list was not found. {n} charges a golf cart registration fee. This map does not turn a street green for a golf cart without the street list. LSVs may use roads posted 35 mph or less.",
     ("limited", "Designated streets only", "n/a", "Street list not found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, ("Registration", "The city fee schedule charges a golf cart registration under an ordinance", "Apalachicola fee schedule", S.APAL), FLLSV],
     [],
     [("Can I drive a regular golf cart in {n}?", "Only on a street the city has designated and signed. That list was not found, so this map does not show those streets as golf cart roads."),
      ("Can I drive an LSV in {n}?", "Yes, on a road posted 35 mph or less.")])

prof("cedarkey", "Street-legal LSVs yes. Plain golf carts only on streets the city designates and signs. No current street list for {n} was found, so plain golf carts stay red except a tagged cart path. LSVs may use roads posted 35 mph or less.",
     ("limited", "Designated streets only", "n/a", "No current street list found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, ("Local questions", "A Florida Attorney General opinion discusses how F.S. 316.212 applies when Cedar Key regulates golf carts", "Florida Attorney General opinion", S.CEDAR), FLLSV],
     [],
     [("Can I drive a regular golf cart on the island?", "Only on a street the city has designated and signed. No current list was found, so this map does not show island streets as golf cart roads."),
      ("Can I drive an LSV in {n}?", "Yes, on a road posted 35 mph or less.")])

prof("islamorada", "Street-legal LSVs yes. Plain golf carts only on designated streets, and no official street list was found for {n}. LSVs may use roads posted 35 mph or less. US 1 stays closed where it is posted higher.",
     ("limited", "Designated streets only", "n/a", "Street list not found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, FLLSV],
     [("US 1 (Overseas Highway) where posted over 35 mph", "No LSVs", True)],
     [("Can I drive an LSV on US 1 in {n}?", "Only where it is posted 35 mph or less. Much of Overseas Highway is posted higher."),
      ("Can I drive a regular golf cart on a side street?", "Only if the village has designated and signed that street. No official list was found, so this map does not show those streets as golf cart roads.")])

prof("keylargo", "Street-legal LSVs yes. Plain golf carts only on designated streets, and no county street list was found for {n}. This map is the town center, not the whole island. LSVs may use roads posted 35 mph or less.",
     ("limited", "Designated streets only", "n/a", "Street list not found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, FLLSV],
     [("US 1 (Overseas Highway) where posted over 35 mph", "No LSVs", True)],
     [("Can I drive an LSV on a side street in {n}?", "Yes, where it is posted 35 mph or less."),
      ("Does this map cover all of Key Largo?", "No. It covers the town center in this box.")])

prof("crystalriver", "Street-legal LSVs yes. Plain golf carts only on streets a city resolution designates. The resolution in hand names one stretch of SE 8th Avenue, between SE Governors Boulevard and a point just east of US 19. That piece is not split out on this map, so plain golf carts stay red. US 19 itself is not a golf cart road.",
     ("limited", "Resolution streets only", "n/a", "SE 8th Avenue piece not drawn"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not along US 19"),
     [("Golf carts", "Golf carts only on streets designated by resolution. The resolution names SE 8th Avenue between SE Governors Boulevard and 250 feet east of US 19.", "Crystal River resolution", S.CRRES),
      ("Code", "The city authorizes golf carts on designated streets, with a driver's license and insurance", "Crystal River Code Secs. 15-80 to 15-82", S.CRCODE), FLLSV],
     [("US 19", "No golf carts along the highway", True)],
     [("Can I drive a golf cart on US 19?", "No. The resolution does not authorize driving along US 19."),
      ("Is SE 8th Avenue shown as a golf cart road?", "Not on this map. The designated piece is shorter than the whole street, so it is left red rather than painting the whole avenue green.")])
