# Roads to verify: 24 new towns

These are the roads in each new town whose legal status is the least certain: a ban, an untagged major road, an assumed 25 mph tertiary, or a speed sitting on the golf cart or LSV cap.
Posted signs win. A road listed here is not a claim that the map is wrong.

## Sign check

Mapillary sign detection (`scripts/mapillary_signs.py`, called from `scripts/build_region.py`) did not run: `MAPILLARY_TOKEN` is not set. The token is read from the environment or from `.env`. No speed from that API was written into the tiles.
Street View batches 3 and 4 (`research/streetview_batch3/make_list.py`, `research/streetview_batch4/make_list.py`, then `resolve.py`) turn a filled sheet of signs a person read into `signs.json`. No sheet was filled. Those scripts do not call Google. Downloading Street View imagery would need a Google Maps Platform API key, and none is present (`GOOGLE_MAPS_API_KEY`, `GOOGLE_API_KEY`, and `STREETVIEW_API_KEY` are unset). No posted speed was guessed.
Rebuild input `cache/<id>_osm.json` is missing for 24 of these 24 towns, so `scripts/build_region.py` cannot apply signs even after a fetch. `public/data` for these towns was not edited.
A road piece is one drawn segment. It is backed by a posted sign when its source code is `m`, or its cited source names Mapillary or a Street View posted sign. The before and after counts match because the tiles were not rebuilt. No road changed from open to closed or from closed to open.
A road is dropped only when `research/expansion100_signchecks.json` marks it confirmed. That file is absent, so none of the roads below were dropped.

| Town | Posted-sign pieces before | Posted-sign pieces after |
|---|---:|---:|
| Fairhope, AL | 0 | 0 |
| Ocracoke, NC | 0 | 0 |
| Dade City, FL | 0 | 0 |
| Mount Dora, FL | 0 | 0 |
| Pinehurst, NC | 0 | 0 |
| Beaufort, SC | 0 | 0 |
| Port Royal, SC | 0 | 0 |
| Georgetown, SC | 0 | 0 |
| Horseshoe Bay, TX | 0 | 0 |
| Surfside Beach, TX | 0 | 0 |
| Colonial Beach, VA | 0 | 0 |
| Flagler Beach, FL | 0 | 0 |
| Oriental, NC | 0 | 0 |
| Celina, OH | 0 | 0 |
| Cape Charles, VA | 0 | 0 |
| Sun Lakes, AZ | 0 | 0 |
| Morro Bay, CA | 0 | 0 |
| Pismo Beach, CA | 0 | 0 |
| Howey-in-the-Hills, FL | 0 | 0 |
| Apalachicola, FL | 0 | 0 |
| Cedar Key, FL | 0 | 0 |
| Islamorada, FL | 0 | 0 |
| Key Largo, FL | 0 | 0 |
| Crystal River, FL | 0 | 0 |

Roads whose legal status changed (open to closed or closed to open): none.

## Fairhope, AL

- **South Greeno Road** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Greeno+Road+Fairhope+AL+@30.50940,-87.88615)
- **Greeno Road** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Greeno+Road+Fairhope+AL+@30.51442,-87.88615)
- **US Highway 98** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=US+Highway+98+Fairhope+AL+@30.55099,-87.89115)
- **Old Spanish Trail** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+Spanish+Trail+Fairhope+AL+@30.54552,-87.88911)
- **State Highway 104** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=State+Highway+104+Fairhope+AL+@30.54553,-87.88890)
- **United States Highway 98 (Alt)** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=United+States+Highway+98+(Alt)+Fairhope+AL+@30.55110,-87.89161)
- **Fairhope Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Fairhope+Avenue+Fairhope+AL+@30.52365,-87.88721)
- **Twin Beech Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Twin+Beech+Road+Fairhope+AL+@30.50171,-87.89870)

## Ocracoke, NC

- **Cutting Sage Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Cutting+Sage+Road+Ocracoke+NC+@35.11418,-75.97372)
- **Sunset Drive** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sunset+Drive+Ocracoke+NC+@35.11382,-75.97232)
- **Old Beach Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+Beach+Road+Ocracoke+NC+@35.10997,-75.97561)
- **Pamlico Shores Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Pamlico+Shores+Road+Ocracoke+NC+@35.11890,-75.98219)
- **British Cemetery Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=British+Cemetery+Road+Ocracoke+NC+@35.11871,-75.98078)
- **School Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=School+Road+Ocracoke+NC+@35.11150,-75.97928)

