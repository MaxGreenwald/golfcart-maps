#!/usr/bin/env python3
"""Generate content/towns/<region>/<town>.json from sourced region profiles below (seo-town-pages, 2026-10-21).
Every rule line carries a source_url taken from research/regions/<id>.json, public/data/rules.json or the official page
it names. Anything we could not source is left off and listed in research/town_pages_flags.md."""
import json, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DAY = "2026-10-21"
FLS = "https://www.flsenate.gov/Laws/Statutes/2026/"
CA = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=VEH&sectionNum="
WCSO = "https://waltonso.org/lsv/"
WMAP = "https://waltonso.org/wp-content/uploads/2022/10/lsv_map_102022.png"
SCDPS = "https://scdps.sc.gov/DrivinginSC/golf-cart-law"
P = {}
P["30a"] = dict(
  q="Can I drive a golf cart in {n}?",
  a="In {n}, street-legal LSVs yes; regular golf carts no. The Walton County Sheriff says golf carts are not permitted on any public road. Registered LSVs may use roads posted 35 mph or less, but not US 98 or the roads marked red on the sheriff's LSV map.",
  gc=dict(allowed="no", roads="Not on any public road", speed_line="n/a", notes="Walton County Sheriff"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less, except red roads on the sheriff's map", speed_line="35 mph", notes="Cross US 98 only at a four-way intersection"),
  rules=[("Golf carts","Golf carts are not legally permitted on any public roadway at any time","Walton County Sheriff LSV laws",WCSO),
         ("LSV roads","LSVs only on roads with speed limits of 35 mph or less; not on sidewalks or bike paths","Walton County Sheriff LSV laws",WCSO),
         ("US 98","No LSVs on US 98 or its sidewalk; cross only at a four-way intersection","Walton County Sheriff LSV laws",WCSO),
         ("LSV equipment","Registered, tagged LSV with a VIN, seat belts, lights and mirrors; licensed driver","F.S. 316.2122",FLS+"316.2122"),
         ("Safety sticker","LSVs on county-jurisdiction roads must display the county LSV safety sticker","Walton County Sheriff LSV laws",WCSO)],
  banned=[("US 98","No LSVs; cross only at a four-way intersection",True),
          ("CR 283 (US 98 to the bay and south to 30A)","Red on the sheriff's LSV map",False),
          ("CR 395 north of the Point Washington fire station","Red on the sheriff's LSV map",False),
          ("CR 83 from Chat Holley Rd south past US 98","Red on the sheriff's LSV map",False),
          ("Alys Beach, Seacrest Beach and Rosemary Beach town streets (about 70)","Red on the sheriff's LSV map",False),
          ("Seaside town-center streets (12)","Red on the sheriff's LSV map",False)],
  faq=[("Can I drive a regular golf cart on 30A?","No. The Walton County Sheriff says golf carts are not legally permitted on any public roadway. Only registered, tagged LSVs may use 30A."),
       ("Can an LSV drive on 30A itself?","Yes. 30A is not red on the sheriff's LSV map, so registered LSVs may use it. US 98 is off limits except to cross at a four-way intersection."),
       ("Where do I get the LSV safety sticker?","The Walton County Sheriff's Office hands it out at its Santa Rosa Beach administration office, 133 Sheriff Drive, weekdays 8 am to 5 pm.")],
  sources=[WCSO, WMAP])
P["hhi"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, with limits. In {n}, a permitted, insured golf cart may use secondary roads posted 35 mph or less, in daylight, within 4 miles of its registration address. Street-legal LSVs may use roads posted 35 mph or less. Carts stay off US 278 and the Cross Island Parkway.",
  gc=dict(allowed="limited", roads="Secondary roads posted 35 mph or less", speed_line="35 mph", notes="Daylight, within 4 mi of registration, SCDMV permit and insurance"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Registered and insured like a car"),
  rules=[("Golf cart roads","Secondary highway or street posted 35 mph or less","S.C. golf cart law (SCDPS)",SCDPS),
         ("Distance","Within 4 miles of the registration address (or a gated community entrance)","S.C. golf cart law (SCDPS)",SCDPS),
         ("Hours","Daylight only, unless a local ordinance says otherwise","S.C. Code 56-2-90 (SCDPS)",SCDPS),
         ("Driver and permit","Driver 16+ with a license; cart permitted, registered with SCDMV and insured","S.C. golf cart law (SCDPS)",SCDPS)],
  banned=[("US 278 (William Hilton Pkwy, Fording Island Rd)","Primary road; carts not allowed",True),("Cross Island Parkway","Primary road; carts not allowed",False),("SC 46","Primary road; carts not allowed",True)],
  faq=[("Can I drive a golf cart at night in {n}?","Not under the state default. South Carolina allows golf carts on public roads in daylight only unless a local ordinance sets other hours."),
       ("How far can I drive a golf cart from home?","Within 4 miles of the address on the cart's SCDMV registration, or of a gated community entrance if you live inside one."),
       ("Can I drive a golf cart on US 278?","No. US 278 is a primary road, and South Carolina only allows golf carts on secondary roads posted 35 mph or less.")],
  sources=[SCDPS, "https://hiltonheadislandsc.gov/news/news.cfm?NewsID=3193"])
P["sd"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="A street-legal LSV can drive on {n} streets posted 35 mph or less under CVC 21260. A plain golf cart is limited to streets posted 25 mph or less in a business or residence district (CVC 21716). Freeways like I-5 are off limits. Posted signs win.",
  gc=dict(allowed="limited", roads="Streets posted 25 mph or less", speed_line="25 mph", notes="Business or residence district only"),
  lsv=dict(allowed="yes", roads="Streets posted 35 mph or less", speed_line="35 mph", notes="May cross faster roads at intersections"),
  rules=[("LSV roads","Only roads posted 35 mph or less","CVC 21260",CA+"21260."),
         ("Golf carts","Roads posted 25 mph or less in a business or residence district","CVC 21716",CA+"21716.")],
  banned=[("I-5 and other freeways","Freeway",False)],
  faq=[("Can an LSV drive on a 40 mph road in {n}?","No. California limits LSVs to roads posted 35 mph or less (CVC 21260). They may cross a faster road at an intersection."),
       ("Can a regular golf cart drive on {n} streets?","Only on streets posted 25 mph or less in a business or residence district (CVC 21716), unless a local golf cart plan says otherwise.")],
  sources=[CA+"21260.", CA+"21716."])
VS = "https://www.districtgov.org/wp-content/uploads/2024/10/Golf-Car-Rules-of-the-Road.pdf"
P["villages"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes. In {n}, golf carts use the multi-modal paths and streets the county or city has designated, but not roads posted 35 mph or more. Street-legal LSVs may use roads posted 35 mph or less. Cross US 27/441, US 301 and SR 44 only at tunnels, bridges or signed crossings.",
  gc=dict(allowed="yes", roads="Multi-modal paths and designated streets under 35 mph", speed_line="30 mph", notes="Use tunnels, bridges or signed crossings at major roads"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Registered and tagged; multi-modal paths allowed"),
  rules=[("Golf cart roads","Golf carts only on roads a county or city has designated and signed","F.S. 316.212",FLS+"316.212"),
         ("District rule","Golf carts may not use roadways posted 35 mph or more","District Golf Car Rules of the Road",VS),
         ("Sumter County","County golf cart ordinance designates cart routes in the retirement community","Sumter County golf cart ordinance","https://www.sumtercountyfl.gov/AgendaModule/AI7446/Golf%20Cart%20Ordinance%20Amendment%20-%20Final%20(00268768).pdf"),
         ("LSVs","Registered LSVs on roads posted 35 mph or less","F.S. 316.2122",FLS+"316.2122")],
  banned=[("US 27/441","State highway; cross at tunnels, bridges or signed crossings",True),("US 301","State highway",True),("SR 44","State highway",True)],
  faq=[("Do I need a license to drive a golf cart in {n}?","Florida requires golf cart drivers on public roads to be at least 14; LSV drivers need a valid driver's license and the LSV must be registered and insured."),
       ("Can golf carts use roads posted 35 mph in {n}?","No. The District's rules prohibit golf carts on roadways posted 35 mph or more; use the multi-modal paths, tunnels and bridges instead.")],
  sources=[VS, FLS+"316.212"])
PTCO = "https://mcclibraryfunctions-stage.azurewebsites.us/api/ordinanceDownload/11414/1250481/pdf"
P["ptc"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes. Golf carts use the {n} multi-use path network. The city ordinance bars carts from Hwy 74, Hwy 54, Peachtree Parkway and Crosstown Rd between Peachtree Parkway and Hwy 74, except at crossings. Street-legal LSVs may use roads posted 35 mph or less.",
  gc=dict(allowed="yes", roads="Multi-use paths and city streets the ordinance allows", speed_line="n/a", notes="Not on Hwy 74, Hwy 54 or Peachtree Pkwy"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Georgia LSV law"),
  rules=[("Barred roads","Carts barred from Hwy 74, Hwy 54, Peachtree Pkwy and Crosstown Rd (Peachtree Pkwy to Hwy 74) except to cross","Peachtree City cart ordinance",PTCO),
         ("Paths","Golf carts use the city's multi-use path network","Peachtree City: Paths and motorized carts","https://peachtree-city.org/navigateptc")],
  banned=[("Hwy 74 (Joel Cowan Pkwy)","Carts barred except at crossings",True),("Hwy 54","Carts barred except at crossings",True),("Peachtree Parkway / N Peachtree Parkway","Carts barred except at crossings",True),("Crosstown Rd (Peachtree Pkwy to Hwy 74)","Carts barred except at crossings",True)],
  faq=[("Can I drive a golf cart on Peachtree Parkway?","No. The city ordinance bars carts from Peachtree Parkway except to cross it."),
       ("Where can golf carts go in {n}?","On the city's multi-use path network and the streets the ordinance allows, crossing the big highways at the path tunnels and bridges.")],
  sources=[PTCO, "https://peachtree-city.org/navigateptc"])
GSO = "https://www.gulfshoresal.gov/AgendaCenter/ViewFile/Item/15481?fileID=45110"
P["gulfshores"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, on low-speed streets. In {n}, state-tagged golf carts and LSVs may only use streets posted 25 mph or less, and not the state highways (AL 59, 180, 182 and 161). Posted signs win.",
  gc=dict(allowed="limited", roads="Streets posted 25 mph or less", speed_line="25 mph", notes="State tag required"),
  lsv=dict(allowed="limited", roads="Streets posted 25 mph or less", speed_line="25 mph", notes="Local cap is lower than the usual 35"),
  rules=[("Speed cap","Carts and LSVs not on streets posted over 25 mph","Gulf Shores Sec. 21-13 (Apr 13 2026)",GSO),
         ("Designated streets","City list of designated cart streets","Gulf Shores designated cart streets","https://www.gulfshoresal.gov/AgendaCenter/ViewFile/Item/15531?fileID=45381"),
         ("Orange Beach","Orange Beach cart ordinance (designated streets, 25 mph cap)","Orange Beach Ord. 2025-1521","https://library.municode.com/al/orange_beach/ordinances/code_of_ordinances?nodeId=2025")],
  banned=[("AL 59","State highway",True),("AL 180 (Fort Morgan Rd / Canal Rd)","State highway",True),("AL 182 (Beach Blvd / Perdido Beach Blvd)","State highway",True),("AL 161","State highway",True),("Foley Beach Express","Not a cart street",False)],
  faq=[("Can I drive a golf cart on Beach Blvd?","No. Beach Blvd is AL 182, a state highway, and carts and LSVs are limited to streets posted 25 mph or less."),
       ("Does an LSV get more roads than a golf cart in {n}?","Not here. The local rule caps both at streets posted 25 mph or less.")],
  sources=[GSO])
MB = "https://www.cityofmyrtlebeach.com/news_detail_T6_R2337.php"
P["myrtle"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, with limits. In {n}, a permitted, insured golf cart may use secondary streets posted 35 mph or less, in daylight, within 4 miles of its registered address. Carts are not allowed on Kings Highway, US 501, US 17 or other primary roads, or in bike lanes.",
  gc=dict(allowed="limited", roads="Secondary streets posted 35 mph or less", speed_line="35 mph", notes="Daylight, within 4 mi of registration"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Registered and insured like a car"),
  rules=[("Primary roads","No golf carts on Kings Highway, US 501 or roads posted over 35 mph","City of Myrtle Beach golf cart rules",MB),
         ("Golf cart roads","Secondary streets posted 35 mph or less, daylight, within 4 miles of the registered address","S.C. golf cart law (SCDPS)",SCDPS),
         ("Sidewalks","Not on sidewalks, multipurpose lanes or bike lanes; no more riders than seats","City of Myrtle Beach golf cart rules",MB)],
  banned=[("Kings Highway (US 17 Business)","Primary road",True),("US 501","Primary road",True),("US 17 Bypass","Primary road",True),("SC 31 (Carolina Bays Pkwy)","Primary road",False),("SC 22, SC 707, SC 544","Primary roads",True)],
  faq=[("Can I drive a golf cart on Kings Highway?","No. The City of Myrtle Beach says golf carts are not allowed on Kings Highway, US 501 or any road posted over 35 mph."),
       ("Can kids drive golf carts in {n}?","No. Only licensed drivers may drive golf carts on public streets.")],
  sources=[MB, SCDPS])
PA = "https://cityofportaransas.org/golf-cart-information-and-regulations/"
PAP = "https://cityofportaransas.org/wp-content/uploads/2026/02/Golf-Cart-Laws-Strictly-Enforced.pdf"
P["portaransas"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, with a city golf cart plate. In {n}, a licensed, insured golf cart with lights, reflectors, seat belts and a slow-moving vehicle emblem may use city streets. Carts are prohibited on Hwy 361 south of Avenue G. ATVs and UTVs are not allowed.",
  gc=dict(allowed="yes", roads="City streets with a city golf cart plate", speed_line="n/a", notes="Plate renews every Jan 1"),
  lsv=dict(allowed="yes", roads="Roads posted 45 mph or less under state law; the map plans on 35 mph or less", speed_line="45 mph", notes="State-registered LSV/NEV (Tex. Transp. Code 551.304)"),
  rules=[("Golf cart plate","City golf cart license and plate required on public streets; renews each calendar year","Port Aransas Golf Cart Ordinance Art. VIII",PA),
         ("Equipment","Head lamps, tail lamps, reflectors, seat belts, SMV emblem, parking brake, mirror; no engine mods","Port Aransas golf cart regulations",PA),
         ("Hwy 361","Carts prohibited on Hwy 361 south of Avenue G","Port Aransas: Golf Cart Laws Strictly Enforced",PAP),
         ("ATVs","ATVs and UTVs are not golf carts and are not allowed in city limits, including the beach","Port Aransas golf cart regulations",PA)],
  banned=[("Hwy 361 south of Avenue G","Carts prohibited",False)],
  faq=[("How much is a Port Aransas golf cart plate?","$50 a year for year-round residents and $100 for non-residents; plates expire December 31."),
       ("Can I drive a UTV or ATV in Port Aransas?","No. The city says ATVs and UTVs are not golf carts and are not allowed anywhere in city limits, including the beach.")],
  sources=[PA, PAP])
P["naples"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Only where the city or county has designated it. Florida lets golf carts use only roads a local government has designated and signed. Street-legal LSVs may use roads posted 35 mph or less. US 41, SR 84, SR 951 and I-75 are off limits.",
  gc=dict(allowed="limited", roads="Only designated and signed roads", speed_line="n/a", notes="Check local signs"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Registered and tagged"),
  rules=[("Golf carts","Only on roads a county or city has designated and signed","F.S. 316.212",FLS+"316.212"),
         ("LSVs","Registered LSVs on roads posted 35 mph or less","F.S. 316.2122",FLS+"316.2122"),
         ("Local code","Marco Island traffic code (ch. 50)","Marco Island Code ch. 50","https://library.municode.com/fl/marco_island/codes/code_of_ordinances?nodeId=PTIICOOR_CH50TRVE")],
  banned=[("US 41 (Tamiami Trail)","State highway",True),("SR 84 (Davis Blvd)","State road",True),("SR 951 (Collier Blvd)","State road",True),("I-75","Interstate",False)],
  faq=[("Can I drive an LSV on US 41 in {n}?","No. US 41 is a state highway that is not designated for carts, and Florida limits LSVs to roads posted 35 mph or less. The map only lets you cross it."),
       ("Can a plain golf cart drive on {n} streets?","Only on roads the city or county has designated and signed for golf carts (F.S. 316.212).")],
  sources=[FLS+"316.212", FLS+"316.2122"])
SCH = "https://suncityhoa.org/golf-carts-in-sun-city/"
AZ = "https://www.azleg.gov/ars/28/00966.htm"
P["suncity"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, if it is registered. In {n}, the Maricopa County Sheriff's Office recommends golf carts stay on roads posted 35 mph or less. Bell Road, Grand Avenue and 99th Avenue are faster roads it calls unsafe for carts. Street-legal LSVs may use roads posted 35 mph or less.",
  gc=dict(allowed="yes", roads="Roads posted 35 mph or less (MCSO guidance)", speed_line="35 mph", notes="Registered with the state; licensed driver"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="May cross faster roads"),
  rules=[("Golf carts","Stay on roads posted 35 mph or less; Bell Rd, Grand Ave and 99th Ave are unsafe for carts","Sun City HOA (MCSO guidance)",SCH),
         ("Registration","Golf carts on roads must be registered with the state; driver needs a valid license","Sun City HOA",SCH),
         ("LSVs","LSVs/NEVs on roads posted 35 mph or less","A.R.S. 28-966",AZ)],
  banned=[("US 60 (Grand Avenue)","State highway; MCSO calls it unsafe for carts",True),("Loop 101 and Loop 303","Freeways",False)],
  faq=[("Can I drive a golf cart on Bell Road?","The Maricopa County Sheriff's Office lists Bell Road as a higher-speed road that is unsafe for golf carts; stay on roads posted 35 mph or less."),
       ("Do golf carts in {n} need to be registered?","Yes. Golf carts on Sun City roads must be registered with the state, and the driver needs a valid driver's license.")],
  sources=[SCH, AZ])
NOC = "https://www.nocatee.com/golfcartmap"
NOCREG = "https://tmwha.org/wp-content/uploads/2017/11/SJCGolfCartRegulations.pdf"
SJC = "https://www.sjcfl.us/st-johns-county-adopts-golf-cart-ordinance-conforming-to-state-statute/"
VRB = "https://www.artisanlakeshoa.com/editor_upload/File/General/2022-11-04%20Golf%20Carts%20on%20Valley%20Ridge.pdf"
P["nocatee"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="Yes, electric golf carts. St. Johns and Duval county ordinances let them use Nocatee roads posted 25 mph or less, signed golf cart paths and designated multi-use trails. Street-legal LSVs may use roads posted 35 mph or less. Nocatee Parkway, CR 210, US 1 and Valley Ridge Blvd are off limits.",
  gc=dict(allowed="yes", roads="Nocatee roads posted 25 mph or less, signed cart paths and designated multi-use trails", speed_line="25 mph", notes="Electric carts only; 15 mph on multi-use paths"),
  lsv=dict(allowed="yes", roads="Roads posted 35 mph or less", speed_line="35 mph", notes="Registered and tagged"),
  rules=[("Golf cart roads","Roads within Nocatee with a posted speed limit of 25 mph or less and designated golf cart multi-use paths with signage are approved for electric golf carts","Nocatee Golf Cart Map",NOC),
         ("Paths and trails","Signed golf cart paths at least 10 feet wide and multipurpose trails at least 16 feet wide designated for golf carts; not pedestrian sidewalks","St. Johns County and Duval County golf cart regulations for Nocatee",NOCREG),
         ("Path speed","Golf carts and LSVs on a multi-use path are limited to 15 mph and must yield to pedestrians and bicycles","St. Johns County Ord. 2024-7",SJC),
         ("Drivers","Under 18 needs a learner's permit or driver's license; 18 and older needs government-issued photo ID","St. Johns County Ord. 2024-7",SJC),
         ("LSVs","Registered LSVs on roads posted 35 mph or less","F.S. 316.2122",FLS+"316.2122")],
  banned=[("Nocatee Parkway (CR 210)","45-55 mph limited-access parkway",False),("CR 210 / Palm Valley Rd","County road over 35 mph",True),("US 1","State highway, 45+ mph",True),("Valley Ridge Blvd","Posted 45 mph; carts not allowed in the street",True),("Cross Town Dr","Multilane divided road posted 40 mph; carts use cart crossings only",True),("Crosswater Pkwy","Main road posted 35-45 mph; not shown as golf-cart legal",True)],
  faq=[("Can I drive a golf cart on Valley Ridge Blvd in {n}?","No. Valley Ridge Blvd is posted 45 mph, so golf carts aren't allowed in the street. Use the greenway trails where they connect."),
       ("Can I drive a golf cart at night in {n}?","Only if it has headlights, brake lights, turn signals and a windshield, under the Nocatee golf cart rules.")],
  sources=[NOC, NOCREG, SJC, VRB, FLS+"316.212"])
SHC = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=SHC&sectionNum=1953."
MB1428 = "https://gocodebook.com/library/us/ca/manhattan-beach/title-14-traffic/chapter-14.28-miscellaneous-driving-rules"
HB1220 = "https://online.encodeplus.com/regs/hermosabeach-ca/doc-view.aspx?secid=1685"
HB1040 = "https://gocodebook.com/library/us/ca/hermosa-beach/title-10-vehicles-and-traffic/chapter-10.40-speed-regulations"
P["southbay"] = dict(
  q="Can you drive a golf cart in {n}?",
  a="A street-legal LSV can drive on {n} streets posted 35 mph or less (CVC 21260). A plain golf cart is limited to streets posted 25 mph or less in a business or residence district (CVC 21716) and may only cross Pacific Coast Highway. Freeways and the Strand are off limits. Posted signs win.",
  gc=dict(allowed="limited", roads="Streets posted 25 mph or less", speed_line="25 mph", notes="Business or residence district only; cross PCH at intersections"),
  lsv=dict(allowed="yes", roads="Streets posted 35 mph or less", speed_line="35 mph", notes="May cross faster roads at intersections"),
  rules=[("LSV roads","Only roads posted 35 mph or less","CVC 21260",CA+"21260."),
         ("Golf carts","Roads posted 25 mph or less in a business or residence district","CVC 21716",CA+"21716."),
         ("State highways","A golf cart plan can't put carts on a state highway such as PCH (SR-1), except to cross it","Streets & Highways Code 1953",SHC),
         ("The Strand, Manhattan Beach","No motor vehicles on the Strand or the pier","Manhattan Beach Municipal Code ch. 14.28",MB1428),
         ("The Strand, Hermosa Beach","No motor vehicles on the Strand or Pier Plaza","Hermosa Beach Municipal Code 12.20.220",HB1220),
         ("Hermosa Beach streets","Every street not listed in the code is 25 mph","Hermosa Beach Municipal Code 10.40.020",HB1040)],
  banned=[("I-405, I-105, I-110 and SR-91","Freeway",False),("The Strand","Beach walkway closed to motor vehicles in Manhattan Beach and Hermosa Beach",False),
          ("Pacific Coast Highway (SR-1)","State highway: golf carts may only cross. LSVs only where it's posted 35 mph or less",True)],
  faq=[("Can I drive a golf cart on Pacific Coast Highway in {n}?","No. PCH is a state highway posted over 25 mph, so a plain golf cart may only cross it at intersections. A street-legal LSV may use stretches posted 35 mph or less."),
       ("Can I drive an LSV on the Strand?","No. The Strand in Manhattan Beach and Hermosa Beach is a beach walkway closed to motor vehicles under each city's code, so it isn't drawn on the map.")],
  sources=[CA+"21260.", CA+"21716.", SHC, MB1428, HB1220, HB1040], day="2026-10-22")
# (region, slug, name, state, lat, lng, extra faq)
T = [
 ("30a","miramar-beach","Miramar Beach","FL",30.3790,-86.3700),("30a","sandestin","Sandestin","FL",30.3830,-86.3270),
 ("30a","dune-allen-beach","Dune Allen Beach","FL",30.3420,-86.2430),("30a","santa-rosa-beach","Santa Rosa Beach","FL",30.3720,-86.2280),
 ("30a","blue-mountain-beach","Blue Mountain Beach","FL",30.3340,-86.2040),("30a","grayton-beach","Grayton Beach","FL",30.3290,-86.1640),
 ("30a","point-washington","Point Washington","FL",30.3720,-86.1200),("30a","watercolor","WaterColor","FL",30.3260,-86.1440),
 ("30a","seaside","Seaside","FL",30.3210,-86.1390),("30a","seagrove-beach","Seagrove Beach","FL",30.3150,-86.1250),
 ("30a","watersound-beach","WaterSound Beach","FL",30.2950,-86.0390),("30a","seacrest-beach","Seacrest Beach","FL",30.2850,-86.0100),
 ("30a","alys-beach","Alys Beach","FL",30.2890,-86.0250),("30a","rosemary-beach","Rosemary Beach","FL",30.2800,-85.9960),
 ("30a","inlet-beach","Inlet Beach","FL",30.2740,-85.9780),
 ("hiltonhead","hilton-head-island","Hilton Head Island","SC",32.1830,-80.7400),("hiltonhead","bluffton","Bluffton","SC",32.2370,-80.8600),
 ("hiltonhead","north-forest-beach","North Forest Beach","SC",32.1550,-80.7420),("hiltonhead","south-forest-beach","South Forest Beach (Coligny)","SC",32.1430,-80.7530),
 ("sandiego","imperial-beach","Imperial Beach","CA",32.5780,-117.1150),("sandiego","coronado","Coronado","CA",32.6860,-117.1830),
 ("sandiego","point-loma","Point Loma","CA",32.7300,-117.2300),("sandiego","ocean-beach","Ocean Beach","CA",32.7480,-117.2470),
 ("sandiego","mission-beach","Mission Beach","CA",32.7700,-117.2520),("sandiego","pacific-beach","Pacific Beach","CA",32.7978,-117.2400),
 ("sandiego","la-jolla","La Jolla","CA",32.8470,-117.2740),("sandiego","del-mar","Del Mar","CA",32.9590,-117.2650),
 ("sandiego","solana-beach","Solana Beach","CA",32.9910,-117.2710),("sandiego","cardiff","Cardiff-by-the-Sea","CA",33.0170,-117.2800),
 ("sandiego","encinitas","Encinitas","CA",33.0450,-117.2930),("sandiego","leucadia","Leucadia","CA",33.0650,-117.3030),
 ("sandiego","carlsbad","Carlsbad","CA",33.1580,-117.3500),("sandiego","oceanside","Oceanside","CA",33.1960,-117.3790),
 ("villages","the-villages","The Villages","FL",28.9000,-81.9900),("villages","lady-lake","Lady Lake","FL",28.9170,-81.9230),
 ("villages","wildwood","Wildwood","FL",28.8650,-82.0400),
 ("peachtreecity","peachtree-city","Peachtree City","GA",33.3970,-84.5960),
 ("gulfshores","gulf-shores","Gulf Shores","AL",30.2460,-87.7000),("gulfshores","orange-beach","Orange Beach","AL",30.2700,-87.5860),
 ("myrtlebeach","myrtle-beach","Myrtle Beach","SC",33.6890,-78.8870),("myrtlebeach","north-myrtle-beach","North Myrtle Beach","SC",33.8160,-78.6800),
 ("myrtlebeach","surfside-beach","Surfside Beach","SC",33.6060,-78.9730),
 ("portaransas","port-aransas","Port Aransas","TX",27.8340,-97.0610),("portaransas","mustang-island","Mustang Island","TX",27.7500,-97.1300),
 ("naples","naples","Naples","FL",26.1420,-81.7950),("naples","vanderbilt-beach","Vanderbilt Beach","FL",26.2560,-81.8150),
 ("naples","marco-island","Marco Island","FL",25.9410,-81.7180),
 ("suncity","sun-city","Sun City","AZ",33.6120,-112.2810),("suncity","sun-city-west","Sun City West","AZ",33.6620,-112.3410),
 ("suncity","youngtown","Youngtown","AZ",33.5940,-112.3030),
 ("nocatee","ponte-vedra","Nocatee, Ponte Vedra","FL",30.1050,-81.4150),
 ("southbay","el-segundo","El Segundo","CA",33.9192,-118.4165),("southbay","manhattan-beach","Manhattan Beach","CA",33.8847,-118.4109),
 ("southbay","hermosa-beach","Hermosa Beach","CA",33.8622,-118.3995),("southbay","redondo-beach","Redondo Beach","CA",33.8492,-118.3884),
 ("southbay","torrance","Torrance","CA",33.8358,-118.3406),("southbay","palos-verdes-estates","Palos Verdes Estates","CA",33.7870,-118.3965),
 ("southbay","rolling-hills-estates","Rolling Hills Estates","CA",33.7878,-118.3581),("southbay","rancho-palos-verdes","Rancho Palos Verdes","CA",33.7445,-118.3870),
]
RID = {"30a":"30a","hiltonhead":"hhi","sandiego":"sd","villages":"villages","peachtreecity":"ptc","gulfshores":"gulfshores","myrtlebeach":"myrtle","portaransas":"portaransas","naples":"naples","suncity":"suncity","nocatee":"nocatee","southbay":"southbay"}
EXTRA = {
 "manhattan-beach": ("Can I drive an LSV on Sepulveda Boulevard in Manhattan Beach?","Yes, an LSV may: Sepulveda (SR-1) is posted 35 mph through Manhattan Beach. A plain golf cart may only cross it."),
 "hermosa-beach": ("What is the speed limit on most Hermosa Beach streets?","25 mph. Hermosa Beach Municipal Code 10.40.020 makes every street it doesn't list 25 mph, so most Hermosa residential streets are golf-cart legal."),
 "redondo-beach": ("Can I drive an LSV on PCH in Redondo Beach?","Only where it's posted 35 mph or less. Redondo's code posts PCH at 35 mph from Palos Verdes Boulevard north to 190th Street and 40-45 mph farther southeast."),
 "torrance": ("Can I drive an LSV on PCH in Torrance?","Only west of Palos Verdes Boulevard, where Torrance's code posts PCH at 35 mph. East of there it's posted 40-45 mph."),
 "palos-verdes-estates": ("Can I drive an LSV on Palos Verdes Drive West in Palos Verdes Estates?","Yes. Palos Verdes Estates' code posts it 35 mph, so LSVs may use it. A plain golf cart may not, because it's over 25 mph."),
 "rolling-hills-estates": ("Can I drive into Rolling Hills from Rolling Hills Estates?","Only with resident gate access. Rolling Hills is a gated private city, so its roads aren't drawn on the map."),
 "rancho-palos-verdes": ("Can I drive an LSV on Hawthorne Boulevard in Rancho Palos Verdes?","No. Hawthorne Boulevard is posted 45 mph in Rancho Palos Verdes, above the 35 mph LSV limit. Cross it only at intersections."),
 "el-segundo": ("Can I drive an LSV on Vista del Mar in El Segundo?","No. El Segundo's code posts Vista del Mar at 45 mph, above the 35 mph LSV limit."),
 "seaside": ("Can I drive an LSV into Seaside's town center?","No. The 12 Seaside town-center streets are red on the Walton County Sheriff's LSV map, so LSVs are prohibited there. 30A itself stays open."),
 "alys-beach": ("Can I drive an LSV on Alys Beach streets?","No. The Alys Beach town streets are red on the Walton County Sheriff's LSV map, so LSVs are prohibited there; 30A through town stays open."),
 "rosemary-beach": ("Can I drive an LSV on Rosemary Beach streets?","No. Rosemary Beach's town streets are red on the Walton County Sheriff's LSV map, so LSVs are prohibited there; 30A stays open."),
 "seacrest-beach": ("Can I drive an LSV on Seacrest Beach streets?","No. The Seacrest Beach streets are red on the Walton County Sheriff's LSV map, so LSVs are prohibited there; 30A stays open."),
 "grayton-beach": ("Can I take an LSV up CR 283 from Grayton Beach?","No. CR 283 is red on the Walton County Sheriff's LSV map, so LSVs are prohibited on it."),
 "point-washington": ("Can I drive an LSV on CR 395 in Point Washington?","Not north of the Point Washington fire station: that stretch of CR 395 is red on the Walton County Sheriff's LSV map."),
}
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import towns_r25 as R25   # regions-25-batch (Oct 22 2026): profiles, towns and slug map for the 25 new regions
P.update(R25.P); T += R25.T; RID.update(R25.RID)
def nearby(i):
    reg = T[i][0]; same = [j for j in range(len(T)) if T[j][0] == reg and j != i]
    same.sort(key=lambda j: abs(j - i)); return [T[j][1] for j in same[:3]]
def main():
    out = os.path.join(ROOT, "content", "towns")
    for i, (reg, slug, name, st, lat, lng) in enumerate(T):
        p = P[RID[reg]]; f = lambda s: s.format(n=name)
        faq = [{"q": f(q), "a": f(a)} for q, a in p["faq"]] + ([{"q": EXTRA[slug][0], "a": EXTRA[slug][1]}] if slug in EXTRA else [])
        if not any("drive my LSV" in x["q"] for x in faq):   # Max Oct 23: answer "where can I drive my LSV in [town]" from the sourced LSV row
            lv = p["lsv"]; faq.insert(0, {"q": f"Where can I drive my LSV in {name}?", "a": f(lv["roads"]).rstrip(".") + "." + (" " + f(lv["notes"]).rstrip(".") + "." if lv.get("notes") else "")
                                         + " A town or county can still ban LSVs from a specific road, and posted signs win."})
        t = {"slug": slug, "region": reg, "name": name, "state": st, "question_title": f(p["q"]), "answer_short": f(p["a"]),
             "golf_cart": p["gc"], "lsv": p["lsv"],
             "rules": [{"topic": a, "rule": b, "citation": c, "source_url": d} for a, b, c, d in p["rules"]],
             "banned_roads": [{"name": a, "rule": b, "crossings_ok": c} for a, b, c in p["banned"]],
             "faq": faq, "rental_shops": [], "nearby": nearby(i), "map_center": [lat, lng], "zoom": 15,
             "published": p.get("day", DAY), "last_checked": p.get("day", DAY), "checked_by": "Golf Cart Maps", "sources": p["sources"]}
        d = os.path.join(out, reg); os.makedirs(d, exist_ok=True)
        fp = os.path.join(d, slug + ".json")   # keep hand-added local_resources (followed links) on regenerate
        if os.path.exists(fp) and json.load(open(fp)).get("local_resources"):
            ks = list(t); cut = ks.index("rental_shops") + 1
            t = {**{k: t[k] for k in ks[:cut]}, "local_resources": json.load(open(fp))["local_resources"], **{k: t[k] for k in ks[cut:]}}
        open(fp, "w").write(json.dumps(t, indent=1, ensure_ascii=False) + "\n")   # trailing newline, like the committed files
    print(len(T), "towns")
if __name__ == "__main__": main()
