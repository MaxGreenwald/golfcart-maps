"""Town-page profiles for the regions-25-batch regions (Oct 22 2026). Imported by gen_town_pages.py.
Every rule line carries the official (or best available) source; the same sources are in research/regions/<id>.json."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research"))
import regions25_setup as S
FLS = S.FLS; NJ = S.NJMVC; FLH = S.FLHSMV; NC = S.NCLSV; SC = S.SCDPS
P, T, RID = {}, [], {}
def prof(rid, a, gc, lsv, rules, banned, faq, q="Can you drive a golf cart in {n}?"):
    r = next(x for x in S.R if x["id"] == rid)
    P[rid] = dict(q=q, a=a, gc=dict(zip(("allowed", "roads", "speed_line", "notes"), gc)), lsv=dict(zip(("allowed", "roads", "speed_line", "notes"), lsv)),
                  rules=rules, banned=banned, faq=faq, sources=sorted({x["url"] for x in r["enf"]}))
    RID[r["slug"]] = rid
    for slug, name, lat, lng in r["towns"]: T.append((r["slug"], slug, name, r["state"], lat, lng))
NJLSV = ("LSV roads", "LSVs only on roads posted 25 mph or less; they may cross faster roads at intersections", "NJ MVC low-speed vehicles", NJ)
NJGC = ("Golf carts", "Plain golf carts aren't street-legal; only titled, registered and insured LSVs that meet 49 CFR 571.500", "NJ MVC low-speed vehicles", NJ)
FLGC = ("Golf carts", "Plain golf carts only on roads a city or county has designated and signed for carts", "F.S. 316.212", FLS + "316.212")
FLLSV = ("LSV roads", "Registered, insured LSVs on roads posted 35 mph or less; cross faster roads only at intersections", "FLHSMV low-speed vehicles", FLH)
NCLSVR = ("LSV roads", "Registered, insured LSVs on roads posted 35 mph or less; may cross faster roads at intersections", "N.C.G.S. 20-121.1", NC)
SCGC = ("Golf carts (SC law)", "Permitted, insured golf carts on secondary roads posted 35 mph or less, in daylight, within 4 miles of the registration address", "S.C. golf cart law (SCDPS)", SC)

prof("ocnj", "Street-legal LSVs yes, plain golf carts no. In {n}, registered LSVs may use roads posted 25 mph or less, but not Bay Ave, West Ave, Route 52, the 34th Street bridge or Ocean Drive south of South Inlet Drive.",
     ("no", "Not on public roads", "n/a", "Not street-legal in NJ"), ("yes", "Roads posted 25 mph or less", "25 mph", "Cross Bay Ave and West Ave at intersections"),
     [NJGC, NJLSV, ("Banned roads", "No LSVs on Bay Ave, West Ave, Route 52, the 34th St bridge or Ocean Dr south of South Inlet Dr", "Ocean City Police LSV facts", "https://www.ocnj.us/media/Police/LSV%27s.pdf")],
     [("Bay Avenue", "No LSVs; cross at intersections", True), ("West Avenue", "No LSVs; cross at intersections", True), ("Route 52 causeway", "No LSVs", False), ("34th Street bridge (Roosevelt Blvd)", "No LSVs", False)],
     [("Can I drive an LSV on Asbury Avenue in {n}?", "Where Asbury Avenue is posted 25 mph or less, yes. Ocean City police list Bay Ave and West Ave as off limits, crossing only."),
      ("Can I drive a regular golf cart in {n}?", "No. New Jersey only lets titled, registered and insured LSVs on public roads, so plain golf carts stay off the streets.")])
prof("lbi", "Street-legal LSVs yes, plain golf carts no. On Long Beach Island, registered LSVs may use streets posted 25 mph or less. Long Beach Boulevard is mostly posted 30 to 40 mph, so cross it rather than drive it.",
     ("no", "Not on public roads", "n/a", "Not street-legal in NJ"), ("yes", "Roads posted 25 mph or less", "25 mph", "Cross Long Beach Blvd at intersections"),
     [NJGC, NJLSV, ("Surf City", "Surf City police register and enforce LSV rules on the island", "Surf City Police LSV page", "https://surfcitypdnj.org/lsv/")],
     [("Long Beach Boulevard (where posted over 25 mph)", "LSVs cross only", True), ("Route 72 causeway", "No LSVs", False)],
     [("Can I drive an LSV on Long Beach Boulevard in {n}?", "Only where it's posted 25 mph or less. Most of the boulevard is posted 30 to 40 mph, so LSVs cross it at intersections."),
      ("Can I drive a regular golf cart in {n}?", "No. New Jersey only lets titled, registered and insured LSVs on public roads.")])
prof("fmb", "Street-legal LSVs yes; plain golf carts only where the town designates roads, and none were found. In {n}, registered LSVs may use roads posted 35 mph or less, including Estero Boulevard.",
     ("limited", "Only designated, signed roads", "n/a", "No designated streets found"), ("yes", "Roads posted 35 mph or less", "35 mph", "Not on sidewalks or paths"),
     [FLGC, FLLSV, ("Sidewalks and paths", "No motor vehicles on sidewalks or shared paths", "Town of Fort Myers Beach Ord. 25-03", "https://www.fortmyersbeachfl.gov/DocumentCenter/View/24451/25-03-Beach-Bicycle-and-Vehicle-Safety")],
     [("Sidewalks and shared paths", "No motor vehicles", False)],
     [("Can I drive an LSV on Estero Boulevard in {n}?", "Yes, where it's posted 35 mph or less, which is most of it. Registered LSVs follow the Florida LSV law."),
      ("Can I drive a regular golf cart in {n}?", "Only on roads the town has designated and signed for golf carts. We didn't find any, so plan on an LSV.")])
prof("sanibel", "Street-legal LSVs yes; plain golf carts only on designated roads. Sanibel limits golf carts to designated city roads posted 30 mph or less. LSVs may use roads posted 35 mph or less in {n}, such as Periwinkle Way on Sanibel.",
     ("limited", "Designated roads posted 30 mph or less", "30 mph", "City of Sanibel ordinance"), ("yes", "Roads posted 35 mph or less", "35 mph", "Periwinkle Way is posted 35"),
     [("Golf carts", "Golf carts only on designated roads posted 30 mph or less", "City of Sanibel Ord. 19-011", "https://mcclibraryfunctions.azurewebsites.us/api/ordinanceDownload/10937/994063/pdf"), FLLSV],
     [("Shared-use paths", "No LSVs", False)],
     [("Can I drive an LSV on Periwinkle Way on Sanibel?", "Yes. Periwinkle Way is posted 35 mph, the Florida LSV limit."),
      ("Can I drive a regular golf cart in {n}?", "Only on designated roads. Sanibel designates city roads posted 30 mph or less; Captiva is unincorporated Lee County. Check the signs before you go.")])
prof("capemay", "Street-legal LSVs yes, plain golf carts no. In {n}, registered LSVs may use roads posted 25 mph or less and cross faster roads at intersections.",
     ("no", "Not on public roads", "n/a", "Not street-legal in NJ"), ("yes", "Roads posted 25 mph or less", "25 mph", "Local LSV ordinances apply"),
     [NJGC, NJLSV, ("Stone Harbor", "Borough code regulates LSVs", "Stone Harbor borough code", "https://ecode360.com/10814440"),
      ("Avalon", "Borough ordinance on LSV rentals and taxis", "Avalon Ord. 799-2020", "https://avalonboro.net/wp-content/uploads/2020/02/ORD-799-2020-TAXICABS-LOW-SPEED-VEHICLES-WITHOUT-EDITS.pdf")],
     [("Garden State Parkway", "No LSVs", False), ("Roads posted over 25 mph (e.g. Ocean Drive, Route 47)", "LSVs cross only", True)],
     [("Can I drive a regular golf cart in {n}?", "No. New Jersey only lets titled, registered and insured LSVs on public roads."),
      ("How fast can a road be for an LSV in {n}?", "25 mph or less, unless the town, county or NJDOT has opened it to LSVs up to 35 mph.")])
prof("topsail", "Street-legal LSVs yes; golf carts depend on the town. In {n}, LSVs may use roads posted 35 mph or less. In Topsail Beach, LSVs may only cross North and South Anderson Boulevard.",
     ("limited", "Town permit rules vary", "25 mph", "Check the town before you drive"), ("yes", "Roads posted 35 mph or less", "35 mph", "Topsail Beach: cross Anderson Blvd only"),
     [NCLSVR, ("Anderson Boulevard", "LSVs only cross North or South Anderson Blvd, except the 25 mph business district on S. Anderson", "Town of Topsail Beach", "https://topsailbeachnc.gov/Departments/Police/Golf-Cart-Low-Speed-Vehicles")],
     [("North and South Anderson Blvd (Topsail Beach)", "Cross only (except the 25 mph business district)", True), ("NC 210 where posted over 35 mph", "No LSVs", True)],
     [("Can I drive an LSV on Anderson Boulevard?", "In Topsail Beach, only to cross it, except the 25 mph business-district stretch of South Anderson."),
      ("Can I drive a regular golf cart in {n}?", "Golf carts are allowed only where the town's ordinance permits them. Check with the town police first.")])
prof("carolinabeach", "It depends on the town. Carolina Beach lets permitted golf carts and LSVs use roads posted 35 mph or less, and its plain golf cart permits end Dec 31, 2027. Kure Beach only allows carts that are tagged and street-legal as LSVs. In {n}, LSVs may use roads posted 35 mph or less.",
     ("limited", "Carolina Beach: roads posted 35 mph or less with a town permit; Kure Beach: LSVs only", "35 mph", "Carolina Beach permits end Dec 31 2027"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Carts only on roads posted 35 mph or less; may cross faster roads at intersections", "Town of Carolina Beach", "https://www.carolinabeach.gov/324/Golf-Cart-LSV-Rules-Regulations"), NCLSVR,
      ("Phase-out", "Plain golf carts lose street permits after 2027; LSVs continue", "WECT", "https://www.wect.com/2023/03/15/golf-carts-disappear-carolina-beach-streets-by-2028/"),
      ("Kure Beach", "Carts must be tagged, licensed and meet the federal LSV standard (49 CFR 571.500) to use town streets", "Town of Kure Beach golf cart rules", S.KURE)],
     [("Dow Road and other roads posted over 35 mph", "Cross only", True), ("Kure Beach streets (plain golf carts)", "Street-legal LSVs only", False)],
     [("Can I still drive a golf cart in Carolina Beach in 2028?", "Not a plain golf cart. Carolina Beach is phasing out golf cart street permits after Dec 31, 2027; street-legal LSVs can keep driving."),
      ("Can I drive a golf cart on Lake Park Boulevard?", "In Carolina Beach, where it's posted 35 mph or less, with a town permit. In Kure Beach (where it becomes Fort Fisher Boulevard), only street-legal LSVs.")])
prof("emeraldisle", "Yes, with town rules. Emerald Isle keeps golf carts off NC 58 (Emerald Drive) and Coast Guard Road except to cross. Atlantic Beach allows registered carts on streets posted 35 mph or less, but not Fort Macon Road or the causeway. LSVs may use roads posted 35 mph or less in {n}.",
     ("yes", "Town streets, not NC 58, Coast Guard Rd or Fort Macon Rd", "25 mph", "Licensed driver 18+; Atlantic Beach registration"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts on all town streets except NC 58 (Emerald Dr) and Coast Guard Rd; cross straight over only", "Town of Emerald Isle", S.EIDOC),
      ("Atlantic Beach", "Registered, inspected carts on streets posted 35 mph or less; not NC 58/Fort Macon Rd or the causeway", "Atlantic Beach Police golf carts", S.ABNC), NCLSVR],
     [("NC 58 (Emerald Drive)", "No golf carts; cross straight over", True), ("Coast Guard Road", "No golf carts; cross straight over", True), ("Fort Macon Road / Atlantic Beach Causeway", "No golf carts in Atlantic Beach", True), ("Bike path and sidewalks", "No golf carts", False)],
     [("Can I drive a golf cart on Emerald Drive?", "No. Golf carts may only cross NC 58 (Emerald Drive) straight over, never drive along it."),
      ("Can I use the bike path in a golf cart in Emerald Isle?", "No. The town's rules keep golf carts off the bike path and sidewalks.")])
prof("clearwater", "Street-legal LSVs yes; plain golf carts only on designated streets. Dunedin has designated golf cart streets on its official map. LSVs may use roads posted 35 mph or less in {n}.",
     ("limited", "Designated streets only", "n/a", "Dunedin's golf cart map"), ("yes", "Roads posted 35 mph or less", "35 mph", "Not on causeways posted higher"),
     [FLGC, FLLSV, ("Dunedin", "Golf carts on the city's designated streets", "City of Dunedin golf cart map", S.DUN)],
     [("Memorial Causeway and Gulf to Bay Blvd", "Posted over 35 mph: no LSVs", False)],
     [("Can I drive a golf cart in Dunedin?", "Yes, on the streets shown on the city's golf cart map."),
      ("Can I drive a golf cart on Clearwater Beach?", "Only on roads the city designates for carts. Street-legal LSVs may use roads posted 35 mph or less.")])
prof("stpete", "Street-legal LSVs yes; plain golf carts only on designated city streets. St. Pete Beach keeps registered carts off Gulf Boulevard and the Pinellas Bayway (state and county roads). LSVs may use roads posted 35 mph or less in {n}.",
     ("limited", "Designated city streets only", "n/a", "City registration"), ("yes", "Roads posted 35 mph or less", "35 mph", "Gulf Blvd is posted 35"),
     [("Golf carts", "Registered golf carts on designated city streets only, not state or county roads", "City of St. Pete Beach", S.SPB), FLLSV],
     [("Gulf Boulevard", "No golf carts (state road)", True), ("Pinellas Bayway", "No golf carts", False)],
     [("Can I drive a golf cart on Gulf Boulevard?", "No. St. Pete Beach keeps golf carts off state and county roads like Gulf Boulevard. Street-legal LSVs may use it where it's posted 35 mph."),
      ("Do I need to register a golf cart in St. Pete Beach?", "Yes. St. Pete Beach requires golf carts to be registered with the city.")])
prof("newport", "Yes, with limits. In {n}, golf carts may use streets posted 25 mph or less and LSVs streets posted 35 mph or less. Both stay off Pacific Coast Highway.",
     ("yes", "Streets posted 25 mph or less", "25 mph", "Business or residence district"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts on highways posted 25 mph or less in a business or residence district", "CVC 21716", S.CVC + "21716"), ("LSVs", "LSVs on roads posted 35 mph or less", "CVC 21260", S.CVC + "21260"),
      ("PCH", "Golf carts aren't allowed on Pacific Coast Highway", "Patch: Newport Beach police", S.PATCH)],
     [("Pacific Coast Highway", "No golf carts or LSVs", True)],
     [("Can I drive a golf cart on Balboa Island?", "Yes. Balboa Island streets are posted 25 mph or less, so golf carts may use them."),
      ("Can I drive a golf cart on PCH in Newport Beach?", "No. Pacific Coast Highway is posted well above 25 mph and police say carts aren't allowed on it.")])
prof("pensacola", "Street-legal LSVs yes; plain golf carts only on designated roads. LSVs may use roads posted 35 mph or less in {n}; on Pensacola Beach that includes Via de Luna and Fort Pickens Road. Golf carts can't cross the Bob Sikes Bridge or the Navarre Bridge.",
     ("limited", "Designated roads only", "n/a", "No bridges"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, FLLSV, ("Pensacola Beach roads", "Registered LSVs may use Pensacola Beach roads signed 35 mph or less", "Pensacola News Journal (Escambia County traffic)", S.PNJ14),
      ("Bob Sikes Bridge", "Golf carts aren't allowed on the Bob Sikes Bridge", "City of Gulf Breeze", S.GBZ),
      ("Navarre Beach", "Golf carts on Navarre Beach county roads, not the Navarre Bridge", "Santa Rosa County golf cart ordinance", S.NAVB)],
     [("Bob Sikes Bridge", "No golf carts", False), ("Navarre Bridge", "No golf carts", False)],
     [("Can I drive an LSV on Via de Luna?", "Yes. Via de Luna is posted 35 mph or less, so registered LSVs may use it."),
      ("Can I take a golf cart over the bridge to Pensacola?", "No. Golf carts aren't allowed on the Bob Sikes Bridge.")])
prof("brunswick", "Street-legal LSVs yes, plain golf carts no. Ocean Isle Beach and Holden Beach only allow carts that are registered, inspected and insured as LSVs. In {n}, LSVs may use roads posted 35 mph or less.",
     ("no", "Only if registered as an LSV", "n/a", "Gas carts can't pass NC inspection"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered, inspected, insured"),
     [("Golf carts", "Must be registered, tagged and insured LSVs to use public streets", "Town of Ocean Isle Beach", S.OIB),
      ("Holden Beach", "Golf carts aren't allowed on roads; registered, inspected and insured LSVs only", "Town of Holden Beach ordinance summary", S.HBNC), NCLSVR],
     [("Roads posted over 35 mph (e.g. NC 904, NC 130)", "Cross only", True)],
     [("Can I drive a regular golf cart in {n}?", "No. Ocean Isle Beach and Holden Beach only allow carts that are registered, tagged and insured as LSVs."),
      ("Can gas golf carts be street-legal in Ocean Isle Beach?", "No. The town says gas golf carts won't pass NC inspection, so they can't be registered.")])
prof("crystalbeach", "Yes. On the Bolivar Peninsula, golf carts may use roads posted 35 mph or less and cross Highway 87 at intersections, but not drive along it.",
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not on SH 87; cross only"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts on roads posted 35 mph or less; not on highways, which they may cross", "CrystalBeach.com", S.CB), ("State law", "Golf cart rules for roads posted 35 mph or less", "Tex. Transp. Code 551.404", S.TX551)],
     [("State Highway 87", "No golf carts; cross at intersections", True)],
     [("Can I drive a golf cart on Highway 87?", "No. Golf carts may only cross SH 87 at intersections."),
      ("Do I need a license to drive a golf cart in {n}?", "Yes. You need a valid driver's license, and night driving needs lights and reflectors.")])
prof("padre", "Yes. Corpus Christi lets golf carts and NEVs use island streets posted 35 mph or less on {n}. They stay off SH 361 and South Padre Island Drive where it's posted higher.",
     ("yes", "Island streets posted 35 mph or less", "35 mph", "City ordinance area"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts and NEVs on island streets posted 35 mph or less", "City of Corpus Christi ordinance (File 19-1512)", S.CC)],
     [("SH 361", "No golf carts", True), ("JFK Causeway", "No golf carts", False)],
     [("Can I drive a golf cart on Whitecap Boulevard?", "Yes, where it's posted 35 mph or less."),
      ("Can I drive a golf cart over the JFK Causeway?", "No. It's posted 55 mph.")])
prof("bocagrande", "Partly. In {n}, electric golf carts may use the island bike path at up to 15 mph. Plain golf carts aren't designated for the island's roads; street-legal LSVs may use roads posted 35 mph or less.",
     ("limited", "Island bike path (electric only)", "15 mph on the path", "50 inches wide max"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Bike path", "Electric golf carts may use the Boca Grande bike path, 15 mph max, 50 inches wide max", "GICIA bike path rules", S.GICIA), FLGC, FLLSV,
      ("Lee County", "County ordinance on the Boca Grande path", "Lee County Ord. 25-16", "https://www.leegov.com/bocc/Ordinances/25-16.pdf")],
     [("Gas golf carts on the bike path", "Not allowed", False)],
     [("Can I drive a gas golf cart on the Boca Grande bike path?", "No. Only electric carts may use the path."),
      ("How fast can a golf cart go on the bike path?", "15 mph at most.")])
prof("pawleys", "Golf carts yes; LSVs depend on where you are. The Town of Pawleys Island requires SC DMV and town permits for golf carts and bans LSVs on all town roads. Around Litchfield and Murrells Inlet, SC golf cart law applies and LSVs may use roads posted 35 mph or less.",
     ("limited", "Secondary roads posted 35 mph or less; town permit on the island", "35 mph", "Daylight; within 4 mi (2 mi for the town permit)"), ("limited", "Not on Pawleys Island town roads", "35 mph", "Elsewhere roads posted 35 mph or less"),
     [SCGC, ("Pawleys Island", "Golf carts need SC DMV and town stickers; LSVs prohibited on all town roads", "Town of Pawleys Island", S.PAW)],
     [("Pawleys Island town roads", "No LSVs", False), ("US 17 (Ocean Highway)", "No golf carts or LSVs", True)],
     [("Can I drive an LSV on Pawleys Island?", "No. The town prohibits low-speed vehicles on all primary and secondary roads within town limits."),
      ("Can I drive a golf cart on Pawleys Island?", "Yes, with SC DMV and Town of Pawleys Island stickers, in daylight.")])
prof("dauphin", "Yes, if it's plated. On {n}, golf carts need a license plate from their home state to use public roads.",
     ("yes", "Public roads, plated carts", "25 mph", "Home-state license plate"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts need a state-issued license plate for public roadways", "Town of Dauphin Island FAQ", S.DI)],
     [("Dauphin Island Bridge (AL 193)", "Posted 55 mph: no carts", False)],
     [("Do I need a plate for a golf cart on {n}?", "Yes. The town says golf carts need a license plate issued by their home state to drive on public roads."),
      ("Can I drive a golf cart on Bienville Boulevard?", "Where it's posted 25 mph, yes with a plated cart; check the posted limit on faster stretches.")])
prof("stgeorge", "Yes. Franklin County lets golf carts use county roads on {n}, except Gulf Beach Drive. Franklin Boulevard may only be crossed.",
     ("yes", "County roads, not Gulf Beach Dr", "35 mph", "Cross Franklin Blvd only"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts on St. George Island county roads except Gulf Beach Dr; Franklin Blvd crossing only", "Franklin County Code ch. 12", S.FC), FLLSV],
     [("Gulf Beach Drive", "No golf carts", False), ("Franklin Boulevard", "No golf carts; cross only", True)],
     [("Can I drive a golf cart on Gulf Beach Drive?", "No. Franklin County keeps golf carts off Gulf Beach Drive."),
      ("Can I drive a golf cart across Franklin Boulevard?", "Yes, to cross it, but not along it.")])
prof("capesanblas", "Street-legal LSVs yes; plain golf carts only on designated roads, and never on US 98 or the state roads. Mexico Beach's ordinance sets its own cart rules.",
     ("limited", "Designated roads only", "n/a", "Not US 98 or state roads"), ("yes", "Roads posted 35 mph or less", "35 mph", "US 98 is posted higher"),
     [FLGC, FLLSV, ("Mexico Beach", "City golf cart rules; no carts on US 98", "City of Mexico Beach Ord. 569", S.MB)],
     [("US 98", "No golf carts", True), ("SR 30A, SR 30E, SR 71", "No golf carts", True)],
     [("Can I drive a golf cart on US 98 in Mexico Beach?", "No. Carts may only cross US 98."),
      ("Can I drive an LSV on Cape San Blas Road?", "Only where it's posted 35 mph or less; much of it is 45 to 55 mph.")])
prof("delbeaches", "Street-legal LSVs yes, plain golf carts no. Delaware doesn't allow golf carts on its highways. LSVs may use roads posted 35 mph or less, but not Coastal Highway outside towns, and not in Fenwick Island at all.",
     ("no", "Not on public roads", "n/a", "Delaware DMV"), ("yes", "Roads posted 35 mph or less", "35 mph", "Not Coastal Hwy outside towns; not in Fenwick Island"),
     [("Golf carts", "Golf carts are not allowed to operate on Delaware highways", "Delaware DMV", S.DEDMV), ("LSVs", "LSVs on roads posted 35 mph or less; not on dual highways outside towns except to cross", "21 Del. C. 2113A", S.DE2113),
      ("Fenwick Island", "Low-speed vehicles prohibited on town streets", "Fenwick Island Code ch. 153", S.FEN)],
     [("Coastal Highway (DE 1) outside towns", "No LSVs; cross only", True), ("Fenwick Island streets", "No LSVs", False)],
     [("Can I drive a golf cart in {n}?", "No. Delaware DMV says golf carts aren't allowed on Delaware highways. Only registered LSVs may use roads posted 35 mph or less."),
      ("Can I drive an LSV in Fenwick Island?", "No. Fenwick Island's town code prohibits low-speed vehicles.")])
prof("edisto", "Yes. In {n}, permitted golf carts may use every town road except Palmetto Boulevard (SC 174), which they may only cross straight over. LSVs may use roads posted 35 mph or less.",
     ("yes", "All town roads except Palmetto Blvd", "35 mph", "SC DMV permit; daylight"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Every road in town limits except Palmetto Blvd (SC 174); cross straight over", "Town of Edisto Beach", S.EDI), SCGC],
     [("Palmetto Boulevard (SC 174)", "No golf carts; cross straight over", True)],
     [("Can I drive a golf cart on Palmetto Boulevard?", "No. It's a primary highway (SC 174); golf carts may only cross it straight over."),
      ("Can I drive an LSV on Palmetto Boulevard?", "Where it's posted 35 mph or less, yes.")])
prof("nsb", "Street-legal LSVs yes, plain golf carts no on city streets. In {n}, LSVs may use roads posted 35 mph or less but not A1A/Atlantic Avenue or 3rd Avenue, which they may cross at intersections.",
     ("no", "No designated streets", "n/a", "F.S. 316.212"), ("yes", "Roads posted 35 mph or less", "35 mph", "Not A1A/Atlantic Ave or 3rd Ave"),
     [FLGC, FLLSV, ("Banned roads", "No LSVs on A1A/Atlantic Ave or 3rd Ave; cross at intersections", "Hometown News (NSB police)", S.HTN)],
     [("A1A / Atlantic Avenue", "No LSVs; cross at intersections", True), ("3rd Avenue", "No LSVs; cross at intersections", True)],
     [("Can I drive an LSV on 3rd Avenue in {n}?", "No. Police say LSVs may only cross 3rd Avenue."),
      ("Can I drive a regular golf cart in {n}?", "Not on city streets; the city hasn't designated any for golf carts.")])
prof("kelleys", "Yes, if it's titled and plated. On Kelleys Island and in Marblehead, golf carts must pass a police inspection for a title and plate before using public roads, and Marblehead limits them to streets posted 35 mph or less.",
     ("yes", "Public roads, plated carts", "35 mph", "Police inspection for title and plate"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Golf carts are motor vehicles in Ohio; police inspect them for title and plates", "Kelleys Island Police", S.KI),
      ("Marblehead", "Inspected, titled and registered carts on streets posted 35 mph or less", "Village of Marblehead Code", S.MHOH)],
     [],
     [("Can my child drive a golf cart in {n}?", "No. Golf carts are motor vehicles in Ohio and need a licensed driver."),
      ("Can I drink on a golf cart on Kelleys Island?", "No. The island isn't a DORA district, so open containers aren't allowed on golf carts.")])
prof("chincoteague", "Yes, with limits. In {n}, registered golf carts may use streets the Town Council designates, posted 25 mph or less, but never Main Street or Second Street.",
     ("limited", "Designated streets posted 25 mph or less", "25 mph", "Town registration; not Main St or Second St"), ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Only on designated streets posted 25 mph or less; not Main St or Second St", "Town of Chincoteague Sec. 8-2-13", S.CHT), ("LSVs", "LSVs on highways posted 35 mph or less", "Va. Code 46.2-908.3", S.VA9083)],
     [("Main Street", "No golf carts; cross at Sycamore, Fifth or Third St", True), ("Second Street", "No golf carts; cross at Marshall or Endly St", True)],
     [("Can I drive a golf cart on Main Street in {n}?", "No. Golf carts may only cross Main Street at Sycamore, Fifth and Third Streets."),
      ("Do I need to register a golf cart in {n}?", "Yes. The town requires registration, proof of insurance and a $25 yearly decal.")])
