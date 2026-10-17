# Accuracy pass (2026-10-14, expansion-15)

Lessons applied from San Diego: untagged collectors defaulting to 25 (Grand Ave PB), wrong/old OSM maxspeed, changed limits, banned-highway crossings.
New sources: state DOT speed layers (FDOT Maximum Speed Limit TDA, TxDOT Speed Limits, SCDOT Speed Limits) used over OSM; FHWA 2022 NHS speed study (HPMS 2020) fills only untagged OSM roads (conflicts with tagged OSM listed for Street View, not applied). Mapillary re-pulled (30A now has signs). Gulf Shores 21-13 and Orange Beach 70-273 designated cart-street lists digitized; Orange Beach treated designated-only (state-tagged LSVs included by its ordinance).
Known % = share of road length with a speed from OSM tag, DOT/ordinance, Mapillary or designation (not assumed).

| region | known % before→after | segments newly blocked / newly OK | roads changed | unresolved untagged majors (count, km) | top unresolved |
|---|---|---|---|---|---|
| ptc | 56.1→56.4 | 11 / 0 | 9 | 57, 60.1 | McIntosh Trail, Fischer Road, Minix Road, Reese Road |
| hhi | 15.0→17.0 | 160 / 30 | 13 | 97, 89.1 | Marshland Road, Greenwood Drive, Laurel Oak Bay Road, Spanish Wells Road |
| myrtle | 17.1→17.9 | 112 / 81 | 41 | 196, 314.6 | Highway 65, Long Avenue Extension, Water Tower Road, Highway 472 |
| chs | 15.8→19.9 | 11 / 443 | 30 | 103, 74.9 | (unnamed unclassified), River Road, Sol Legare Road, Johnnie Dodds Boulevard |
| 30a | 16.7→20.3 | 20 / 1 | 5 | 31, 40.3 | Pine Log Road, County Highway 283, (unnamed unclassified), Mack Bayou Road |
| gulfshores | 40.2→59.7 | 699 / 0 | 92 | 18, 28.1 | Waterway East Boulevard, County Road 49, Bon Secour Highway, County Road 19 |
| portaransas | 21.3→26.5 | 37 / 7 | 9 | 27, 24.0 | Avenue A, (unnamed unclassified), Harbor Island Road, Arleigh Burke Road |
| suncity | 80.5→80.7 | 10 / 3 | 10 | 129, 159.8 | North Del Webb Boulevard, (unnamed unclassified), Beardsley Canal Service Road, West Pinnacle Peak Road |
| coachella | 21.3→21.3 | 0 / 0 | 0 | 153, 235.1 | Madison Street, Van Buren Street, Jackson Street, Calhoun Street |
| naples | 21.6→24.3 | 119 / 43 | 35 | 180, 220.0 | Vineyards Boulevard, Saint Andrews Boulevard, Pelican Bay Boulevard North, South Barfield Drive |
| goldenisles | 18.9→18.9 | 0 / 0 | 0 | 23, 34.9 | (unnamed unclassified), Lawrence Road, Ocean Road, Sidney Lanier Drive |
| tybee | 39.8→39.8 | 0 / 0 | 0 | 4, 0.8 | Crusoe Island Drive, Tybrisa Street, Taylor Street, Cedarwood Avenue |
| galveston | 25.9→27.7 | 26 / 21 | 19 | 94, 95.8 | Stewart Road, (unnamed unclassified), Seawolf Parkway, Ball Street - Avenue H |
| ocoast | 36.7→36.8 | 5 / 0 | 5 | 498, 242.2 | (unnamed unclassified), Nellie Gail Road, (unnamed tertiary), Marina Hills Drive |

