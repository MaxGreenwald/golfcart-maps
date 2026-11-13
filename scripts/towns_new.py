"""Town-page profiles for towns added after the map reached 100.
Each line cites a statute or ordinance. Plain golf carts stay off streets
where no local permit was found."""
P, T, RID = {}, [], {}
DAY = "2026-11-13"

def one(rid, slug, name, state, lat, lng, a, gc, lsv, rules, banned, faq, town_slug=None):
    if rid not in P:
        P[rid] = dict(q="Can you drive a golf cart in {n}?", a=a,
                      gc=dict(zip(("allowed", "roads", "speed_line", "notes"), gc)),
                      lsv=dict(zip(("allowed", "roads", "speed_line", "notes"), lsv)),
                      rules=rules, banned=banned, faq=faq, sources=sorted({x[3] for x in rules}), day=DAY)
    RID[slug] = rid
    T.append((slug, town_slug or slug, name, state, lat, lng))

M660 = "https://www.legislature.mi.gov/Laws/MCL?objectName=MCL-257-660"
M657 = "https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-257-657a"
MI_RULES = [
    ("LSV roads", "A registered low-speed vehicle may use a street posted 35 mph or less, and may cross a faster street.", "MCL 257.660(8)", M660),
    ("Golf carts", "A city may allow golf carts only by resolution. No Traverse City or Holland resolution was found.", "MCL 257.657a", M657),
]
MI_FAQ = [
    ("Can I drive a regular golf cart in {n}?", "No. Michigan allows that only after the city adopts a resolution, and none was found."),
    ("What streets can an LSV use in {n}?", "Streets posted 35 mph or less. A faster street can be crossed, not driven along."),
]

one("traversecity", "traversecity", "Traverse City", "MI", 44.7631, -85.6206,
    "Street-legal LSVs yes, plain golf carts no. In {n}, a registered low-speed vehicle may use streets posted 35 mph or less and may cross a faster street. No city resolution allowing plain golf carts was found.",
    ("no", "Not on public roads", "n/a", "No city resolution found"),
    ("yes", "Streets posted 35 mph or less", "35 mph", "Registered and insured; a state highway can still be closed"),
    MI_RULES, [("State trunk lines posted over 35 mph", "Cross only", True)], MI_FAQ)

one("holland", "holland", "Holland", "MI", 42.7875, -86.1089,
    "Street-legal LSVs yes, plain golf carts no. In {n}, a registered low-speed vehicle may use streets posted 35 mph or less and may cross a faster street. No city resolution allowing plain golf carts was found.",
    ("no", "Not on public roads", "n/a", "No city resolution found"),
    ("yes", "Streets posted 35 mph or less", "35 mph", "Not on I-196"),
    MI_RULES + [("Freeway", "I-196 is above the 35 mph cap", "MCL 257.660(8)", M660)],
    [("I-196", "Freeway; no low-speed vehicles", False)], MI_FAQ)

CGS289 = "https://www.cga.ct.gov/current/pub/chap_248.htm#sec_14-289m"
CGS300 = "https://www.cga.ct.gov/current/pub/chap_249.htm#sec_14-300g"
one("mystic", "mystic", "Mystic", "CT", 41.354, -71.966,
    "Street-legal LSVs yes, plain golf carts no. In {n}, an LSV may use a road whose speed limit is 25 mph or less, unless the town prohibits that road. No Stonington or Groton permit for plain golf carts was found.",
    ("no", "Not on public roads", "n/a", "A town permit is required and none was found"),
    ("yes", "Roads with a speed limit of 25 mph or less", "25 mph", "Registered. The town or the state can still close a road."),
    [("LSV roads", "An LSV may use a highway with an established speed limit of 25 mph or less, unless the traffic authority or the state prohibits that highway.", "Conn. Gen. Stat. Sec. 14-289m", CGS289),
     ("Golf carts", "A traffic authority may permit golf carts in daylight on roads posted 25 mph or less. No Stonington or Groton permit was found.", "Conn. Gen. Stat. Sec. 14-300g", CGS300)],
    [("I-95", "Limited-access highway; no LSVs", False)],
    [("Can I drive a regular golf cart in {n}?", "No. Connecticut requires the town traffic authority to permit it, and no Stonington or Groton permit was found."),
     ("What is the LSV speed cap in {n}?", "25 mph. A road posted faster than that is closed to LSVs.")])

