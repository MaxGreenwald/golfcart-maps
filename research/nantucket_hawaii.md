# Nantucket, Hawaii, Mackinac Island, Martha's Vineyard: worth adding? (research Oct 17, 2026)

Research only, nothing built. OSM check = Overpass, drivable ways (motorway..living_street incl. links), share with any `maxspeed` tag. Raw script: /workspace/ovp.py, ovp2.py.

## Verdicts
- **Hawaii (Maui/Kauai/Big Island/Oahu pockets): MAYBE, leaning good add.** The law fits the app as-is (NEV/LSV on roads posted ≤35, HRS 291C-134), and real LSV rental shops exist in Wailea/Kaanapali, Poipu, Mauna Lani/Waikoloa and Kailua. But OSM maxspeed is thin on residential streets, so it needs the inherited/assumed-speed logic plus overrides, and the rules are electric-only (no gas carts).
- **Nantucket: MAYBE (only if we add a 30 mph mode).** In MA an LSV is legal only where the limit is ≤30 mph (MGL c.90 §1F/§1G), not ≤35, so the app's current threshold would show illegal roads as green. Rental evidence is thin.
- **Martha's Vineyard: SKIP for now.** Same 30 mph MA rule, OSM maxspeed is only about 5%, and the local transport is mopeds, Jeeps and e-bikes. I found no verified LSV rental shop; a 2026 local guide says carts aren't street-legal there.
- **Mackinac Island: SKIP.** Motor vehicles are banned, including golf carts (allowed only on golf courses while golfing) and LSVs. The only exceptions are mobility devices, permitted disability e-bikes and emergency/permit vehicles. There is no road-legality question to map.

