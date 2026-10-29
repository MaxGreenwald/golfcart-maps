# Next 11 regions: ranking (2026-10-28)

Max (Oct 28): "add greenwich ct and the next 10 cities to the map". Greenwich is first. The other ten are the next uncovered public-road towns in `research/towns.md`, with one replacement where a bbox would overlap a live region.

**How these were checked:** a local ordinance or the state rule must allow carts or LSVs on some public roads. Gated and private islands were skipped. Every bbox was checked against the live boxes in `public/data/regions.json` so none overlap.

| # | id | Region | State | Why (one line) | Key local rule / source |
|---|---|---|---|---|---|
| 1 | greenwich | Greenwich | CT | First Connecticut region. Since Oct 1, 2024, registered LSVs may use roads posted 25 mph or less unless the traffic authority closes them. | LSVs: [Conn. Gen. Stat. Sec. 14-289m](https://www.cga.ct.gov/current/pub/chap_248.htm#sec_14-289m) (P.A. 24-20). Golf carts only if the town traffic authority permits them: [Sec. 14-300g](https://www.cga.ct.gov/current/pub/chap_249.htm#sec_14-300g). No Greenwich permission was found. |
| 2 | tyrone | Tyrone | GA | Cart town on the north edge of Peachtree City, with town permits and multi-use paths. | Designated streets posted 35 mph or less, plus paved paths. [Town of Tyrone paths page](https://tyronega.gov/paths). The street list is not digitized, so plain carts stay red except tagged paths. |
| 3 | fayetteville | Fayetteville | GA | Cart paths and a city motorized-cart permit, east of the live Peachtree City box. | Authorized streets and paths only; not major or collector streets. [Fayetteville permits](https://www.fayetteville-ga.gov/413/Permits-Licenses), [Code Sec. 82-262](https://library.municode.com/ga/fayetteville/codes/code_of_ordinances?nodeId=PTIICOOR_CH82TRVE_ARTIXMOCA_S82-260DE). |
| 4 | senoia | Senoia | GA | Cart town south of Peachtree City with a city registration. | Carts on streets posted 35 mph or less; not SR 16 or SR 85 except crossings. [Senoia Code Ch. 66](https://library.municode.com/ga/senoia/codes/code_of_ordinances?nodeId=COOR_CH66TRVE). |
| 5 | conyers | Conyers | GA | City motorized-cart district (2014, expanded 2019 and 2024). | District streets only; the map is not digitized. [City of Conyers golf cart district](https://www.conyersga.com/residents/golf-cart-district). |
| 6 | augusta | Augusta | GA | Consolidated government PTV ordinance for downtown and a few named streets. | Named streets plus a downtown area, with listed bans (15th, Walton Way, Gordon Highway, and others). [Augusta PTV requirements](https://www.augustaga.gov/DocumentCenter/View/11417/PERSONAL-TRANSPORTATION-VEHICLE--APPLICATION-PTV). Downtown streets that are not named stay red. |
| 7 | euharlee | Euharlee | GA | 2025 ordinance for carts and LSVs on subdivision streets. | Carts on streets posted 25 mph or less; LSVs 35 or less; not on state or county highways except to cross. [Ord. 2025-03](https://euharlee.com/wp-content/uploads/2024/04/Ordinance-2025-03-Golf-Cart-Amended-5-6-2025-1.pdf). |
| 8 | stmarys | St. Marys | GA | Coastal cart town north of Amelia Island, separate from the live Amelia box. | PTVs on streets posted 35 mph or less, except Winding Road; state highways are crossing only. [City PTV ordinance (2021)](https://cms3.revize.com/revize/stmarysnew/department/community_development/PTVs.20210419.v1.pdf). |
| 9 | lowerkeys | Lower Keys / Marathon | FL | The keys northeast of live Key West (Big Pine through Marathon). The box starts north of the Key West box. | LSVs on roads posted 35 mph or less. No Marathon golf-cart street list was found, so plain carts stay red except tagged paths. [Marathon council, 2011](https://keysweekly.com/42/council-says-golf-carts-are-a-go/), [F.S. 316.2122](https://www.flsenate.gov/Laws/Statutes/2025/316.2122). |
| 10 | cocoabeach | Cocoa Beach | FL | Replacement for Sarasota (see skips). Beach town with a city golf-cart network map. | Designated streets posted 30 mph or less on the city's map; the map is not digitized. [Resolution 2023-07](https://cocoabeach.granicus.com/MetaViewer.php?clip_id=4536&meta_id=240956&view_id=4), [Ord. 1660](https://cocoabeach.granicus.com/MetaViewer.php?clip_id=4213&meta_id=225018&view_id=4). |
| 11 | venice | Venice | FL | Beach town south of the live Siesta Key box. | No city golf-cart street designation was found. LSVs follow F.S. 316.2122 (roads posted 35 mph or less). [Venice code](https://library.municode.com/fl/venice/codes/code_of_ordinances), [F.S. 316.212](https://www.flsenate.gov/Laws/Statutes/2025/316.212). |

## Skips and the Sarasota replacement

- **Sarasota / Lido Key / Longboat Key (`sarasota`): skipped.** The live `siesta` box is [27.17, -82.7, 27.45, -82.5] and its cover already names Lido, St. Armands, Longboat Key, and the south Sarasota mainland. A second box on that strip would overlap. There is no non-overlapping slice that still contains the keys. Replaced with Cocoa Beach, the next uncovered town in the replacement list.
- **Not used as replacements:** Stone Harbor is already inside `capemay`. Lakeside and Marblehead are already inside `kelleys`. Daufuskie, Fripp, and other gated islands stay out. Solivita and On Top of the World are private-community road systems and were not needed once Cocoa Beach fit.

## Notes

- **New state:** Connecticut is added to `public/data/rules.json`. LSV cap is 25 mph (Sec. 14-289m), not 35. Plain golf carts are not street-legal unless that town's traffic authority permits them (Sec. 14-300g). Greenwich has not.
- **Peachtree City cluster:** `tyrone` starts north of live `ptc` (33.46). `fayetteville` starts east of -84.50. `senoia` stops south of 33.33. The three boxes do not overlap `ptc` or each other.
- **Golf cart vs LSV:** where the allowed street list is not digitized (Tyrone, Fayetteville, Conyers, Augusta downtown, Cocoa Beach, Lower Keys, Venice), plain golf carts stay red except tagged cart paths. That is stricter than a town that allows "most" slow streets. It does not paint a road green without a source.
- **Posted signs win.** A local ban in these files does not get lifted by a speed tag.