## Dade City, FL

- **US 98;US 301** (primary, 40 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=US+98;US+301+Dade+City+FL+@28.35578,-82.18671)
- **17th Street** (tertiary, 25 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=17th+Street+Dade+City+FL+@28.36332,-82.19988)
- **21st Street** (secondary, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=21st+Street+Dade+City+FL+@28.35560,-82.20411)
- **Meridian Avenue** (secondary, 30 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Meridian+Avenue+Dade+City+FL+@28.36464,-82.18464)
- **Lakeland Road** (primary, 40 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Lakeland+Road+Dade+City+FL+@28.36155,-82.18293)
- **Old State Road 52** (secondary, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+State+Road+52+Dade+City+FL+@28.35410,-82.20496)
- **Fort King Road** (tertiary, 25 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Fort+King+Road+Dade+City+FL+@28.34902,-82.20170)
- **Blanton Road** (secondary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Blanton+Road+Dade+City+FL+@28.37606,-82.20452)

## Mount Dora, FL

- **US 441** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=US+441+Mount+Dora+FL+@28.82396,-81.64304)
- **CR Old 441** (secondary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=CR+Old+441+Mount+Dora+FL+@28.80767,-81.67244)
- **Eudora Road** (tertiary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Eudora+Road+Mount+Dora+FL+@28.82079,-81.67507)
- **Orange Blossom Trail** (primary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Orange+Blossom+Trail+Mount+Dora+FL+@28.78365,-81.62475)
- **East 5th Avenue** (secondary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+5th+Avenue+Mount+Dora+FL+@28.80053,-81.64421)
- **North Highland Street** (secondary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Highland+Street+Mount+Dora+FL+@28.80043,-81.63642)
- **County Road 19A** (secondary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=County+Road+19A+Mount+Dora+FL+@28.80976,-81.68230)
- **East 1st Avenue** (secondary, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+1st+Avenue+Mount+Dora+FL+@28.79682,-81.63544)

## Pinehurst, NC

- **NC 211 Highway** (primary, 55 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=NC+211+Highway+Pinehurst+NC+@35.21206,-79.51325)
- **Midland Road** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Midland+Road+Pinehurst+NC+@35.20213,-79.44907)
- **Page Road** (tertiary, 25 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Page+Road+Pinehurst+NC+@35.19745,-79.46183)
- **US 15;US 501;NC 211** (primary, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=US+15;US+501;NC+211+Pinehurst+NC+@35.18656,-79.44237)
- **Morganton Road** (secondary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Morganton+Road+Pinehurst+NC+@35.18473,-79.46684)
- **Linden Road** (tertiary, 25 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Linden+Road+Pinehurst+NC+@35.19080,-79.49901)
- **Memorial Drive** (tertiary, 25 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Memorial+Drive+Pinehurst+NC+@35.20546,-79.46145)
- **Beulah Hill Road North** (primary, 35 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Beulah+Hill+Road+North+Pinehurst+NC+@35.19229,-79.47270)

## Beaufort, SC

- **Boundary Street** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Boundary+Street+Beaufort+SC+@32.43955,-80.67079)
- **Ribaut Road** (secondary, 40 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ribaut+Road+Beaufort+SC+@32.40482,-80.68526)
- **Sea Island Parkway** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sea+Island+Parkway+Beaufort+SC+@32.40856,-80.63974)
- **Carteret Street** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Carteret+Street+Beaufort+SC+@32.43168,-80.66995)
- **Ladys Island Drive** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ladys+Island+Drive+Beaufort+SC+@32.40629,-80.65822)
- **Robert Smalls Parkway** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Robert+Smalls+Parkway+Beaufort+SC+@32.43006,-80.71869)
- **Sams Point Road** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sams+Point+Road+Beaufort+SC+@32.41643,-80.64710)
- **Richard V Woods Memorial Bridge** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Richard+V+Woods+Memorial+Bridge+Beaufort+SC+@32.42473,-80.66845)

