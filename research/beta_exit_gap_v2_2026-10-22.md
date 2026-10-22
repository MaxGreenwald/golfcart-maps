# Beta-exit gap v2, 2026-10-22 (analysis only; nothing live, no source codes changed)

Max: "12k stretches is way too high… signs don't change that often… small neighborhood roads are fine… count the real critical longer stretches." Plus: "is there a confidence level for OSM?" and "trust OSM for a segment if there are positive indicators."

## Method
- Same road set and sourced rule as v1: primary/secondary/tertiary + `_link`, trunk only when posted <=35. Residential/unclassified/service roads are excluded (neighborhood roads count as fine). Sourced = `v`, `m`, or `d` with a linked source.
- **Measured by miles, not segments.** v1 counted OSM node-to-node pieces, and a 2-mile arterial can be 40 pieces, so the segment count was inflated.
- **Neighbour inference (rule I):** a connected run of unsourced segments with the same name gets the posted speed when all of these hold: it is bounded by at least 2 sourced segments of that road; every boundary posts the same mph; the run and its boundaries share one highway class; nothing in or around the run is banned; and the run is at most 1.5 mi.
  - If the inferred speed would be more permissive than what the map shows today (for example, a >35 road turning <=35, which makes red green), it is **not credited**. It is counted as "flagged" and needs a photo.
  - Not detectable locally: city or jurisdiction lines and school zones. We have no boundary or school-zone layer in the extracts, so this is the main residual risk.
- **Critical corridors:** the unsourced segments left after inference, merged by name into connected runs and split wherever the current mph or class changes. Only corridors **>= 0.25 mi** count.
  - Why 0.25 mi: US speed zones are rarely posted shorter than about 0.2 to 0.25 mi. Pieces shorter than that are mostly turn lanes, links and intersection stubs that take the speed of their parent road.
  - Corridors are picked longest first until the region reaches 70% of important miles.
- **One check per corridor** means one posted-sign photo (Street View or Mapillary) per corridor, applied to the whole corridor. Divided roads show up as 2 corridors (one per carriageway), for example Vanderbilt Beach Rd, so the counts slightly overstate the work.

## OSM confidence: signals actually present
- Present: `source:maxspeed` (29,875 ways) and `maxspeed:type` (510). Values seen: `sign`, `survey;image`, `survey`, FDOT GIS 2011, implied `US:*` values, and "California vehicle code 22352".
- **Not present:** `version` and `timestamp`. Our Overpass extracts were pulled without metadata, so the "recent edit + many versions" rule can't be tested without re-pulling with `out meta`.
- No extract on the box for oob, kailua, poipu, wailea, kaanapali or waikoloa, so OSM trust adds nothing there.

### Measured agreement of OSM maxspeed with our real sources (v/m segments, ban sentinel 99 excluded)
| Tier / rule | Agree | n | % |
|---|---:|---:|---:|
| explicit+neighbour_agrees | 6,681 | 6,782 | 98.5% |
| explicit_nosource | 4,124 | 5,482 | 75.2% |
| explicit_nosource vs m | 3,009 | 3,778 | 79.6% |
| explicit+neighbour_disagrees | 33 | 2,329 | 1.4% |
| sign_survey | 1,302 | 2,190 | 59.5% |
| dot_gis | 1,553 | 1,773 | 87.6% |
| explicit_nosource vs v | 1,115 | 1,704 | 65.4% |
| sign_survey vs m | 1,102 | 1,290 | 85.4% |
| dot_gis vs m | 840 | 962 | 87.3% |
| sign_survey vs v | 200 | 900 | 22.2% |
| dot_gis vs v | 713 | 811 | 87.9% |
| implied | 11 | 11 | 100.0% |
| implied vs m | 11 | 11 | 100.0% |

Reading:
- The `vs v` rows are biased low. Manual `v` fixes were made exactly where OSM was known to be wrong (sign/survey vs v is 22%).
- `vs m` (Mapillary sign reads) is the fairer test. On that test:
  - sign/survey is 85.4% (n=1,290)
  - FDOT GIS is 87.3% (n=962)
  - explicit with no source is 79.6% (n=3,778)
- **None of the tag-based tiers reaches 95%.**
- The only candidate that clears the bar is **"explicit numeric OSM maxspeed (not implied/default) that equals the speed of an adjacent sourced segment of the same road": 98.5% (n=6,782)**. When the neighbour disagrees, OSM is right only 1.4% of the time (n=2,329).
- The implied rows (n=11) are too small to read, and those values are excluded by rule anyway.

