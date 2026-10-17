# Expansion-15 build (2026-10-14, branch expansion-15, all regions hidden beta; ?r=<id> to load)
Single rule: posted <=35 OK, 40+ blocked, untagged major roads blocked, listed state highways/ordinance bans blocked (build_region.py `bans`).
Coverage = share of drivable OSM road ways with maxspeed (length-weighted in parens); major = primary..tertiary.
Unknown residential = assumed 25. Stats: research/expansion15_stats.json. Sources per region: research/regions/<id>.json.
| id | coverage ways (len) | major | confidence | key gaps |
|---|---|---|---|---|
| ptc | 34.0 (52.7) | 68.7 | med | city cart-street list not digitized; path tags from OSM |
| hhi | 3.6 (7.0) | 9.2 | low | almost no speed data; SC 4-mi/daylight not enforced |
| myrtle | 9.6 (15.2) | 65.9 | med | Kings Hwy/US 17/501 banned (city); residential assumed |
| chs | 8.4 (12.6) | 38.6 | low-med | IOP Connector banned; Folly/Sullivan's town rules not modeled |
| 30a | 6.0 (14.4) | 60.9 | med | US 98 banned (WCSO); Mapillary failed; Walton red-road map not digitized; private communities |
| gulfshores | 23.7 (39.6) | 83.8 | low-med | region cap 25 mph (Max 2026-10-14; Gulf Shores 21-13, Orange Beach 70-273); designated-street list not digitized |
| portaransas | 14.7 (20.0) | 56.7 | med | SH 361 ban south of Ave G approx lat 27.823; beach-as-street not modeled |
| suncity | 71.1 (77.9) | 73.4 | high-med | best coverage; HOA paths partial |
| coachella | 12.4 (16.3) | 58.4 | low-med | Palm Desert cart route map not digitized |
| naples | 6.8 (12.8) | 43.2 | low | Naples/Marco designations not digitized |
| goldenisles | 5.9 (9.3) | 40.7 | low | Jekyll/Glynn rules not digitized |
| tybee | 6.1 (17.9) | 66.7 | med | Butler Ave/US 80 banned; crossing points not modeled |
| galveston | 3.5 (6.5) | 2.6 | med | ordinance bans strong (Seawall, Broadway, Ave O/P approx bbox); speed data weak |
| ocoast | 26.3 (28.2) | 67.6 | med | Laguna Woods internal rules not modeled |