ME = "https://legislature.maine.gov/legis/statutes/29-a/title29-Asec2089.html"
one("boothbay", "boothbay", "Boothbay Harbor", "ME", 43.853, -69.629,
    "Street-legal LSVs yes, plain golf carts no. In {n}, a registered LSV may use a road posted 35 mph or less and may cross a faster road at an intersection. Plain golf carts are not road-legal on the mainland.",
    ("no", "Not on public roads", "n/a", "Mainland golf carts are not road-legal"),
    ("yes", "Roads posted 35 mph or less", "35 mph", "Registered. The town can still close a road for safety."),
    [("LSV roads", "A low-speed vehicle may be operated only on a road posted 35 mph or less, and may cross a faster road at an intersection.", "29-A M.R.S. section 2089", ME),
     ("Golf carts", "A golf cart registration for public roads is limited to islands that have no state-maintained roads.", "29-A M.R.S. section 501(2-A)", "https://legislature.maine.gov/statutes/29-a/title29-Asec501.html")],
    [],
    [("Can I drive a regular golf cart in {n}?", "No. Maine limits that registration to islands without state roads."),
     ("Where can I drive an LSV in {n}?", "On roads posted 35 mph or less. Cross a faster road only at an intersection.")])

FL = "https://www.flsenate.gov/Laws/Statutes/2025/316.2122"
FLC = "https://www.flsenate.gov/Laws/Statutes/2025/316.212"
AB = "https://coab.civicweb.net/document/205079/Ordinanace%20No.%2075-25-29.pdf?handle=93BD604B23A8469CA793846F12E20CB8"
JX_RULES = [
    ("LSV roads", "A registered, insured LSV may use a road posted 35 mph or less and may cross a faster road at an intersection.", "F.S. 316.2122", FL),
    ("Atlantic Beach", "A low-speed vehicle must be registered and may be operated only on the roadways in the city.", "Atlantic Beach Ordinance 75-25-29, Sec. 21-107(i)", AB),
    ("Golf carts", "A golf cart may use a public road only where the city has designated and signed it. That street list is not drawn on this map, so plain carts stay off public roads here.", "F.S. 316.212", FLC),
]
JX_A = "Street-legal LSVs yes. Plain golf carts only on a street the city has designated, and that list is not drawn here. In {n}, a registered LSV may use roads posted 35 mph or less."
JX_GC = ("no", "Not drawn on public roads", "n/a", "A designated street list is required and is not on this map")
JX_LSV = ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured")
JX_FAQ = [
    ("Can I drive a regular golf cart in {n}?", "Only on a street the city has designated and signed. That list is not on this map, so plain carts are shown off public roads."),
    ("Where can I drive an LSV in {n}?", "On roads posted 35 mph or less. Atlantic Beach also says an LSV stays on the roadway and must be registered."),
]
for slug, name, lat, lng in (
    ("atlantic-beach", "Atlantic Beach", 30.334, -81.398),
    ("neptune-beach", "Neptune Beach", 30.317, -81.396),
    ("jacksonville-beach", "Jacksonville Beach", 30.274, -81.388),
):
    one("jaxbeaches", "jaxbeaches", name, "FL", lat, lng, JX_A, JX_GC, JX_LSV, JX_RULES, [], JX_FAQ, town_slug=slug)

NJ = "https://law.justia.com/codes/new-jersey/title-39/section-39-4-31-1/"
NJM = "https://www.nj.gov/mvc/vehicletopics/lowspeed.htm"
one("atlanticcity", "atlanticcity", "Atlantic City", "NJ", 39.364, -74.423,
    "Street-legal LSVs yes, plain golf carts no. In {n}, a registered electric LSV may use roads posted 25 mph or less. A town can open a road up to 35 mph by ordinance. No such ordinance was found.",
    ("no", "Not on public roads", "n/a", "New Jersey does not register a plain golf cart for the street"),
    ("yes", "Roads posted 25 mph or less", "25 mph", "Electric, titled, and insured. Not on the expressway."),
    [("LSV roads", "An LSV may use a public road posted 25 mph or less. A municipality may by ordinance open a road posted up to 35 mph, or ban a hazardous street.", "N.J.S.A. 39:4-31.1", NJ),
     ("Golf carts", "An LSV must be electric and meet the federal low-speed vehicle standard. A gas golf cart does not qualify.", "NJ MVC low-speed vehicles", NJM)],
    [("Atlantic City Expressway", "Above the 25 mph cap", False)],
    [("Can I drive a regular golf cart in {n}?", "No. New Jersey allows a registered electric low-speed vehicle, not a plain golf cart."),
     ("Can an LSV use Atlantic Avenue?", "Only where it is posted 25 mph or less. No city ordinance opening 30 or 35 mph roads was found.")])

