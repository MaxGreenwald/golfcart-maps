"""Town-page profiles for Greenwich and the next 10 regions (Oct 28 2026). Imported by gen_town_pages.py.
Every rule line carries the official (or best available) source; the same sources are in research/regions/<id>.json."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "research"))
import regions11_setup as S
FLS = S.FLS
P, T, RID = {}, [], {}
def prof(rid, a, gc, lsv, rules, banned, faq, q="Can you drive a golf cart in {n}?"):
    r = next(x for x in S.R if x["id"] == rid)
    P[rid] = dict(q=q, a=a, gc=dict(zip(("allowed", "roads", "speed_line", "notes"), gc)), lsv=dict(zip(("allowed", "roads", "speed_line", "notes"), lsv)),
                  rules=rules, banned=banned, faq=faq, sources=sorted({x["url"] for x in r["enf"]}), day="2026-10-28")
    RID[r["slug"]] = rid
    for slug, name, lat, lng in r["towns"]: T.append((r["slug"], slug, name, r["state"], lat, lng))

CTLSV = ("LSV roads", "Registered LSVs on roads posted 25 mph or less, unless the traffic authority has prohibited that road", "Conn. Gen. Stat. Sec. 14-289m", S.CTLSV)
CTGC = ("Golf carts", "Plain golf carts are not street-legal unless the town traffic authority permits them", "Conn. Gen. Stat. Sec. 14-300g", S.CTGC)
GALS = ("LSV roads", "Registered LSVs on roads posted 35 mph or less; they may cross faster roads at intersections", "O.C.G.A. 40-6-362", S.OCGA_LSV)
GAPT = ("Golf carts", "Personal transportation vehicles only where a local ordinance allows them", "O.C.G.A. 40-6-331", S.OCGA)
FLGC = ("Golf carts", "Plain golf carts only on roads a city or county has designated and signed for carts", "F.S. 316.212", S.FL212)
FLLSV = ("LSV roads", "Registered, insured LSVs on roads posted 35 mph or less; cross faster roads only at intersections", "F.S. 316.2122", S.FL2122)

prof("greenwich", "Street-legal LSVs yes, plain golf carts no. In {n}, a registered LSV may use roads posted 25 mph or less unless the traffic authority has closed that road. Greenwich has not permitted plain golf carts.",
     ("no", "Not on public roads", "n/a", "Town traffic authority has not permitted them"),
     ("yes", "Roads posted 25 mph or less", "25 mph", "I-95 and the Merritt Parkway are closed"),
     [CTGC, CTLSV, ("Limited-access roads", "No LSVs on I-95 or the Merritt Parkway", "Conn. Gen. Stat. Sec. 14-289m", S.CTLSV)],
     [("I-95", "No LSVs", False), ("Merritt Parkway (CT 15)", "No LSVs", False)],
     [("Can I drive a regular golf cart in {n}?", "No. Connecticut only allows golf carts on public streets when that town's traffic authority permits them, and Greenwich has not."),
      ("Can I drive an LSV on a 25 mph street in {n}?", "Yes, if it is registered and the traffic authority has not prohibited that street. Roads posted over 25 mph are closed.")])

prof("tyrone", "Street-legal LSVs yes. Golf carts need a Tyrone permit and may use designated streets posted 35 mph or less, plus paved paths. That street list is not drawn on this map yet, so plan on an LSV or a tagged cart path. Highway 74 is not a cart route.",
     ("limited", "Designated streets posted 35 mph or less, and paved paths", "35 mph", "Street list not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Designated streets posted 35 mph or less, and paved multi-use paths. Highway 74 is not a cart route.", "Town of Tyrone", S.TYR), GALS],
     [("Highway 74", "No golf carts", True)],
     [("Can I drive a golf cart on Highway 74 in {n}?", "No. Tyrone does not treat Highway 74 as a cart route."),
      ("Why are most streets red for a golf cart in {n}?", "Tyrone allows carts on designated streets. That list is not digitized, so the map keeps plain golf carts off streets that are not tagged cart paths.")])

prof("fayetteville", "Street-legal LSVs yes. Golf carts need a city permit and may use authorized streets and recreation paths only, not major or collector streets. The authorized list is not drawn here, so plain golf carts show on tagged cart paths only.",
     ("limited", "Authorized streets and recreation paths", "n/a", "Not major or collector streets"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Motorized carts only on authorized streets and recreation paths, not on major or collector streets except approved crossings", "Fayetteville Code Sec. 82-262", S.FAYCODE), GALS],
     [("Glynn Street and state routes 54, 85, and 92", "No golf carts except approved crossings", True)],
     [("Can I drive a golf cart on Glynn Street in {n}?", "No. Fayetteville keeps carts off major and collector streets except at approved crossings."),
      ("Can I drive an LSV in {n}?", "Yes, on roads posted 35 mph or less. A plain golf cart still needs an authorized street.")])

prof("senoia", "Yes, with a city registration. In {n}, motorized carts may use streets posted 35 mph or less, but not State Route 16 or State Route 85 except at a crossing. LSVs may use roads posted 35 mph or less.",
     ("yes", "Streets posted 35 mph or less", "35 mph", "Not SR 16 or SR 85"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not the parts of SR 16 and SR 85 posted over 35"),
     [("Golf carts", "Motorized carts on streets posted 35 mph or less; not on State Highway 16 or 85 except authorized crossings", "Senoia Code Sec. 66-103", S.SEN), GALS],
     [("State Route 16", "No golf carts; cross only", True), ("State Route 85", "No golf carts; cross only", True)],
     [("Can I drive a golf cart on State Route 16 in {n}?", "No. You may cross it where the city has an authorized crossing, not drive along it."),
      ("Do I need to register a golf cart in {n}?", "Yes. Senoia requires a city registration decal before a cart uses public streets or paths.")])

prof("conyers", "Street-legal LSVs yes. Golf carts only inside the city's motorized cart district, on designated roads. That district map is not drawn here, so plain golf carts show on tagged cart paths only.",
     ("limited", "Designated roads inside the cart district", "n/a", "District map not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not on I-20"),
     [("Golf carts", "Motorized carts only on designated public roads inside the cart district", "City of Conyers golf cart district", S.CON), GALS],
     [("Interstate 20", "No carts or LSVs", False)],
     [("Can I drive a golf cart anywhere in {n}?", "No. Only on roads inside the motorized cart district. That map is not digitized here, so use an LSV or a tagged cart path until it is."),
      ("Can I drive an LSV on a 35 mph street in {n}?", "Yes, where it is posted 35 mph or less. I-20 is closed.")])

prof("augusta", "PTVs only on streets Augusta designates: a downtown area and a few named streets on the west side. Downtown streets that are not in the named list stay red on this map. LSVs may use roads posted 35 mph or less in {n}.",
     ("limited", "Named PTV streets only", "35 mph", "Downtown side streets not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Not on the interstates"),
     [("PTV streets", "J. Dewey Gray Circle, Wainbrook, Devore Place, part of Interstate Parkway, Heath Drive, and Pine Needle Road, plus the downtown area except listed bans", "Augusta PTV requirements", S.AUG), GALS],
     [("15th Street, Walton Way, Gordon Highway, Laney Walker Boulevard", "No PTVs in the downtown area", False),
      ("I-20 and I-520", "No carts or LSVs", False)],
     [("Can I drive a PTV on Walton Way in downtown {n}?", "No. Augusta bans PTVs on Walton Way, 15th Street, Gordon Highway, and several other downtown streets."),
      ("Can I drive a PTV on every downtown street?", "The ordinance allows streets inside the downtown boundary except the named bans. Those extra streets are not digitized, so this map keeps them red.")])

prof("euharlee", "Yes, on city streets in the subdivisions. Golf carts may use public streets posted 25 mph or less. LSVs may use streets posted 35 mph or less. Neither may drive along a state or county highway except to cross.",
     ("yes", "Public streets posted 25 mph or less", "25 mph", "Not state or county highways"),
     ("yes", "Streets posted 35 mph or less", "35 mph", "Not state or county highways"),
     [("Golf carts", "Public streets posted 25 mph or less; not on state or county highways except to cross", "Euharlee Ord. 2025-03", S.EUH),
      ("LSVs", "Low-speed vehicles on streets posted 35 mph or less; not on state or county highways except to cross", "Euharlee Ord. 2025-03", S.EUH)],
     [("Euharlee Road (GA 113)", "Cross only", True), ("State and county highways", "Cross only", True)],
     [("Can I drive a golf cart on Euharlee Road?", "No. It is the state highway through town. Cross it at an intersection."),
      ("Can I drive a golf cart at night in {n}?", "Only if the cart has working headlights and taillights. Otherwise, sunrise to sunset.")])

prof("stmarys", "Yes. In {n}, a PTV may use streets posted 35 mph or less, except Winding Road. State highways are for crossing, not driving along. LSVs follow the 35 mph state rule.",
     ("yes", "Streets posted 35 mph or less", "35 mph", "Not Winding Road or state highways"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("PTVs", "Streets posted 35 mph or less, except Winding Road; state highways only at a marked crossing", "St. Marys PTV ordinance", S.STM), GALS],
     [("Winding Road", "No PTVs", False), ("State highways", "Cross only", True)],
     [("Can I drive a golf cart on Winding Road in {n}?", "No. The city ordinance bans PTVs on every part of Winding Road."),
      ("Can I drive a golf cart on a 35 mph city street in {n}?", "Yes, if it is not Winding Road or a state highway.")])

prof("lowerkeys", "Street-legal LSVs yes. Plain golf carts only on roads a city or the county has designated, and no designation was found for {n}, so plain golf carts show red except tagged cart paths. LSVs may use roads posted 35 mph or less. US 1 is usually posted higher.",
     ("limited", "Designated roads only", "n/a", "No Marathon list found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "US 1 is often posted higher"),
     [FLGC, FLLSV, ("Marathon", "The city discussed LSVs in 2011 and did not adopt a golf-cart street list", "Keys Weekly", S.KEYS)],
     [("US 1 where posted over 35 mph", "No LSVs", True)],
     [("Can I drive a regular golf cart in {n}?", "Only on a road the city or county has designated and signed. We did not find that list, so plan on a registered LSV."),
      ("Can I drive an LSV on US 1 in {n}?", "Only where it is posted 35 mph or less. Most of US 1 in the Keys is posted higher, so cross it rather than drive along it.")])

prof("cocoabeach", "Street-legal LSVs yes. Golf carts only on streets Cocoa Beach marks on its Golf Cart Network Map, posted 30 mph or less. That map is not drawn here, so plain golf carts show red except tagged cart paths. SR A1A is not a cart street.",
     ("limited", "Streets on the Golf Cart Network Map", "30 mph", "Map not digitized"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [("Golf carts", "Only on city streets the commission designates, posted 30 mph or less", "Cocoa Beach Code Sec. 15-47", S.CBO),
      ("Network map", "Resolution 2023-07 adopts the current golf cart network map", "Cocoa Beach Resolution 2023-07", S.CBB), FLLSV],
     [("SR A1A (Atlantic Avenue)", "No golf carts", True)],
     [("Can I drive a golf cart on A1A in {n}?", "No. A1A is a state road. The city designates city streets, and this map does not treat A1A as one of them."),
      ("Can I drive an LSV on a 35 mph street in {n}?", "Yes. The 30 mph cap is for plain golf carts on designated streets. A registered LSV follows the Florida 35 mph rule.")])

prof("venice", "Street-legal LSVs yes. Plain golf carts only on roads the city designates, and no Venice designation was found, so plain golf carts show red on public roads. LSVs may use roads posted 35 mph or less in {n}.",
     ("limited", "Designated, signed roads only", "n/a", "No city designation found"),
     ("yes", "Roads posted 35 mph or less", "35 mph", "Registered and insured"),
     [FLGC, FLLSV, ("City code", "No golf-cart street designation was found in the city code", "City of Venice code", S.VEN)],
     [("Roads posted over 35 mph", "No LSVs", True)],
     [("Can I drive a regular golf cart in {n}?", "Only on a street the city has designated and signed. We did not find any, so plan on a registered LSV."),
      ("Can I drive an LSV on the island streets in {n}?", "Yes, where they are posted 35 mph or less.")])
