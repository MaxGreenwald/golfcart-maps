# Red islands (Oct 18 2026)

Max flagged a short red stretch of **Soledad Mountain Rd** (La Jolla, by Soledad Rancho Ct, about 32.8156,-117.2358 to 32.8178,-117.2363)
between green on both sides: "reds like this are unlikely. how do we fix this and do better next time."

## Root cause (Soledad)
Soledad Mountain Rd is a divided road there. An OpenStreetMap mapper drew the southbound carriageway as a separate way on
Mar 28 2026 (way [1493577203](https://www.openstreetmap.org/way/1493577203), `highway=secondary`, `oneway=yes`) **without a name
and without maxspeed**. Every speed source we have is matched by street name (the Mapillary corridor rule that gives Soledad
Mountain Rd its 35, the city lists, the short-stub rule), so the unnamed piece got none of them and fell to the default for an
untagged `secondary`: "no limit, assume 40+" = red. The posted limit is 35: Mapillary has a 35 mph sign photographed right at
the south end of this piece (32.81549,-117.23563, [feature 1267538231008834](https://www.mapillary.com/app/?lat=32.81549&lng=-117.23563&z=19&focus=map&mapFeatureId=1267538231008834)),
4 more 35 signs along the road, no 40+ sign anywhere on it, and the northbound carriageway (named) is 35.

## Why CI missed it
`validate_data.py` did flag it (it was one of San Diego's 77 "red islands"), but the check was a **count** per region, and SD's
baseline was set to 77 on Oct 17 with every island accepted at once. A count can't tell a new island from an old one, and it only
looked at untagged roads, not stray OSM tags, single Mapillary signs or DOT speed lines.

## What changed (top of the pyramid first)
1. **Pipeline rule, one implementation for every region** (`scripts/islands.py`, run by `build_data.py` and `build_region.py`):
   a short (< 0.5 mi) run of one road that is red while the SAME road is posted <= 35 on both ends (by a real source, not an
   assumption) is an island. Unnamed pieces borrow the name of the road that continues at both ends.
   - No limit of its own -> takes the highest neighbouring posted limit (code `n`, solid green, popup "same road posted on both
     sides" and names the road).
   - **One source disagreeing with both neighbours can't turn a road red on its own** (an OSM tag, or a single Mapillary sign;
     stretch <= 300 m) -> takes the neighbour limit but is drawn as a dashed orange caution, "Sources disagree: OpenStreetMap
     says 45 mph here, but X is posted 35 on both sides. Check posted signs", penalised in routing and warned in route steps
     (code `q`). An official/DOT list, two agreeing sources, or 2+ Mapillary signs keep it red.
2. **DOT speed bleed fixed at the source** (`build_region.py`): a short way (< 150 m) only takes a state DOT/FHWA speed when it
   runs along the DOT line, not across it. Side streets were taking the crossing highway's 45-55 mph at junctions (most of the
   "official" islands in FL/SC/GA/TX/AZ regions).
3. **CI by location, not count**: `validate_data.py` now fails on any same-road island that isn't listed in
   `research/red_island_allowlist.json` (region + road + within 150 m). Today's leftovers are listed as `source-confirmed`
   (red because an official/DOT list or 2+ sources say 40+; the cite is in the entry) or `unreviewed` (one side of the road is
   only assumed <= 35, so the builder won't heal it). The old untagged-island count baseline was lowered to today's numbers.
4. Tests: `tests/test_islands.py` (rule + Soledad regression on real data), `scripts/test_islands_ui.py` (browser, in CI),
   `test_roadrule.js` (new codes).

## Same-road islands per region (detector, LSV rule)
| Region | Before | After | Left: source-confirmed | Left: unreviewed |
|---|---|---|---|---|
| sd | 137 | 76 | 14 | 62 |
| villages | 5 | 0 | 0 | 0 |
| ptc | 4 | 1 | 0 | 1 |
| hhi | 2 | 0 | 0 | 0 |
| myrtle | 17 | 3 | 0 | 3 |
| chs | 2 | 1 | 1 | 0 |
| 30a | 1 | 0 | 0 | 0 |
| portaransas | 1 | 0 | 0 | 0 |
| suncity | 24 | 9 | 4 | 5 |
| coachella | 2 | 2 | 0 | 2 |
| naples | 9 | 1 | 1 | 0 |
| goldenisles | 1 | 1 | 1 | 0 |
| galveston | 7 | 1 | 1 | 0 |
| ocoast | 44 | 31 | 19 | 12 |
| siesta | 12 | 7 | 6 | 1 |
| destin | 2 | 0 | 0 | 0 |
| pcb | 7 | 2 | 1 | 1 |
| staug | 4 | 0 | 0 | 0 |
| amelia | 3 | 1 | 1 | 0 |
| keywest | 1 | 0 | 0 | 0 |
| suncitycenter | 2 | 3 | 3 | 0 |
| lwr | 9 | 4 | 3 | 1 |
| rockport | 2 | 2 | 1 | 1 |
| wailea | 2 | 1 | 1 | 0 |
| **all** | **300** | **146** | 57 | 89 |

Regions not listed had none before or after. Hawaii and Old Orchard Beach have no OSM cache on the box; wailea was healed in place
with `scripts/heal_tiles.py` (same function). Full list with causes: `research/red_islands_report.json`.

## Legality changes vs live data (segments that changed red/OK for LSVs)
```
sd {'heal-n red->ok': '228 segs/7.18 mi', 'heal-q red->ok': '47 segs/1.56 mi', 'other red->ok': '2 segs/0.07 mi'}
villages {'heal-n red->ok': '14 segs/0.56 mi'}
ptc {'dot red->ok': '9 segs/0.10 mi'}
hhi {'dot ok->red': '1 segs/0.01 mi', 'dot red->ok': '1 segs/0.00 mi', 'heal-n red->ok': '14 segs/0.68 mi'}
myrtle {'dot ok->red': '20 segs/0.34 mi', 'dot red->ok': '28 segs/0.42 mi', 'heal-n red->ok': '5 segs/0.05 mi', 'heal-q red->ok': '1 segs/0.01 mi'}
chs {'dot ok->red': '1 segs/0.02 mi', 'dot red->ok': '1 segs/0.01 mi'}
30a {'dot red->ok': '4 segs/0.03 mi', 'heal-n red->ok': '5 segs/0.45 mi'}
gulfshores {'dot red->ok': '1 segs/0.01 mi'}
portaransas {'dot ok->red': '1 segs/0.02 mi', 'dot red->ok': '4 segs/0.07 mi'}
suncity {'dot ok->red': '1 segs/0.01 mi', 'dot red->ok': '10 segs/0.10 mi', 'heal-n red->ok': '20 segs/1.20 mi', 'heal-q red->ok': '3 segs/0.22 mi'}
naples {'dot ok->red': '9 segs/0.18 mi', 'dot red->ok': '34 segs/0.40 mi', 'heal-n red->ok': '2 segs/0.01 mi'}
galveston {'dot ok->red': '19 segs/0.25 mi', 'dot red->ok': '12 segs/0.22 mi', 'heal-n red->ok': '13 segs/0.64 mi'}
ocoast {'dot red->ok': '4 segs/0.07 mi', 'heal-n red->ok': '17 segs/0.36 mi', 'heal-q red->ok': '21 segs/0.67 mi'}
southpadre {'dot ok->red': '4 segs/0.12 mi'}
siesta {'dot ok->red': '6 segs/0.15 mi', 'dot red->ok': '22 segs/0.25 mi'}
destin {'dot ok->red': '11 segs/0.14 mi', 'dot red->ok': '10 segs/0.10 mi'}
pcb {'dot ok->red': '1 segs/0.03 mi', 'dot red->ok': '11 segs/0.15 mi', 'heal-n red->ok': '11 segs/0.24 mi', 'heal-q red->ok': '2 segs/0.11 mi', 'other red->ok': '4 segs/0.12 mi'}
staug {'dot ok->red': '6 segs/0.07 mi', 'dot red->ok': '13 segs/0.12 mi', 'heal-n red->ok': '3 segs/0.06 mi'}
amelia {'dot ok->red': '4 segs/0.05 mi', 'dot red->ok': '3 segs/0.08 mi', 'heal-n red->ok': '1 segs/0.01 mi'}
keywest {'dot ok->red': '1 segs/0.07 mi', 'dot red->ok': '4 segs/0.03 mi', 'heal-n red->ok': '5 segs/0.14 mi'}
suncitycenter {'dot red->ok': '3 segs/0.04 mi'}
lwr {'dot ok->red': '1 segs/0.01 mi', 'dot red->ok': '4 segs/0.05 mi', 'heal-n red->ok': '2 segs/0.05 mi', 'heal-q red->ok': '1 segs/0.01 mi'}
wailea {'heal-q red->ok': '4 segs/0.12 mi'}
TOTAL {'heal-n red->ok': 340, 'heal-q red->ok': 79, 'other red->ok': 6, 'dot red->ok': 178, 'dot ok->red': 86}
```
`dot ok->red` are short junction pieces that were green only because they borrowed the crossing road's DOT speed; most touch a
40+ or banned road.

## Needs a human look
- `q` (sources disagree) stretches now drawn as caution instead of red, e.g. Gilman Dr (OSM 45), Balboa Ave (OSM 45/40), Carmel
  Valley Rd (OSM 45), Palomar Airport Rd (OSM 45), El Camino Real / N El Camino Real (OSM 55), Nobel Dr (OSM 40), Airoso St and
  Legado Rd in OC (OSM 65 on residential streets). Search the built data for code `q`.
- Allowlist `unreviewed` entries (mostly untagged secondaries in San Diego/Chula Vista/Oceanside between assumed-25 pieces).
- `source-confirmed` long ones that look odd: Nobel Dr 40 (OSM + Mapillary agree), Dana Landing Rd 45 (Mapillary), Hotel Circle S 65.