## Law
- **Massachusetts:** an LSV must be FMVSS 500, registered, titled, insured, inspected, with a licensed driver. It may use any public way except limited-access/express highways and ways with a limit **over 30 mph**, and towns can bar more roads. Plain golf carts are not road-legal. [mass.gov LSV](https://www.mass.gov/info-details/low-speed-vehicles), [Acts 2008 c.523 (creates §1F)](https://malegislature.gov/Laws/SessionLaws/Acts/2008/Chapter523), [§1G rental disclosure](https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXIV/Chapter90/Section1G). Several rental/SEO sites claim "35 mph", which is wrong.
- **Nantucket:** 25 mph default in thickly settled areas ([Ch. 375 Traffic](https://ecode360.com/32944020)). Golf carts are exempt only from the motorized-device bylaw ([Ch. 98](https://ecode360.com/11470762)), which doesn't make them road-legal. Rental vehicles need a town medallion, capped at 700 per year ([rental licensing](https://www.nantucket-ma.gov/2302/Rental-Car-Licensing)). LSV/golf-cart zones are being discussed, not enacted ([Below Deck Nantucket](https://www.belowdecknantucket.com/traffic)).
- **Martha's Vineyard:** state LSV law applies. I found no town LSV bylaw for Edgartown, Oak Bluffs or Tisbury (Vineyard Haven). Oak Bluffs, the only town that still rents mopeds, cut moped rentals in Nov 2025 to 3 shops and 178 decals, single rider ([MV Times](https://www.mvtimes.com/2025/11/04/oak-bluffs-passes-moped-rental-restrictions/), [Gazette](https://vineyardgazette.com/news/2025/11/05/oak-bluffs-restricts-rental-mopeds-just-driver)).
- **Hawaii:** the only street class is the "neighborhood electric vehicle" (electric, 4 wheels, under 3,000 lb, FMVSS 500, county-registered). It can go up to 25 mph on roads posted ≤35 and cross faster roads at intersections, but not controlled-access highways. Hawaii has no golf-cart road category. [HRS 291C-134](https://www.capitol.hawaii.gov/hrscurrent/Vol05_Ch0261-0319/HRS0291C/HRS_0291C-0134.HTM), [291C-53](https://www.capitol.hawaii.gov/hrscurrent/Vol05_Ch0261-0319/HRS0291C/HRS_0291C-0053.htm), [AFDC summary](https://afdc.energy.gov/laws/5598).
  - Hawaii County Code ch. 24 div. 6 (§24-177) bars golf carts from public roads except at marked crossings ([county code](https://records.hawaiicounty.gov/WebLink/1/doc/100891/Page7.aspx)).
  - Ko Olina (Oahu) is a private resort where carts and LSVs register with the community association (KOCA) ([KOCA](https://koolina.com/koca/)).
  - Maui and Kauai: I found no county ordinance beyond state NEV law. Operators say "Maui County roads ≤35 mph".
- **Mackinac Island:** city ordinance §66-31 and §66-64(4) allow golf carts only when used for golf on a course ([Municode](https://library.municode.com/mi/mackinac_island/codes/code_of_ordinances?nodeId=PTIICOOR_CH66TR_ARTIIMOVE_DIV1GE_S66-31DE), [mackinacisland.org](https://www.mackinacisland.org/blog/post/mackinac-island-rules-for-electric-scooters-skateboards-and-more/)). State Park rules ban motor vehicles without permission and allow only personal assistive mobility devices and Class 1 e-bikes for disabled riders ([R 318.145](https://www.law.cornell.edu/regulations/michigan/Mich-Admin-Code-R-318-145)).

## Rentals in practice
- **Hawaii, real local shops:**
  - Maui: [Island EV](https://islandev.com/where-can-i-drive-golf-carts-on-maui/) and [Beach EV](https://www.beachev.net/faq/) (Wailea/Kihei, Kaanapali). [Kaanapali Karts](https://kaanapalikarts.com/) says "coming soon".
  - Kauai: [Kaua'i Carts](https://www.kauaicarsandcarts.com/carts/) (Poipu/Koloa, Princeville).
  - Big Island: [Resort Carts](https://www.resortcarts.com/), [Kohala Beach Buggies](https://www.kohalabeachbuggies.com/meet-the-fleet) (LSVs required in Mauna Kea and parts of Waikoloa) and [Golf Cars Hawaii](https://www.golfcarshawaii.com/book-online).
  - Oahu: [Kailua Carts](https://www.kailuacarts.com/). Ko Olina has carts owned by residents.
  - Lanai: no cart rentals found, only Jeeps/EVs ([Lanai Car Rental](https://www.lanaicarrental.com/)).
- **Nantucket:**
  - [nantucketgolfcarts.com](https://www.nantucketgolfcarts.com/) lists LSVs at $325/day, but the site shows a placeholder phone and email and a Hyannis address, so it is unverified.
  - [nantucketgolfcartrental.com](https://nantucketgolfcartrental.com/) mostly rents event/utility carts.
  - The College Golf Carts pages look like templated SEO pages.
  - Carts are uncommon in practice. The 700-medallion cap on rentals limits growth.
- **Martha's Vineyard:** only templated SEO pages ([collegegolfcarts](https://collegegolfcarts.com/massachusetts/marthas-vineyard-golf-carts), [massachusettsgolfcarts](https://massachusettsgolfcarts.com/locations/edgartown)). A local guide says golf carts aren't street-legal and electric Mokes come and go ([mvvacation](https://mvvacation.com/blog/marthas-vineyard-car-rental-jeep-moped-guide)).
- **Mackinac:** none, and none allowed.

## OSM maxspeed share (drivable ways, Oct 17 2026)
| Area | Ways | maxspeed | Residential tagged | Tertiary+ tagged |
|---|---|---|---|---|
| Nantucket island | 1349 | 17% | 103/1158 | 117/170 |
| Martha's Vineyard | 2648 | 5% | 101/2377 | 23/208 |
| Mackinac Island | 120 | 98% (10/15 mph) | 92/93 | n/a |
| Maui Kaanapali–Kapalua | 535 | 23% | 11/307 | 100/146 |
| Maui Kihei–Wailea | 828 | 25% | 8/449 | 181/241 |
| Kauai Poipu–Koloa | 258 | 18% | 12/168 | 19/50 |
| Big Island Waikoloa–Mauna Lani | 469 | 58% | 96/223 | 153/164 |
| Oahu Kailua | 737 | 35% | 19/417 | 204/230 |
| Oahu Ko Olina | 136 | 23% | 5/45 | 20/63 |
| Lanai City | 127 | 1% | 1/108 | 0/15 |

Main roads are mostly tagged in the Hawaii resort areas and on Nantucket, but residential streets are not. These areas would need the assumed-residential-speed logic. On MA islands, that logic would have to assume 25 mph and check every 35 mph road against the 30 mph cap.

## Old Orchard Beach, Maine (added Oct 17, 2026)
**Verdict: MAYBE.** The law fits the app's 35 mph threshold as-is, and real street-legal LSV rentals exist. But OSM has almost no speed tags (2 of 531 drivable ways), so the main roads would need hand-entered speed limits and the residential streets would need the 25 mph assumption.

- **Maine law:** an LSV (licensed driver, registered) may use roads posted **35 mph or less** and may cross faster roads at intersections. MaineDOT or a town may ban LSVs on specific roads ([29-A §2089](https://www.legislature.maine.gov/legis/statutes/29-A/title29-Asec2089.html), [§102(2)](https://www.legislature.maine.gov/legis/statutes/29-A/title29-Asec102.html)).
  - Plain golf carts are road-legal only on islands with no state roads ([§501(2-A)](https://legislature.maine.gov/statutes/29-A/title29-Asec501.html)) or with a Secretary of State special permit (§501(8)). The 2017 bill for town golf-cart routes ([LD 878](https://legislature.maine.gov/legis/bills/bills_128th/billtexts/HP062701.asp)) does not appear to have passed. So the app should target LSVs only.
  - The default speed is 25 mph in built-up areas unless posted ([MaineDOT](https://www.maine.gov/dot/programs-services/cslr/mlrc/tech/local-road-traffic-issues)).
- **Town ordinances:** I found no golf cart or LSV ordinance in the OOB code. Chapter 54 (Traffic) and Chapter 62 (Vehicles for hire) don't mention them ([OOB code](https://oob-me.elaws.us/code/coor), [Ch. 54](https://www.oobmaine.com/wp-content/uploads/2022/12/06.07.2011_public_hearing_chapter_54_traffic_and_vehicles.pdf)). That means statewide LSV rules apply.
- **Rentals:**
  - [Coastal Maine Carts](https://coastalmainecarts.com/pages/old-orchard-beach-golf-cart-rentals) is a local shop with street-legal 4- and 6-seat carts, phone (207) 625-2050.
  - [Sarge's LSV Rentals](https://www.sargeslsvrentals.com/) is based in Londonderry, NH and delivers to OOB.
  - [Bayley's Camping Resort](https://bayleysresort.com/resort-information-policies/faq/) in nearby Scarborough rents golf carts on site and allows LSVs for seasonal guests.
  - [streetlegalgolfcartrental.com](https://streetlegalgolfcartrental.com/beaches/old-orchard-beach-main) is a national 1-844 number, possibly a lead-gen site.
- **OSM maxspeed** (bbox 43.48,-70.42,43.54,-70.33): 531 drivable ways, **2 tagged (0.4%)**. Residential: 1 of 472 tagged. Tertiary and above: 1 of 51 tagged.