## Street View check list
| region | road | lat,lon | what to check |
|---|---|---|---|
| ptc | McIntosh Trail | 33.34801,-84.59338 | untagged tertiary assumed 25 (9.19 km) – confirm posted limit |
| ptc | Fischer Road | 33.44507,-84.65637 | untagged tertiary assumed 25 (7.6 km) – confirm posted limit |
| ptc | Minix Road | 33.42222,-84.62491 | untagged tertiary assumed 25 (6.23 km) – confirm posted limit |
| hhi | Marshland Road | 32.19508,-80.74278 | untagged tertiary assumed 25 (7.39 km) – confirm posted limit |
| hhi | Greenwood Drive | 32.14948,-80.77845 | untagged tertiary assumed 25 (5.19 km) – confirm posted limit |
| hhi | Laurel Oak Bay Road | 32.19215,-80.91743 | untagged unclassified assumed 25 (4.48 km) – confirm posted limit |
| hhi | Commerce Place East | 32.2983,-80.93526 | OSM 25 vs FHWA(2020) 45 – which is posted? |
| myrtle | Highway 65 | 33.92813,-78.98613 | untagged tertiary assumed 25 (12.05 km) – confirm posted limit |
| myrtle | Long Avenue Extension | 33.92805,-79.02721 | untagged tertiary assumed 25 (9.91 km) – confirm posted limit |
| myrtle | Water Tower Road | 33.81395,-78.78447 | untagged tertiary assumed 25 (6.75 km) – confirm posted limit |
| myrtle | Seaboard Street | 33.70648,-78.91068 | OSM 30 vs FHWA(2020) 45 – which is posted? |
| myrtle | South Ocean Boulevard | 33.65911,-78.92706 | OSM 35 vs FHWA(2020) 45 – which is posted? |
| myrtle | River Oaks Drive | 33.75077,-78.86853 | OSM 35 vs FHWA(2020) 65 – which is posted? |
| chs | River Road | 32.68451,-80.02233 | untagged tertiary assumed 25 (6.42 km) – confirm posted limit |
| chs | Sol Legare Road | 32.67317,-79.99219 | untagged unclassified assumed 25 (4.18 km) – confirm posted limit |
| chs | Johnnie Dodds Boulevard | 32.80926,-79.87575 | untagged tertiary assumed 25 (3.1 km) – confirm posted limit |
| chs | James Island Expressway | 32.78153,-79.95178 | FIXED: OSM said 25; now blocked as expressway (SC 30) – quick confirm |
| chs | Folly Road | 32.67723,-79.95253 | OSM 40 vs FHWA(2020) 35 – which is posted? |
| chs | Ashley River Road | 32.80107,-80.01612 | OSM 40 vs FHWA(2020) 35 – which is posted? |
| 30a | Pine Log Road | 30.40354,-85.91545 | untagged tertiary assumed 25 (5.07 km) – confirm posted limit |
| 30a | County Highway 283 | 30.34777,-86.15954 | untagged tertiary assumed 25 (4.64 km) – confirm posted limit |
| 30a | Mack Bayou Road | 30.39953,-86.30818 | untagged tertiary assumed 25 (3.55 km) – confirm posted limit |
| 30a | East County Highway 30A | 30.27928,-86.00965 | OSM 30 vs FHWA(2020) 45 – which is posted? |
| gulfshores | Waterway East Boulevard | 30.28473,-87.65259 | untagged unclassified assumed 25 (5.19 km) – confirm posted limit |
| gulfshores | County Road 49 | 30.31924,-87.74238 | untagged tertiary assumed 25 (4.11 km) – confirm posted limit |
| gulfshores | Bon Secour Highway | 30.32659,-87.72553 | untagged tertiary assumed 25 (3.79 km) – confirm posted limit |
| portaransas | Avenue A | 27.88346,-97.18821 | untagged tertiary assumed 25 (3.24 km) – confirm posted limit |
| portaransas | Harbor Island Road | 27.86163,-97.07885 | untagged unclassified assumed 25 (2.14 km) – confirm posted limit |
| portaransas | Arleigh Burke Road | 27.82363,-97.2017 | untagged unclassified assumed 25 (1.62 km) – confirm posted limit |
| suncity | North Del Webb Boulevard | 33.64396,-112.28309 | untagged tertiary assumed 25 (8.02 km) – confirm posted limit |
| suncity | Beardsley Canal Service Road | 33.70392,-112.38293 | untagged unclassified assumed 25 (5.76 km) – confirm posted limit |
| suncity | West Pinnacle Peak Road | 33.69631,-112.25532 | untagged tertiary assumed 25 (5.46 km) – confirm posted limit |
| suncity | North Mountain Vista Boulevard | 33.63868,-112.39993 | OSM 25 vs FHWA(2020) 45 – which is posted? |
| suncity | North Reems Road | 33.65684,-112.37376 | OSM 35 vs FHWA(2020) 45 – which is posted? |
| suncity | North El Mirage Road | 33.63876,-112.3247 | OSM 35 vs FHWA(2020) 45 – which is posted? |
| coachella | Madison Street | 33.66332,-116.25022 | untagged tertiary assumed 25 (16.35 km) – confirm posted limit |
| coachella | Van Buren Street | 33.58743,-116.19843 | untagged tertiary assumed 25 (13.51 km) – confirm posted limit |
| coachella | Jackson Street | 33.59452,-116.21611 | untagged tertiary assumed 25 (9.76 km) – confirm posted limit |
| naples | Vineyards Boulevard | 26.23983,-81.73239 | untagged tertiary assumed 25 (9.12 km) – confirm posted limit |
| naples | Saint Andrews Boulevard | 26.09803,-81.72144 | untagged tertiary assumed 25 (6.98 km) – confirm posted limit |
| naples | Pelican Bay Boulevard North | 26.23774,-81.81217 | untagged tertiary assumed 25 (6.58 km) – confirm posted limit |
| naples | Goodlette-Frank Road North | 26.14211,-81.79087 | OSM 45 vs FHWA(2020) 35 – which is posted? |
| goldenisles | Lawrence Road | 31.23424,-81.35659 | untagged tertiary assumed 25 (4.77 km) – confirm posted limit |
| goldenisles | Ocean Road | 31.1798,-81.35531 | untagged tertiary assumed 25 (2.76 km) – confirm posted limit |
| goldenisles | Sidney Lanier Drive | 31.25143,-81.44798 | untagged unclassified assumed 25 (2.43 km) – confirm posted limit |
| tybee | Crusoe Island Drive | 32.01427,-80.87556 | untagged unclassified assumed 25 (0.26 km) – confirm posted limit |
| tybee | Tybrisa Street | 31.99242,-80.84926 | untagged tertiary assumed 25 (0.2 km) – confirm posted limit |
| tybee | Taylor Street | 32.02336,-80.84723 | untagged tertiary assumed 25 (0.17 km) – confirm posted limit |
| galveston | Stewart Road | 29.23783,-94.89404 | untagged tertiary assumed 25 (10.52 km) – confirm posted limit |
| galveston | Seawolf Parkway | 29.32784,-94.78325 | untagged tertiary assumed 25 (4.13 km) – confirm posted limit |
| galveston | Ball Street - Avenue H | 29.29443,-94.82121 | untagged tertiary assumed 25 (4.06 km) – confirm posted limit |
| ocoast | Nellie Gail Road | 33.56979,-117.69308 | untagged tertiary assumed 25 (4.84 km) – confirm posted limit |
| ocoast | Marina Hills Drive | 33.52121,-117.69466 | untagged tertiary assumed 25 (4.02 km) – confirm posted limit |
| ocoast | Chrisanta Drive | 33.59773,-117.6699 | untagged tertiary assumed 25 (2.96 km) – confirm posted limit |
| ocoast | Pacific Coast Highway | 33.54284,-117.78554 | OSM 30 vs FHWA(2020) 55 – which is posted? |
| ocoast | Ortega Highway | 33.50262,-117.658 | OSM 35 vs FHWA(2020) 50 – which is posted? |
| ocoast | Cristianitos Road | 33.39536,-117.59298 | OSM 25 vs FHWA(2020) 70 – which is posted? |
| portaransas | SH 361 at Avenue G | 27.823,-97.068 | confirm cart ban starts south of Ave G (cut is approximate) |
| tybee | Butler Ave at 14th St / Jones Ave / Campbell Ave | 31.995,-80.847 | allowed cart crossings of US 80 – not modeled; confirm signals |
| gulfshores | Orange Beach / Gulf Shores line in Gulf State Park | 30.255,-87.615 | designated-only zone boundary approximated at lon -87.615 |
| chs | Meeting St / King St downtown Charleston | 32.785,-79.935 | opened by SCDOT layer (<=35); downtown is outside the beach-town focus – confirm or trim bbox |

## Not done / gaps
- No GA (GDOT), AL (ALDOT), AZ (ADOT) or CA (Caltrans) current speed layer found; FHWA 2020 used only to fill untagged roads.
- County roads in Walton (CR 30A) not in FDOT TDA; Walton red/green LSV map is an image, not digitized.
- City speed-zone lists not found online for HHI, Myrtle Beach, Naples, St. Simons, Coachella cities; Palm Desert cart route map not digitized.
- Allowed crossing points (Tybee, Walton US 98 4-way only) not enforced in routing.
- Orange Beach list is OCR text from Ord. 2024-1487; amendment 2025-1521 not read.