## Port Royal, SC

- **Ribaut Road** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ribaut+Road+Port+Royal+SC+@32.38392,-80.69763)
- **Ladys Island Drive** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ladys+Island+Drive+Port+Royal+SC+@32.39451,-80.68421)
- **Parris Island Gateway** (primary, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Parris+Island+Gateway+Port+Royal+SC+@32.37598,-80.71771)
- **Russell Bell Bridge** (primary, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Russell+Bell+Bridge+Port+Royal+SC+@32.37634,-80.71641)
- **Paris Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Paris+Avenue+Port+Royal+SC+@32.37326,-80.69256)
- **Waddell Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Waddell+Road+Port+Royal+SC+@32.39312,-80.69752)
- **Richmond Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Richmond+Avenue+Port+Royal+SC+@32.37749,-80.68888)
- **Battery Creek Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Battery+Creek+Road+Port+Royal+SC+@32.39707,-80.69945)

## Georgetown, SC

- **North Fraser Street** (trunk, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Fraser+Street+Georgetown+SC+@33.37365,-79.28865)
- **Church Street** (trunk, 35 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Church+Street+Georgetown+SC+@33.37534,-79.28723)
- **Highmarket Street** (trunk, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Highmarket+Street+Georgetown+SC+@33.38064,-79.30180)
- **South Fraser Street** (trunk, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Fraser+Street+Georgetown+SC+@33.36285,-79.29547)
- **Ocean Highway** (trunk, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ocean+Highway+Georgetown+SC+@33.36628,-79.25933)
- **Sylvan L. Rosen Bridge** (trunk, 99 mph, source i): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sylvan+L.+Rosen+Bridge+Georgetown+SC+@33.36098,-79.29513)
- **L. H. Siau Bridge** (trunk, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=L.+H.+Siau+Bridge+Georgetown+SC+@33.36705,-79.26774)
- **Front Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Front+Street+Georgetown+SC+@33.37077,-79.28953)

## Horseshoe Bay, TX

- **West Ranch Road 2147** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Ranch+Road+2147+Horseshoe+Bay+TX+@30.52110,-98.40730)
- **TX 71** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=TX+71+Horseshoe+Bay+TX+@30.51282,-98.37666)
- **West State Highway 71** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+State+Highway+71+Horseshoe+Bay+TX+@30.51595,-98.40022)
- **Bay West Boulevard** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Bay+West+Boulevard+Horseshoe+Bay+TX+@30.53128,-98.39966)
- **Mountain Dew Road** (residential, 30 mph, source t): Posted at the golf cart or LSV cap (30 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Mountain+Dew+Road+Horseshoe+Bay+TX+@30.53375,-98.33970)
- **Pronghorn** (residential, 30 mph, source t): Posted at the golf cart or LSV cap (30 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Pronghorn+Horseshoe+Bay+TX+@30.52947,-98.32766)
- **Hi Circle North** (residential, 30 mph, source t): Posted at the golf cart or LSV cap (30 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Hi+Circle+North+Horseshoe+Bay+TX+@30.54750,-98.37196)
- **Stag** (residential, 30 mph, source t): Posted at the golf cart or LSV cap (30 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Stag+Horseshoe+Bay+TX+@30.53109,-98.33973)

## Surfside Beach, TX

- **Bluewater Highway** (primary, 40 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Bluewater+Highway+Surfside+Beach+TX+@28.95202,-95.28721)
- **Baldwin Road** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Baldwin+Road+Surfside+Beach+TX+@28.97820,-95.33990)
- **Fort Velasco Drive** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Fort+Velasco+Drive+Surfside+Beach+TX+@28.94159,-95.29741)
- **Surf Drive** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Surf+Drive+Surfside+Beach+TX+@28.94001,-95.29535)
- **Thunder Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Thunder+Road+Surfside+Beach+TX+@28.94581,-95.30382)
- **Old Surfside Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+Surfside+Road+Surfside+Beach+TX+@28.95909,-95.33843)
- **Crab Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Crab+Street+Surfside+Beach+TX+@28.94586,-95.29245)
- **Levee Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Levee+Road+Surfside+Beach+TX+@28.92669,-95.35154)

## Colonial Beach, VA

