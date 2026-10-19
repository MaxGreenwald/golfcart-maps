# SD safety caution: 5 flagged roads (Oct 18 2026)

Flag from the Street View batch-1 rebuild: the map showed a LOWER limit than a sign detection or OpenStreetMap.
Live check (golfcartmap.com tiles, Oct 18 2026, 9:20 AM PT): all five were shown "OK for carts & LSVs" (SD rule: posted <= 35).

Rule used: where a dated sign photo shows the higher posted limit, use it (a local limit takes effect once signs are up, CVC 22357)
and flag the stretch; where only OpenStreetMap disagrees, keep the official value and flag it; where the evidence doesn't hold up, no change.
Flag = dashed orange line, popup line ending "Check posted signs", route-step note, route summary note (CAU list in public/app.js).
Photos (Mapillary, CC-BY-SA, viewed at 2048 px) are linked by feature id: https://www.mapillary.com/app/?focus=map&mapFeatureId=<id>

| Road / stretch | Live | Branch | Evidence |
|---|---|---|---|
| La Jolla Blvd, Loring St - Colima St (Bird Rock; 50 segments, ~1.8 km both carriageways) | 25, OK | **35 + caution** | Mapillary photos Jan 8 2025: SPEED LIMIT 35 northbound at 32.81046,-117.2661 (feature 9238952249552002, readable); 35 at 32.80539,-117.25887 (1123107969555071). OSM maxspeed 35 on 6 ways. Our 25 came from a 2017 Union-Tribune guide and San Diego R-316675 (adopted Mar 16 2026, Table 7: 25 both directions); no photo of a 25 sign yet. Still <= 35, so still OK; flagged. |
| Mission Blvd, Santa Clara Pl - Loring St (139 segments, ~3.6 km) | 25, OK | **30 + caution** | Mapillary photo Jan 8 2025: SPEED LIMIT 30 at Wilbur Ave, 32.8038,-117.2579 (960076746257679, readable); 30 detected at 32.79995 (1563178347972776) and 4 more Jan 2025 detections. KPBS Feb 21 2025: Mission Blvd segments "lowered from 30 to 25" (proposal); R-316675 Table 1 lists it. Still OK; flagged. |
| Mission Blvd, San Fernando Pl - Santa Clara Pl (Mission Beach) | 25, OK | 25 + caution | R-316675 Table 7: 25. Mapillary 30 detections Dec 20 2024 (3960899604187237, 646794851055392), sign not readable in the photos, so no value change. |
| Prospect St (Village) | 25, OK | no change | The Mapillary "35" (1174767567383190, Jan 10 2025) is a parking/curb sign, not a speed limit. R-316675 Table 3 lists Prospect St (Eads Av - Cave St) as a 25 mph business district. |
| S Coast Hwy 101, Cardiff (Swami's - San Elijo) | 30, OK | no change | The 45/40 detections are 2017-2019 photos. Newer: SPEED LIMIT 35 northbound, Oct 3 2023 (205146932586013, readable); Max's Street View Mar + Sep 2025: 30. Current posted is 30-35, both OK. |
| S Coast Hwy 101, Encinitas Blvd - Swami's | 25, OK | no change | Encinitas ordinance 25 (ecode360 LF2740111); 30/45 detections are 2017-2019. |
| Lomas Santa Fe Dr at Hwy 101 (4 short ways, 58 m) | 35, OK | 35 + caution | Solana Beach staff report Jul 12 2023: 35 (Hwy 101 - Stevens). Only OSM says 50 (the rest of the stretch is tagged 35). No sign photo on LSF here. |

Not changed, worth a look: S Coast Hwy 101 in Solana Beach (32.991-33.0, south of the San Elijo bridge) shows 30 because the Cardiff
Street View rule's box reaches past the lagoon; Solana Beach lists 35 (2023 report) and an Oct 25 2018 photo shows 35 at Lomas Santa Fe.
Map is lower than the evidence there, but legal either way.

Caveat for the SD "carts & LSVs <= 35" rule: CVC 21115/21716 limit plain golf carts (not LSVs) to roads posted 25 or less. At 30-35 these
stretches are LSV-only under state law; the app's SD rule treats <= 35 as OK for both.
