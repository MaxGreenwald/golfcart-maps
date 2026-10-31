# Pacific Beach unknown speeds (99/'i') — sources

Box 32.785..32.825, -117.26..-117.215. On master the build had 131 segments at 99/'i' here. No OSM `maxspeed` tag exists on any of these ways (live Overpass check: `analyze.py`).
The fills are in `scripts/overrides.py` `_PB_GAPS`/`GAP_RULES`. They apply only to ways with no maxspeed tag and no other override, so they never replace a tag. Tested by `tests/test_pb_speeds.py`.

| Road (segment) | mph | Sources |
|---|---|---|
| Turquoise St (Mission Blvd–Pacifica) | 25 | R-316675 Table 3 (La Jolla Bl–Cass, 25); Mapillary 25 signs at 3 spots (667828525767446…); SANDAG 20/25 |
| Foothill Blvd | 25 | Mapillary 25 sign 501492799481148; SANDAG 20; local report. Weakest evidence (1 sign) |
| Beryl St | 25 | Mapillary 25 signs at 3 spots; SANDAG 20 |
| Mission Blvd (Loring–Turquoise) | 30 | Mapillary 30 sign 625302710421552; SANDAG 25 |
| Mission Bay Dr (Garnet/Balboa ramps) | 35 | Mapillary 35 signs at 4 spots just south; SANDAG 30 |
| Balboa Ave (Grand–Garnet) | 35 | Mapillary 35 signs at 5 spots; R-316675 Table 1; SANDAG 25 |
| Soledad Mountain Rd (north) | 35 | Mapillary 35 signs at 5 spots; SANDAG 35 |
| Soledad Mountain Rd (south, near Garnet) | 40 | Mapillary 40 sign 322255992662393. SANDAG says 35, so check Street View |
| Garnet Ave (way 436317660 at SMR) | 40 | Mapillary 40 sign 1829036611190471; R-316675 Table 1 (45-5) |

Garnet 40 'm' (way 775872879, OSM 45): plausible. Mapillary has a 40 sign (and a 35 sign), Table 1 gives 45-5=40, and SANDAG has Garnet 40 pieces. It is kept and the test asserts it.

## Unresolved (left 99, no source found)
- Morena Blvd: 25 pieces. SANDAG class speed 35 only; no Mapillary sign and no OSM tag.
- Balboa Ave: 1 piece, 14 m near I-5.
- Unnamed links: 11 motorway_link, 9 primary_link, 3 secondary_link (I-5 / Balboa / SMR ramps).

Scripts: `ways99.py` (list 99 ways), `signs_by_road.py` (Mapillary signs per road), `sandag.py` (City PLN_Mobility layer 19 SPEED; class speed, cross-check only), `table.py`.