- **McKinney Boulevard** (primary, 45 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=McKinney+Boulevard+Colonial+Beach+VA+@38.25168,-76.97845)
- **James Monroe Highway** (primary, 55 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=James+Monroe+Highway+Colonial+Beach+VA+@38.20448,-77.00779)
- **Washington Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Washington+Avenue+Colonial+Beach+VA+@38.25071,-76.96330)
- **Monroe Bay Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Monroe+Bay+Avenue+Colonial+Beach+VA+@38.23732,-76.96159)
- **Irving Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Irving+Avenue+Colonial+Beach+VA+@38.23188,-76.96080)
- **Boundary Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Boundary+Street+Colonial+Beach+VA+@38.24974,-76.96496)
- **Colonial Avenue** (secondary, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Colonial+Avenue+Colonial+Beach+VA+@38.25441,-76.97417)
- **Sunset Cove Court** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sunset+Cove+Court+Colonial+Beach+VA+@38.25241,-76.96790)

## Flagler Beach, FL

- **South Oceanshore Boulevard** (primary, 35 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Oceanshore+Boulevard+Flagler+Beach+FL+@29.47594,-81.12491)
- **Moody Boulevard** (primary, 35 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Moody+Boulevard+Flagler+Beach+FL+@29.48090,-81.12778)
- **North Ocean Shore Boulevard** (primary, 30 mph, source t): Golf-cart-only ban. An LSV may still use it where the posted limit allows. Confirm the ordinance names this road. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Ocean+Shore+Boulevard+Flagler+Beach+FL+@29.48136,-81.12757)
- **South Central Avenue** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Central+Avenue+Flagler+Beach+FL+@29.45035,-81.11386)
- **South Daytona Avenue** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Daytona+Avenue+Flagler+Beach+FL+@29.45771,-81.11857)
- **North Central Avenue** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Central+Avenue+Flagler+Beach+FL+@29.49097,-81.13308)

## Oriental, NC

- **Broad Street** (secondary, 25 mph, source t): Posted at the golf cart or LSV cap (25/35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Broad+Street+Oriental+NC+@35.02590,-76.69833)
- **Oriental Road** (tertiary, 35 mph, source t): Posted at the golf cart or LSV cap (35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Oriental+Road+Oriental+NC+@35.02521,-76.69920)
- **South Avenue** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Avenue+Oriental+NC+@35.02399,-76.69529)
- **Midyette Street** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Midyette+Street+Oriental+NC+@35.02802,-76.69781)
- **Mildred Street** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Mildred+Street+Oriental+NC+@35.02631,-76.69131)
- **1st Avenue** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=1st+Avenue+Oriental+NC+@35.02555,-76.69429)

## Celina, OH

- **East Market Street** (trunk, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Market+Street+Celina+OH+@40.54909,-84.55474)
- **North Main Street** (trunk, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Main+Street+Celina+OH+@40.55352,-84.57081)
- **West Logan Street** (trunk, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Logan+Street+Celina+OH+@40.54570,-84.57162)
- **West Market Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Market+Street+Celina+OH+@40.54900,-84.57161)
- **East Wayne Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Wayne+Street+Celina+OH+@40.55288,-84.56851)
- **South Main Street** (trunk, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Main+Street+Celina+OH+@40.53686,-84.57634)
- **Wayne Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Wayne+Street+Celina+OH+@40.56031,-84.54925)
- **South Walnut Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Walnut+Street+Celina+OH+@40.54849,-84.57235)

## Cape Charles, VA

- **Randolph Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Randolph+Avenue+Cape+Charles+VA+@37.26828,-76.00710)
- **Stone Road** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Stone+Road+Cape+Charles+VA+@37.26919,-76.00081)
- **VA 184** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=VA+184+Cape+Charles+VA+@37.26811,-76.01068)
- **Bay Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Bay+Avenue+Cape+Charles+VA+@37.26703,-76.02301)
- **Fig Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Fig+Street+Cape+Charles+VA+@37.26727,-76.01081)
- **Mason Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Mason+Avenue+Cape+Charles+VA+@37.26705,-76.02128)
- **Washington Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Washington+Avenue+Cape+Charles+VA+@37.27293,-76.01967)
- **Old Cape Charles Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+Cape+Charles+Road+Cape+Charles+VA+@37.26699,-76.01137)