AZ = "https://www.azleg.gov/ars/28/00966.htm"
SCOT = "https://www.scottsdaleaz.gov/codes-and-ordinances/alternative-transportation-laws"
one("scottsdale", "scottsdale", "Scottsdale", "AZ", 33.494, -111.926,
    "Neighborhood electric vehicles yes, plain golf carts no. In {n}, a registered neighborhood electric vehicle may use a road posted 35 mph or less and may cross a faster road. The city describes a golf cart as crossing a road for golf play, not as a street network.",
    ("no", "Not on public roads, except a crossing for golf play", "n/a", "The city page does not open city streets to plain golf carts"),
    ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured. Not on Loop 101."),
    [("Neighborhood electric vehicles", "A neighborhood electric vehicle shall not be driven on a highway posted over 35 mph, except to cross at an intersection.", "A.R.S. 28-966", AZ),
     ("Golf carts", "On a golf course, no street registration is required. The city says a golf cart may cross the roadway for golf play.", "City of Scottsdale alternative transportation page", SCOT)],
    [("Loop 101 (Pima Freeway)", "Posted well above 35 mph", True)],
    [("Can I drive a regular golf cart on city streets in {n}?", "The city page does not allow that. It says a golf cart may cross a roadway for golf play."),
     ("Can a neighborhood electric vehicle use Scottsdale Road?", "Only where it is posted 35 mph or less. Much of it is posted higher. Loop 101 is closed.")])

WI = "https://library.municode.com/wi/madison/codes/code_of_ordinances?nodeId=COORMAWIVOIICH11--19_CH12VECO_MO"
WIG = "https://docs.legis.wisconsin.gov/statutes/statutes/349/ii/18"
one("madison", "madison", "Madison", "WI", 43.0747, -89.3841,
    "Street-legal low-speed vehicles yes, plain golf carts no. In {n}, city code allows a low-speed vehicle on a roadway posted 35 mph or less. No ordinance allowing plain golf carts on those streets was found.",
    ("no", "Not on public roads", "n/a", "No golf cart ordinance was found"),
    ("yes", "Roadways posted 35 mph or less", "35 mph", "A connecting highway needs state consent. Objections are signed."),
    [("LSV roads", "A low-speed vehicle may be operated on a roadway with a speed limit of 35 mph or less. A connecting highway or a state-trunk crossing needs Wisconsin DOT consent, and an objection is signed.", "Madison Code Sec. 12.792", WI),
     ("Golf carts", "A municipality may allow golf carts on highways posted 25 mph or less. No Madison ordinance doing that was found.", "Wis. Stat. 349.18(1m)", WIG)],
    [],
    [("Can I drive a regular golf cart in {n}?", "No. The city ordinance is for low-speed vehicles, and no golf cart ordinance was found."),
     ("Where can I drive an LSV in {n}?", "On a roadway posted 35 mph or less, unless a sign says low-speed vehicles are prohibited.")])

RI = "https://webserver.rilegislature.gov/Statutes/TITLE31/31-19.6/31-19.6-1.htm"
one("newportri", "newportri", "Newport", "RI", 41.490, -71.313,
    "Street-legal low-speed vehicles yes, plain golf carts no. In {n}, a registered low-speed vehicle may use a public road posted 35 mph or less. Rhode Island does not register a golf cart as that vehicle.",
    ("no", "Not on public roads", "n/a", "A golf cart is not registered as a low-speed vehicle"),
    ("yes", "Public roads posted 35 mph or less", "35 mph", "Registered, insured, and inspected. A city ban must be posted."),
    [("LSV roads", "A registered low-speed vehicle may use a public highway posted 35 mph or less, and may cross a highway posted 35 to 45 mph at a signal or stop sign.", "R.I. Gen. Laws 31-19.6-1", RI),
     ("Golf carts", "A golf cart is not manufactured to the low-speed vehicle standard and may not be registered for public roads.", "R.I. Gen. Laws 31-19.6-1", RI)],
    [],
    [("Can I drive a regular golf cart in {n}?", "No. Rhode Island does not register a golf cart as a low-speed vehicle."),
     ("Is this Newport Beach, California?", "No. This map is Newport, Rhode Island. Newport Beach, California is a separate map.")])