**Proposed trusted-OSM rule (for Max's OK):** trust a segment's OSM maxspeed when it is an explicit number (not `US:*`, not a vehicle-code or default source, not a `maxspeed:type` zone), it equals the posted speed of an adjacent sourced segment of the same name, and the segment is not banned. sign/survey on its own is rejected (85%).
- Caveat: an adjacent sourced segment is often on the same OSM way, so this rule partly overlaps with inference. Its extra coverage is modest (see the table).

## Old vs new, all 37 regions (by important miles)
| Region | Important mi | v1 % mi sourced | + inference | + inference + trusted OSM (neighbour-agree rule) | Flagged inferences | Corridors >=0.25 mi to 70% (no OSM trust) | Mi | Corridors to 70% (with trusted OSM) | Mi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| oob | 30.7 | 97.3% | 97.3% | 97.3% (no extract) | 0 | 0 | 0.0 | 0 | 0.0 |
| annamaria | 15.3 | 97.0% | 97.3% | 97.9% | 0 | 0 | 0.0 | 0 | 0.0 |
| amelia | 51.7 | 92.3% | 93.0% | 93.3% | 0 | 0 | 0.0 | 0 | 0.0 |
| tybee | 8.7 | 88.5% | 88.5% | 88.9% | 0 | 0 | 0.0 | 0 | 0.0 |
| southpadre | 25.6 | 85.4% | 85.4% | 85.9% | 0 | 0 | 0.0 | 0 | 0.0 |
| staug | 131.0 | 85.1% | 85.1% | 85.3% | 0 | 0 | 0.0 | 0 | 0.0 |
| portaransas | 39.6 | 75.0% | 75.0% | 75.0% | 0 | 0 | 0.0 | 0 | 0.0 |
| kailua | 40.2 | 72.0% | 74.9% | 74.9% (no extract) | 0 | 0 | 0.0 | 0 | 0.0 |
| poipu | 18.4 | 68.9% | 72.4% | 72.4% (no extract) | 0 | 0 | 0.0 | 0 | 0.0 |
| gulfshores | 89.4 | 71.8% | 71.8% | 71.8% | 0 | 0 | 0.0 | 0 | 0.0 |
| chs | 57.1 | 70.4% | 71.4% | 71.4% | 9 | 0 | 0.0 | 0 | 0.0 |
| siesta | 300.0 | 71.2% | 71.4% | 72.6% | 0 | 0 | 0.0 | 0 | 0.0 |
| 30a | 55.1 | 70.4% | 71.0% | 71.8% | 0 | 0 | 0.0 | 0 | 0.0 |
| rockport | 56.3 | 70.5% | 70.5% | 70.5% | 1 | 0 | 0.0 | 0 | 0.0 |
| pcb | 74.3 | 65.4% | 65.8% | 67.5% | 0 | 2 | 3.9 | 1 | 2.1 |
| obx | 72.2 | 65.4% | 65.5% | 65.7% | 0 | 2 | 5.2 | 2 | 5.2 |
| lwr | 158.4 | 64.8% | 64.9% | 65.6% | 0 | 3 | 8.4 | 3 | 8.4 |
| galveston | 172.5 | 63.3% | 63.5% | 63.5% | 4 | 4 | 12.8 | 4 | 12.8 |
| wailea | 36.2 | 60.8% | 62.7% | 62.7% (no extract) | 1 | 1 | 5.0 | 1 | 5.0 |
| keywest | 34.9 | 62.4% | 62.7% | 64.5% | 2 | 3 | 3.2 | 2 | 2.2 |
| kaanapali | 23.9 | 58.6% | 59.4% | 59.4% (no extract) | 19 | 1 | 3.3 | 1 | 3.3 |
| suncitycenter | 57.0 | 56.6% | 56.6% | 56.6% | 0 | 3 | 8.4 | 3 | 8.4 |
| destin | 45.7 | 51.8% | 51.8% | 51.9% | 0 | 6 | 8.7 | 6 | 8.7 |
| naples | 465.9 | 48.8% | 48.8% | 49.4% | 0 | 30 | 99.6 | 29 | 97.1 |
| myrtle | 525.6 | 44.5% | 44.9% | 46.2% | 0 | 44 | 133.0 | 41 | 125.9 |
| goldenisles | 64.8 | 42.3% | 42.3% | 42.7% | 0 | 7 | 19.6 | 7 | 19.6 |
| waikoloa | 48.1 | 39.9% | 39.9% | 39.9% (no extract) | 0 | 2 | 15.4 | 2 | 15.4 |
| bhi | 44.4 | 38.3% | 38.3% | 39.4% | 0 | 5 | 14.9 | 5 | 14.9 |
| hhi | 95.7 | 37.2% | 37.2% | 37.2% | 0 | 9 | 32.8 | 9 | 32.8 |
| avalon | 6.2 | 36.2% | 36.2% | 36.3% | 1 | 2 | 2.6 | 2 | 2.6 |
| sd | 1,455.9 | 33.6% | 34.6% | 36.8% | 57 | 500 | 515.0 | 455 | 483.3 |
| ptc | 163.0 | 31.4% | 31.4% | 31.4% | 0 | 21 | 64.0 | 21 | 64.0 |
| suncity | 458.5 | 26.0% | 28.8% | 32.6% | 105 | 123 | 189.2 | 106 | 172.2 |
| ocoast | 704.9 | 25.5% | 28.1% | 33.0% | 95 | 346 | 295.9 | 285 | 261.1 |
| villages | 384.9 | 19.5% | 19.5% | 20.8% | 0 | 75 | 195.5 | 72 | 190.1 |
| coachella | 521.2 | 17.8% | 18.0% | 18.9% | 1 | 79 | 271.3 | 76 | 266.4 |
| putinbay | 7.9 | 0.0% | 0.0% | 0.0% | 0 | 4 | 5.6 | 4 | 5.6 |
| **All 37** | 6,541 | 41.2% | 42.0% | 43.7% | 295 | 1,272 | 1,913 | 1,137 | 1,807 |


sign/survey-only rule coverage (rejected): {'coachella': 26.3, 'myrtle': 46.6, 'naples': 49.3, 'ocoast': 48.7, 'sd': 56.0, 'suncity': 28.8, 'villages': 20.5}

Remaining gap miles by OSM tier (after inference):
coachella {'none': 204.3, 'explicit_nosource': 179.6, 'sign_survey': 43.5}
myrtle {'none': 183.7, 'explicit_nosource': 97.2, 'sign_survey': 8.8}
naples {'none': 150.2, 'explicit_nosource': 86.0, 'sign_survey': 2.1}
ocoast {'none': 188.2, 'explicit_nosource': 172.6, 'sign_survey': 145.8, 'implied': 0.6}
sd {'none': 513.3, 'sign_survey': 311.2, 'explicit_nosource': 126.9, 'implied': 0.1}
suncity {'explicit_nosource': 223.9, 'none': 102.4}
villages {'explicit_nosource': 152.5, 'none': 133.1, 'dot_gis': 20.4, 'sign_survey': 3.7}

sd top corridors (none): Mission Avenue 3.98 mi @unknown [none]; North River Road 3.45 mi @unknown [none]; Rancho del Oro Drive 3.43 mi @35 [sign_survey]; Carlsbad Village Drive 3.37 mi @40 [sign_survey]; Faraday Avenue 3.23 mi @unknown [none]; Avenida de la Plata 3.00 mi @25 [none]; College Boulevard 2.96 mi @45 [sign_survey]; Batiquitos Drive 2.89 mi @40 [sign_survey]; Poinsettia Lane 2.73 mi @unknown [none]; College Boulevard 2.72 mi @35 [sign_survey]

sd top corridors (nbr): Mission Avenue 3.98 mi @unknown [none]; North River Road 3.45 mi @unknown [none]; Rancho del Oro Drive 3.43 mi @35 [sign_survey]; Carlsbad Village Drive 3.37 mi @40 [sign_survey]; Faraday Avenue 3.23 mi @unknown [none]; Avenida de la Plata 3.00 mi @25 [none]; College Boulevard 2.95 mi @45 [sign_survey]; Batiquitos Drive 2.89 mi @40 [sign_survey]; Poinsettia Lane 2.73 mi @unknown [none]; College Boulevard 2.72 mi @35 [sign_survey]

ocoast top corridors (none): Marguerite Parkway 3.46 mi @45 [sign_survey]; Rancho Viejo Road 3.02 mi @45 [sign_survey]; Nellie Gail Road 3.01 mi @25 [none]; Alicia Parkway 2.99 mi @50 [sign_survey]; Melinda Road 2.97 mi @45 [explicit_nosource]; Antonio Parkway 2.48 mi @55 [explicit_nosource]; Paseo de la Colinas 2.43 mi @unknown [none]; Alicia Parkway 2.30 mi @50 [sign_survey]; Antonio Parkway 2.26 mi @55 [sign_survey]; San Juan Creek Road 2.12 mi @40 [explicit_nosource]

ocoast top corridors (nbr): Marguerite Parkway 3.36 mi @45 [sign_survey]; Rancho Viejo Road 3.02 mi @45 [sign_survey]; Nellie Gail Road 3.01 mi @25 [none]; Melinda Road 2.97 mi @45 [explicit_nosource]; Alicia Parkway 2.93 mi @50 [sign_survey]; Antonio Parkway 2.48 mi @55 [explicit_nosource]; Paseo de la Colinas 2.43 mi @unknown [none]; Alicia Parkway 2.30 mi @50 [sign_survey]; Antonio Parkway 2.24 mi @55 [sign_survey]; San Juan Creek Road 2.12 mi @40 [explicit_nosource]

suncity top corridors (none): North Dysart Road 6.88 mi @45 [explicit_nosource]; West Happy Valley Road 5.87 mi @45 [explicit_nosource]; North Litchfield Road 5.55 mi @45 [explicit_nosource]; North 99th Avenue 5.10 mi @40 [explicit_nosource]; North Bullard Avenue 4.53 mi @35 [explicit_nosource]; West Mountain View Boulevard 3.92 mi @35 [explicit_nosource]; North 83rd Avenue 3.75 mi @unknown [none]; North 99th Avenue 3.58 mi @40 [explicit_nosource]; North Reems Road 3.35 mi @45 [explicit_nosource]; North Boswell Boulevard 3.25 mi @25 [none]

suncity top corridors (nbr): North Dysart Road 6.88 mi @45 [explicit_nosource]; West Happy Valley Road 5.76 mi @45 [explicit_nosource]; North Litchfield Road 5.55 mi @45 [explicit_nosource]; North 99th Avenue 5.08 mi @40 [explicit_nosource]; North Bullard Avenue 4.49 mi @35 [explicit_nosource]; West Mountain View Boulevard 3.84 mi @35 [explicit_nosource]; North 83rd Avenue 3.75 mi @unknown [none]; North 99th Avenue 3.54 mi @40 [explicit_nosource]; North Boswell Boulevard 3.25 mi @25 [none]; North Reems Road 3.20 mi @45 [explicit_nosource]

coachella top corridors (none): Fred Waring Drive 18.46 mi @unknown [none]; Dillon Road 13.73 mi @unknown [none]; Madison Street 9.16 mi @25 [none]; Avenue 52 7.29 mi @unknown [none]; Monroe Street 7.10 mi @unknown [none]; Van Buren Street 6.98 mi @25 [none]; Avenue 50 6.29 mi @50 [explicit_nosource]; Frank Sinatra Drive 6.14 mi @50 [explicit_nosource]; Avenue 42 6.03 mi @unknown [none]; Jackson Street 6.00 mi @25 [none]

coachella top corridors (nbr): Fred Waring Drive 18.46 mi @unknown [none]; Dillon Road 13.73 mi @unknown [none]; Madison Street 9.16 mi @25 [none]; Avenue 52 7.29 mi @unknown [none]; Monroe Street 7.10 mi @unknown [none]; Van Buren Street 6.98 mi @25 [none]; Avenue 50 6.29 mi @50 [explicit_nosource]; Frank Sinatra Drive 6.14 mi @50 [explicit_nosource]; Avenue 42 6.03 mi @unknown [none]; Jackson Street 6.00 mi @25 [none]

villages top corridors (none): Buena Vista Boulevard 7.22 mi @35 [none]; Southeast 36th Avenue 6.53 mi @25 [none]; Buena Vista Boulevard 6.45 mi @35 [explicit_nosource]; El Camino Real 5.95 mi @35 [explicit_nosource]; Morse Boulevard 5.80 mi @35 [none]; County Road 466 5.31 mi @45 [explicit_nosource]; County Road 466 4.68 mi @45 [explicit_nosource]; CR 462 4.36 mi @25 [none]; Buena Vista Boulevard 4.05 mi @35 [none]; Marsh Bend Trail 3.87 mi @30 [explicit_nosource]

villages top corridors (nbr): Buena Vista Boulevard 7.22 mi @35 [none]; Southeast 36th Avenue 6.53 mi @25 [none]; Buena Vista Boulevard 6.45 mi @35 [explicit_nosource]; El Camino Real 5.95 mi @35 [explicit_nosource]; Morse Boulevard 5.80 mi @35 [none]; County Road 466 5.31 mi @45 [explicit_nosource]; County Road 466 4.68 mi @45 [explicit_nosource]; CR 462 4.36 mi @25 [none]; Buena Vista Boulevard 4.05 mi @35 [none]; Marsh Bend Trail 3.87 mi @30 [explicit_nosource]

myrtle top corridors (none): Highway 65 7.49 mi @25 [none]; Old Reaves Ferry Road 7.17 mi @45 [explicit_nosource]; Red Bluff Road 6.46 mi @unknown [none]; Long Avenue Extension 6.16 mi @25 [none]; Water Tower Road 4.20 mi @25 [none]; Highway 472 3.98 mi @25 [none]; Cates Bay Highway 3.94 mi @25 [none]; Highway 19 3.56 mi @55 [explicit_nosource]; Gardner Lacy Road 3.48 mi @25 [none]; International Drive 3.46 mi @45 [explicit_nosource]

myrtle top corridors (nbr): Highway 65 7.49 mi @25 [none]; Old Reaves Ferry Road 7.17 mi @45 [explicit_nosource]; Red Bluff Road 6.46 mi @unknown [none]; Long Avenue Extension 6.16 mi @25 [none]; Water Tower Road 4.20 mi @25 [none]; Highway 472 3.98 mi @25 [none]; Cates Bay Highway 3.94 mi @25 [none]; Highway 19 3.56 mi @55 [explicit_nosource]; Gardner Lacy Road 3.48 mi @25 [none]; McDowell Shortcut Road 3.34 mi @25 [none]

naples top corridors (none): Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Santa Barbara Boulevard 6.47 mi @unknown [none]; Livingston Road 4.81 mi @45 [explicit_nosource]; Goodlette-Frank Road North 4.28 mi @45 [explicit_nosource]; Livingston Road 4.23 mi @unknown [none]; Pelican Bay Boulevard North 4.09 mi @25 [none]; Immokalee Road 3.97 mi @45 [explicit_nosource]; Airport-Pulling Road 3.91 mi @45 [explicit_nosource]; South Barfield Drive 3.75 mi @25 [none]

naples top corridors (nbr): Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Santa Barbara Boulevard 6.47 mi @unknown [none]; Livingston Road 4.81 mi @45 [explicit_nosource]; Livingston Road 4.23 mi @unknown [none]; Pelican Bay Boulevard North 4.09 mi @25 [none]; Goodlette-Frank Road North 4.01 mi @45 [explicit_nosource]; Immokalee Road 3.97 mi @45 [explicit_nosource]; Airport-Pulling Road 3.88 mi @45 [explicit_nosource]; South Barfield Drive 3.75 mi @25 [none]

Columns:
- "Corridors to 70%" = the fewest corridors of at least 0.25 mi, longest first, that lift the region to 70% of important miles.
- "Flagged" = inferences withheld because they would make a road more permissive.
- v1 (segments) said San Diego needs 12,357 segments. v2 says **500 corridors / 515 mi**, or **455 / 483 mi** with trusted OSM.

## Big regions: remaining gap by OSM tier (miles, after inference)
coachella {'none': 204.3, 'explicit_nosource': 179.6, 'sign_survey': 43.5}
myrtle {'none': 183.7, 'explicit_nosource': 97.2, 'sign_survey': 8.8}
naples {'none': 150.2, 'explicit_nosource': 86.0, 'sign_survey': 2.1}
ocoast {'none': 188.2, 'explicit_nosource': 172.6, 'sign_survey': 145.8, 'implied': 0.6}
sd {'none': 513.3, 'sign_survey': 311.2, 'explicit_nosource': 126.9, 'implied': 0.1}
suncity {'explicit_nosource': 223.9, 'none': 102.4}
villages {'explicit_nosource': 152.5, 'none': 133.1, 'dot_gis': 20.4, 'sign_survey': 3.7}


## Big regions: top corridors (longest first; speed shown is today's map value, 'unknown' = no speed; [dominant OSM tier])
- sd top corridors (none): Mission Avenue 3.98 mi @unknown [none]; North River Road 3.45 mi @unknown [none]; Rancho del Oro Drive 3.43 mi @35 [sign_survey]; Carlsbad Village Drive 3.37 mi @40 [sign_survey]; Faraday Avenue 3.23 mi @unknown [none]; Avenida de la Plata 3.00 mi @25 [none]; College Boulevard 2.96 mi @45 [sign_survey]; Batiquitos Drive 2.89 mi @40 [sign_survey]; Poinsettia Lane 2.73 mi @unknown [none]; College Boulevard 2.72 mi @35 [sign_survey]
- ocoast top corridors (none): Marguerite Parkway 3.46 mi @45 [sign_survey]; Rancho Viejo Road 3.02 mi @45 [sign_survey]; Nellie Gail Road 3.01 mi @25 [none]; Alicia Parkway 2.99 mi @50 [sign_survey]; Melinda Road 2.97 mi @45 [explicit_nosource]; Antonio Parkway 2.48 mi @55 [explicit_nosource]; Paseo de la Colinas 2.43 mi @unknown [none]; Alicia Parkway 2.30 mi @50 [sign_survey]; Antonio Parkway 2.26 mi @55 [sign_survey]; San Juan Creek Road 2.12 mi @40 [explicit_nosource]
- suncity top corridors (none): North Dysart Road 6.88 mi @45 [explicit_nosource]; West Happy Valley Road 5.87 mi @45 [explicit_nosource]; North Litchfield Road 5.55 mi @45 [explicit_nosource]; North 99th Avenue 5.10 mi @40 [explicit_nosource]; North Bullard Avenue 4.53 mi @35 [explicit_nosource]; West Mountain View Boulevard 3.92 mi @35 [explicit_nosource]; North 83rd Avenue 3.75 mi @unknown [none]; North 99th Avenue 3.58 mi @40 [explicit_nosource]; North Reems Road 3.35 mi @45 [explicit_nosource]; North Boswell Boulevard 3.25 mi @25 [none]
- coachella top corridors (none): Fred Waring Drive 18.46 mi @unknown [none]; Dillon Road 13.73 mi @unknown [none]; Madison Street 9.16 mi @25 [none]; Avenue 52 7.29 mi @unknown [none]; Monroe Street 7.10 mi @unknown [none]; Van Buren Street 6.98 mi @25 [none]; Avenue 50 6.29 mi @50 [explicit_nosource]; Frank Sinatra Drive 6.14 mi @50 [explicit_nosource]; Avenue 42 6.03 mi @unknown [none]; Jackson Street 6.00 mi @25 [none]
- villages top corridors (none): Buena Vista Boulevard 7.22 mi @35 [none]; Southeast 36th Avenue 6.53 mi @25 [none]; Buena Vista Boulevard 6.45 mi @35 [explicit_nosource]; El Camino Real 5.95 mi @35 [explicit_nosource]; Morse Boulevard 5.80 mi @35 [none]; County Road 466 5.31 mi @45 [explicit_nosource]; County Road 466 4.68 mi @45 [explicit_nosource]; CR 462 4.36 mi @25 [none]; Buena Vista Boulevard 4.05 mi @35 [none]; Marsh Bend Trail 3.87 mi @30 [explicit_nosource]
- myrtle top corridors (none): Highway 65 7.49 mi @25 [none]; Old Reaves Ferry Road 7.17 mi @45 [explicit_nosource]; Red Bluff Road 6.46 mi @unknown [none]; Long Avenue Extension 6.16 mi @25 [none]; Water Tower Road 4.20 mi @25 [none]; Highway 472 3.98 mi @25 [none]; Cates Bay Highway 3.94 mi @25 [none]; Highway 19 3.56 mi @55 [explicit_nosource]; Gardner Lacy Road 3.48 mi @25 [none]; International Drive 3.46 mi @45 [explicit_nosource]
- naples top corridors (none): Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Vanderbilt Beach Road 7.18 mi @45 [explicit_nosource]; Santa Barbara Boulevard 6.47 mi @unknown [none]; Livingston Road 4.81 mi @45 [explicit_nosource]; Goodlette-Frank Road North 4.28 mi @45 [explicit_nosource]; Livingston Road 4.23 mi @unknown [none]; Pelican Bay Boulevard North 4.09 mi @25 [none]; Immokalee Road 3.97 mi @45 [explicit_nosource]; Airport-Pulling Road 3.91 mi @45 [explicit_nosource]; South Barfield Drive 3.75 mi @25 [none]

## Effort estimate
- One sign photo per corridor, using Reginald's Street View workflow at about 2 to 3 minutes per check:
  - San Diego: about 500 checks, roughly 17 to 25 h, about 5 batches of 100
  - Orange County coast: about 346 checks
  - Coachella: 79
  - Sun City: 123
  - The Villages: 75
  - Myrtle Beach: 44
  - Naples: 30
  - **All 37: about 1,272 checks (about 1,137 with trusted OSM), roughly 45 to 65 h total**, versus about 59 batches of 1,000 segments in v1.
- Faster still for the long `unknown` corridors (Coachella's Fred Waring 18 mi, Dillon 14 mi): use county or city GIS speed layers.

## Risks and guardrails
1. Inferred or trusted speeds must **never lift a ban** or turn a red road green silently. Both are withheld and flagged here (295 flagged across regions).
2. Jurisdiction lines and school zones can't be detected in our data. Inferred runs that cross a city line could be wrong. Keep the 1.5 mi cap, and add a boundary layer before shipping.
3. If shipped, show the new kinds as **distinct source codes**: proposed `f` = inferred from neighbours, `o` = trusted OSM. The popup should say "inferred from posted signs nearby" or "OpenStreetMap (matches nearby sign)", never "verified". Ship behind tests (no ban lift, no red-to-green), on its own branch and preview.
4. San Diego is excluded from the beta bar (Max: "keep San Diego live tho no beta"). Its numbers are shown for information only.

Reproduce: `python3 research/beta_exit_gap_v2.py /workspace/gcm-sv2apply` (needs a built `public/data` and `cache/*_osm.json`). The raw output is in `beta_exit_gap_v2_2026-10-22.json`.

## Final official measure (Max, 2026-10-22, all rules built in)

A region leaves beta only when BOTH hold (San Diego is exempt and is never beta):
1. **>= 70% of important-road miles are backed by a real source** (`v`, `m`, `d` with a source, and `o` trusted OSM once that branch ships). **Banned stretches are scored separately** and are not in the 70% (rule 3).
2. **A local access source is recorded** in `research/access_sources.json` (a sheriff/county LSV map or an ordinance road list; state-highway-only bans don't count) (rule 2).

The check list (`research/beta_check_list.json`, per region) puts work in this order:
- shop/user reports from `research/road_reports.json`, each with a scan for similar roads (rule 5)
- conflicts: a corridor posted differently by a real source right next to it, or a sourced piece that still draws red between <=35 pieces of the same road (rule 1)
- then the remaining corridors of 0.25 mi or more, longest first

Resort/town-centre grids (`research/beta_grids.json`) pull neighbourhood streets into the measure when an access source exists (rule 4). 30A has 4 grids: Seaside, Alys Beach, Seacrest and Rosemary Beach (from the Sheriff LSV-map bans). Assumed-speed county roads (`i` code on CR/County Road names) are counted per region so they can be checked against the access source.

Fix vs the first v2 draft: that draft read the one-way field as the ban flag. Bans are now read from the real flag (and `v` 99). This changes the inference safety checks and the flagged counts, not the sourced miles.

| Region | % important mi sourced (bans excluded) | Access source | Passes | Missing | Corridors to 70% (mi) | Conflicts to check | Ban mi (sourced) | Grid mi | Assumed county-road mi |
|---|---:|---|---|---|---:|---:|---:|---:|---:|
| oob | 97.3% | **no** | no | no local access source recorded | 0 (0) | 0 | 0 (0) | 0 | 0 |
| annamaria | 97.0% | **no** | no | no local access source recorded | 0 (0) | 1 | 0 (0) | 0 | 0 |
| amelia | 92.3% | **no** | no | no local access source recorded | 0 (0) | 6 | 0 (0) | 0 | 0 |
| southpadre | 85.3% | **no** | no | no local access source recorded | 0 (0) | 0 | 0.2 (0.2) | 0 | 0 |
| staug | 78.3% | **no** | no | no local access source recorded | 0 (0) | 4 | 41.1 (41.1) | 0 | 1.3 |
| kailua | 72.0% | **no** | no | no local access source recorded | 0 (0) | 5 | 0 (0) | 0 | 0 |
| tybee | 70.4% | **no** | no | no local access source recorded | 0 (0) | 1 | 5.4 (5.4) | 0 | 0 |
| poipu | 68.9% | **no** | no | miles 68.9% < 70%; no local access source recorded | 0 (0) | 4 | 0 (0) | 0 | 0 |
| siesta | 68.2% | **no** | no | miles 68.2% < 70%; no local access source recorded | 0 (0) | 68 | 28.7 (28.7) | 0 | 0 |
| obx | 65.4% | **no** | no | miles 65.4% < 70%; no local access source recorded | 2 (5.2) | 8 | 0 (0) | 0 | 0 |
| pcb | 65.4% | **no** | no | miles 65.4% < 70%; no local access source recorded | 0 (0) | 13 | 0 (0) | 0 | 0 |
| portaransas | 64.2% | **no** | no | miles 64.2% < 70%; no local access source recorded | 1 (2.0) | 5 | 11.9 (11.9) | 0 | 0 |
| chs | 62.8% | **no** | no | miles 62.8% < 70%; no local access source recorded | 2 (3.2) | 9 | 11.6 (11.6) | 0 | 0 |
| keywest | 62.4% | **no** | no | miles 62.4% < 70%; no local access source recorded | 3 (3.2) | 12 | 0 (0) | 0 | 0 |
| wailea | 60.8% | **no** | no | miles 60.8% < 70%; no local access source recorded | 1 (5.0) | 8 | 0 (0) | 0 | 0 |
| lwr | 60.7% | **no** | no | miles 60.7% < 70%; no local access source recorded | 3 (8.4) | 25 | 16.5 (16.5) | 0 | 0 |
| kaanapali | 58.6% | **no** | no | miles 58.6% < 70%; no local access source recorded | 1 (3.3) | 8 | 0 (0) | 0 | 0 |
| rockport | 56.7% | **no** | no | miles 56.7% < 70%; no local access source recorded | 1 (5.8) | 8 | 17.9 (17.9) | 0 | 0 |
| destin | 51.8% | **no** | no | miles 51.8% < 70%; no local access source recorded | 6 (8.7) | 2 | 0 (0) | 0 | 0 |
| 30a | 45.2% | yes | no | miles 45.2% < 70% | 16 (16.5) | 4 | 19.5 (19.5) | 33.5 | 4.4 |
| waikoloa | 39.9% | **no** | no | miles 39.9% < 70%; no local access source recorded | 2 (15.4) | 1 | 0 (0) | 0 | 0 |
| galveston | 39.8% | yes | no | miles 39.8% < 70% | 17 (30.7) | 23 | 67.3 (67.3) | 0 | 0 |
| naples | 39.7% | **no** | no | miles 39.7% < 70%; no local access source recorded | 38 (114.8) | 40 | 70.2 (70.2) | 0 | 0 |
| bhi | 38.3% | **no** | no | miles 38.3% < 70%; no local access source recorded | 5 (14.9) | 1 | 0 (0) | 0 | 0 |
| avalon | 36.2% | **no** | no | miles 36.2% < 70%; no local access source recorded | 2 (2.6) | 0 | 0 (0) | 0 | 0 |
| sd (exempt) | 33.6% | **no** | no | miles 33.6% < 70%; no local access source recorded | 419 (464.5) | 428 | 0 (0) | 0 | 0.1 |
| myrtle | 33.4% | **no** | no | miles 33.4% < 70%; no local access source recorded | 56 (152.3) | 54 | 87.3 (87.3) | 0 | 0 |
| suncitycenter | 33.3% | **no** | no | miles 33.3% < 70%; no local access source recorded | 6 (13.1) | 10 | 19.9 (19.9) | 0 | 0 |
| hhi | 30.0% | **no** | no | miles 30.0% < 70%; no local access source recorded | 10 (35.1) | 11 | 9.9 (9.9) | 0 | 0 |
| suncity | 26.0% | **no** | no | miles 26.0% < 70%; no local access source recorded | 81 (150.5) | 105 | 0 (0) | 0 | 0 |
| ocoast | 24.2% | **no** | no | miles 24.2% < 70%; no local access source recorded | 256 (246.6) | 286 | 12.2 (12.2) | 0 | 0 |
| goldenisles | 16.1% | **no** | no | miles 16.1% < 70%; no local access source recorded | 11 (24.8) | 4 | 20.3 (20.3) | 0 | 0 |
| villages | 7.2% | yes | no | miles 7.2% < 70% | 46 (89.3) | 1 | 242.9 (64.9) | 0 | 32.3 |
| gulfshores | 5.7% | yes | no | miles 5.7% < 70% | 8 (18.6) | 0 | 62.6 (62.6) | 0 | 4.6 |
| coachella | 5.6% | **no** | no | miles 5.6% < 70%; no local access source recorded | 92 (288.7) | 19 | 67.2 (67.2) | 0 | 0 |
| ptc | 5.0% | yes | no | miles 5.0% < 70% | 12 (33.5) | 0 | 112.6 (48.6) | 0 | 0 |
| putinbay | 0.0% | **no** | no | miles 0.0% < 70%; no local access source recorded | 4 (5.6) | 0 | 0 (0) | 0 | 0 |

**Passing now: 0 of 37** (none). Regions that clear 70% by miles but have no access source: amelia, annamaria, kailua, oob, southpadre, staug, tybee.
Regions with an access source: 30a, galveston, gulfshores, ptc, villages. Candidate leads are in `access_sources.json` under `candidates`.
Reports recorded: 0 (none yet; add them to `road_reports.json`).

Apply to the app: `python3 research/beta_exit_gap_v2.py && python3 scripts/apply_beta_bar.py && python3 scripts/gen_llms.py`. `tests/test_beta_bar.py` guards that the flags match this table.


## v3 relaxed bar (ANALYSIS ONLY, not applied, not merged), 2026-10-22

Rules: >=70% of important-road miles sourced, cited bans counted as sourced; >=50% of non-ban miles sourced; access check pass/fail = local-rules search recorded in access_sources.json (local source, or "state law, no local ordinance found" + what was searched); grids and reports stay on the check list only; SD exempt. Cells are no-o / with-o.

| region | % miles (bans in) | % non-ban | access | pass (no o) | pass (with o) | fail reason |
|---|---|---|---|---|---|---|
| oob | 97.3 / 97.3 | 97.3 / 97.3 | yes | PASS | PASS |  |
| annamaria | 97.0 / 97.9 | 97.0 / 97.9 | yes | PASS | PASS |  |
| amelia | 92.3 / 92.9 | 92.3 / 92.9 | yes | PASS | PASS |  |
| tybee | 88.5 / 88.9 | 70.4 / 71.2 | yes | PASS | PASS |  |
| southpadre | 85.4 / 85.9 | 85.3 / 85.8 | yes | PASS | PASS |  |
| staug | 85.1 / 85.3 | 78.3 / 78.6 | yes | PASS | PASS |  |
| portaransas | 75.0 / 75.0 | 64.2 / 64.2 | yes | PASS | PASS |  |
| kailua | 72.0 / 72.0 | 72.0 / 72.0 | yes | PASS | PASS |  |
| gulfshores | 71.8 / 71.8 | 5.7 / 5.7 | yes | fail | fail | non-ban 5.7% < 50% floor |
| siesta | 71.2 / 72.6 | 68.2 / 69.7 | yes | PASS | PASS |  |
| rockport | 70.5 / 70.5 | 56.7 / 56.7 | yes | PASS | PASS |  |
| 30a | 70.4 / 71.5 | 65.6 / 66.9 | yes | PASS | PASS |  |
| chs | 70.4 / 70.4 | 62.8 / 62.8 | yes | PASS | PASS |  |
| poipu | 68.9 / 68.9 | 68.9 / 68.9 | no | fail | fail | 68.9% < 70% (bans in); no local-rules search recorded |
| obx | 65.4 / 65.7 | 65.4 / 65.7 | no | fail | fail | 65.4% < 70% (bans in); no local-rules search recorded |
| pcb | 65.4 / 67.5 | 65.4 / 67.5 | no | fail | fail | 65.4% < 70% (bans in); no local-rules search recorded |
| lwr | 64.8 / 65.6 | 60.7 / 61.6 | no | fail | fail | 64.8% < 70% (bans in); no local-rules search recorded |
| galveston | 63.3 / 63.3 | 39.8 / 39.8 | yes | fail | fail | 63.3% < 70% (bans in); non-ban 39.8% < 50% floor |
| keywest | 62.4 / 64.2 | 62.4 / 64.2 | no | fail | fail | 62.4% < 70% (bans in); no local-rules search recorded |
| wailea | 60.8 / 60.8 | 60.8 / 60.8 | no | fail | fail | 60.8% < 70% (bans in); no local-rules search recorded |
| kaanapali | 58.6 / 58.6 | 58.6 / 58.6 | no | fail | fail | 58.6% < 70% (bans in); no local-rules search recorded |
| suncitycenter | 56.6 / 56.6 | 33.3 / 33.3 | no | fail | fail | 56.6% < 70% (bans in); non-ban 33.3% < 50% floor; no local-rules search recorded |
| destin | 51.8 / 51.9 | 51.8 / 51.9 | no | fail | fail | 51.8% < 70% (bans in); no local-rules search recorded |
| naples | 48.8 / 49.4 | 39.7 / 40.4 | no | fail | fail | 48.8% < 70% (bans in); non-ban 39.7% < 50% floor; no local-rules search recorded |
| myrtle | 44.5 / 46.0 | 33.4 / 35.2 | no | fail | fail | 44.5% < 70% (bans in); non-ban 33.4% < 50% floor; no local-rules search recorded |
| goldenisles | 42.3 / 42.7 | 16.1 / 16.7 | no | fail | fail | 42.3% < 70% (bans in); non-ban 16.1% < 50% floor; no local-rules search recorded |
| waikoloa | 39.9 / 39.9 | 39.9 / 39.9 | no | fail | fail | 39.9% < 70% (bans in); non-ban 39.9% < 50% floor; no local-rules search recorded |
| bhi | 38.3 / 39.4 | 38.3 / 39.4 | no | fail | fail | 38.3% < 70% (bans in); non-ban 38.3% < 50% floor; no local-rules search recorded |
| hhi | 37.2 / 37.2 | 30.0 / 30.0 | no | fail | fail | 37.2% < 70% (bans in); non-ban 30.0% < 50% floor; no local-rules search recorded |
| avalon | 36.2 / 36.3 | 36.2 / 36.3 | no | fail | fail | 36.2% < 70% (bans in); non-ban 36.2% < 50% floor; no local-rules search recorded |
| sd | 33.6 / 36.0 | 33.6 / 36.0 | no | PASS | PASS | SD exempt |
| ptc | 31.4 / 31.4 | 5.0 / 5.0 | yes | fail | fail | 31.4% < 70% (bans in); non-ban 5.0% < 50% floor |
| suncity | 26.0 / 30.6 | 26.0 / 30.6 | no | fail | fail | 26.0% < 70% (bans in); non-ban 26.0% < 50% floor; no local-rules search recorded |
| ocoast | 25.5 / 31.4 | 24.2 / 30.2 | no | fail | fail | 25.5% < 70% (bans in); non-ban 24.2% < 50% floor; no local-rules search recorded |
| villages | 20.1 / 20.1 | 7.2 / 7.2 | yes | fail | fail | 20.1% < 70% (bans in); non-ban 7.2% < 50% floor |
| coachella | 17.8 / 18.8 | 5.6 / 6.7 | no | fail | fail | 17.8% < 70% (bans in); non-ban 5.6% < 50% floor; no local-rules search recorded |
| putinbay | 0.0 / 0.0 | 0.0 / 0.0 | no | fail | fail | 0.0% < 70% (bans in); non-ban 0.0% < 50% floor; no local-rules search recorded |

Passing (excl. SD exempt): without o 12, with o 12