## Sun Lakes, AZ

- **South Alma School Road** (residential, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Alma+School+Road+Sun+Lakes+AZ+@33.19748,-111.85820)
- **South Arizona Avenue** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Arizona+Avenue+Sun+Lakes+AZ+@33.20443,-111.84113)
- **East Chandler Heights Road** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Chandler+Heights+Road+Sun+Lakes+AZ+@33.23315,-111.83890)
- **East Riggs Road** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Riggs+Road+Sun+Lakes+AZ+@33.21854,-111.84128)
- **South Dobson Road** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=South+Dobson+Road+Sun+Lakes+AZ+@33.20360,-111.87575)
- **AZ 587** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=AZ+587+Sun+Lakes+AZ+@33.19342,-111.84096)
- **West Hunt Highway** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Hunt+Highway+Sun+Lakes+AZ+@33.20351,-111.87549)
- **East Hunt Highway** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Hunt+Highway+Sun+Lakes+AZ+@33.20403,-111.84024)

## Morro Bay, CA

- **Main Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Main+Street+Morro+Bay+CA+@35.36850,-120.85000)
- **Morro Bay Boulevard** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Morro+Bay+Boulevard+Morro+Bay+CA+@35.36593,-120.84930)
- **Old U.S. Route 466** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+U.S.+Route+466+Morro+Bay+CA+@35.38015,-120.85515)
- **Quintana Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Quintana+Road+Morro+Bay+CA+@35.36647,-120.84050)
- **Morro Bay State Park Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Morro+Bay+State+Park+Road+Morro+Bay+CA+@35.34550,-120.83901)

## Pismo Beach, CA

- **El Camino Real** (motorway, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=El+Camino+Real+Pismo+Beach+CA+@35.14682,-120.64488)
- **Cabrillo Highway** (motorway, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Cabrillo+Highway+Pismo+Beach+CA+@35.14939,-120.64923)
- **Five Cities Drive** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Five+Cities+Drive+Pismo+Beach+CA+@35.13448,-120.61950)
- **James Way** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=James+Way+Pismo+Beach+CA+@35.13780,-120.61645)
- **Hinds Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Hinds+Avenue+Pismo+Beach+CA+@35.14100,-120.63921)
- **Pomeroy Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Pomeroy+Avenue+Pismo+Beach+CA+@35.14153,-120.64021)
- **North 4th Street** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+4th+Street+Pismo+Beach+CA+@35.13695,-120.62152)
- **Wadsworth Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Wadsworth+Avenue+Pismo+Beach+CA+@35.14606,-120.63930)

## Howey-in-the-Hills, FL

- **CR 48** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=CR+48+Howey-in-the-Hills+FL+@28.73567,-81.79693)
- **SR 19** (primary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=SR+19+Howey-in-the-Hills+FL+@28.72674,-81.77566)
- **Number Two Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Number+Two+Road+Howey-in-the-Hills+FL+@28.71022,-81.78100)
- **West Central Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Central+Avenue+Howey-in-the-Hills+FL+@28.71184,-81.77757)
- **Palm Avenue** (primary, 35 mph, source t): Posted at the golf cart or LSV cap (35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Palm+Avenue+Howey-in-the-Hills+FL+@28.71418,-81.77291)
- **Wild Iris Street** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Wild+Iris+Street+Howey-in-the-Hills+FL+@28.70427,-81.78514)
- **Florida Fern Avenue** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Florida+Fern+Avenue+Howey-in-the-Hills+FL+@28.70395,-81.78483)
- **Marsh Lily Drive** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Marsh+Lily+Drive+Howey-in-the-Hills+FL+@28.70306,-81.78283)

## Apalachicola, FL

- **12th Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=12th+Street+Apalachicola+FL+@29.73008,-85.00126)
- **Market** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Market+Apalachicola+FL+@29.73316,-84.99409)
- **Bluff Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Bluff+Road+Apalachicola+FL+@29.73135,-85.00841)
- **Airport Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Airport+Road+Apalachicola+FL+@29.71793,-85.02105)
- **Avenue E** (primary, 35 mph, source t): Posted at the golf cart or LSV cap (25/35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Avenue+E+Apalachicola+FL+@29.71651,-84.99615)
- **US 98** (primary, 35 mph, source t): Posted at the golf cart or LSV cap (25/35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=US+98+Apalachicola+FL+@29.72371,-84.98131)
- **Market Street** (primary, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Market+Street+Apalachicola+FL+@29.72706,-84.98383)

## Cedar Key, FL

- **Gulf Boulevard** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Gulf+Boulevard+Cedar+Key+FL+@29.14028,-83.04207)
- **Airport Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Airport+Road+Cedar+Key+FL+@29.13570,-83.04772)
- **Southwest Airport Road** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Southwest+Airport+Road+Cedar+Key+FL+@29.13261,-83.05197)
- **D Street** (primary, 30 mph, source t): Posted at the golf cart or LSV cap (30 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=D+Street+Cedar+Key+FL+@29.13675,-83.03371)
- **SR 24** (primary, 35 mph, source t): Posted at the golf cart or LSV cap (30/35 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=SR+24+Cedar+Key+FL+@29.15002,-83.03148)
- **Hodges Avenue** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Hodges+Avenue+Cedar+Key+FL+@29.14928,-83.04167)

## Islamorada, FL

- **Overseas Highway** (trunk, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Overseas+Highway+Islamorada+FL+@24.89877,-80.65783)
- **Old State Highway 4A** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+State+Highway+4A+Islamorada+FL+@24.93504,-80.61546)
- **Old Overseas Highway** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Old+Overseas+Highway+Islamorada+FL+@24.95805,-80.57250)
- **Venetian Boulevard** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Venetian+Boulevard+Islamorada+FL+@24.96113,-80.58731)
- **Carroll Street** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Carroll+Street+Islamorada+FL+@24.91863,-80.63282)
- **Madeira Road** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Madeira+Road+Islamorada+FL+@24.92380,-80.63038)

## Key Largo, FL

- **Ocean Bay Drive** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Ocean+Bay+Drive+Key+Largo+FL+@25.08135,-80.44180)
- **East Drive** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=East+Drive+Key+Largo+FL+@25.08991,-80.44492)
- **Hibiscus Lane** (residential, 25 mph, source t): Posted at the golf cart or LSV cap (25 mph). A faster block in the same name would change the route. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Hibiscus+Lane+Key+Largo+FL+@25.11107,-80.42399)
- **Sunset Boulevard** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Sunset+Boulevard+Key+Largo+FL+@25.09757,-80.43738)
- **Kay Drive** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Kay+Drive+Key+Largo+FL+@25.11003,-80.42569)
- **Caribbean Drive** (residential, 25 mph, source i): Residential street with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Caribbean+Drive+Key+Largo+FL+@25.08975,-80.43696)

## Crystal River, FL

- **Suncoast Boulevard** (trunk, 99 mph, source v): Explicit ban (closed to golf carts and LSVs). Confirm the sign and the crossing. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Suncoast+Boulevard+Crystal+River+FL+@28.88361,-82.58295)
- **North Citrus Avenue** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Citrus+Avenue+Crystal+River+FL+@28.90034,-82.59309)
- **North Turkey Oak Drive** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Turkey+Oak+Drive+Crystal+River+FL+@28.90113,-82.56940)
- **West Norvell Bryant Highway** (secondary, 99 mph, source i): Untagged major road, drawn at the fast default. The real posted limit may be lower. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Norvell+Bryant+Highway+Crystal+River+FL+@28.89148,-82.54806)
- **West Fort Island Trail** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+Fort+Island+Trail+Crystal+River+FL+@28.87129,-82.59845)
- **West State Park Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=West+State+Park+Street+Crystal+River+FL+@28.91912,-82.62759)
- **North Dunkenfield Avenue** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=North+Dunkenfield+Avenue+Crystal+River+FL+@28.87323,-82.55078)
- **Northwest 19th Street** (tertiary, 25 mph, source i): Tertiary road with no posted speed, assumed 25 mph. A higher sign would close it. Posted speed seen: not read. Source: none. [Map](https://www.google.com/maps/search/?api=1&query=Northwest+19th+Street+Crystal+River+FL+@28.91317,-82.60784)

