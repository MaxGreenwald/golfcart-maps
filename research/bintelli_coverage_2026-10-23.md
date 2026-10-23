# Bintelli store + dealer coverage vs Golf Cart Maps (2026-10-23 PT)

For Max's follow-up with John Hegedus (President, Bintelli Golf Carts retail). Built by `research/bintelli_coverage.py` from public locator feeds (snapshots in `research/bintelli_raw/`). Private page: `/coverage/8fvdpdeqf4fb/` (noindex, not in sitemap/llms.txt), branch `bintelli-coverage`.

## Method
- Own stores: the Agile Store Locator feed behind bintelligolfcarts.com "Our Locations" (`https://www.bintelligolfcarts.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1`), 17 locations.
- Dealers: the same plugin feed on bintelli.com (`https://www.bintelli.com/wp-admin/admin-ajax.php?action=asl_load_stores&load_all=1&layout=1`). The visible bintelli.com/find-a-dealer/ page is only a lead form. 229 raw rows, minus 24 rows that are the company stores, minus duplicate "(Off-Road)" listings at the same address = **204 unique dealer locations** (incl. 1 Bahamas, 1 Puerto Rico, 1 Ontario).
- Coverage = distance to the nearest of our 64 live regions' bounding boxes (`public/data/regions.json`): **covered** <= 10 mi, **partly/nearby** 10-25 mi, **gap** > 25 mi. Bounding boxes, not road polygons, so 'covered' is slightly generous at the edges.

## Claims vs what the locators list
- They claim 14+ own stores: the locator lists **17** (15 markets; Myrtle Beach + North Myrtle Beach and Charleston + Summerville are counted as one market each). Nocatee has no street address in the feed.
- They claim 250+ dealers: the public dealer feed lists **204 unique** non-company locations (229 rows with duplicates). Either the locator is not complete or the 250+ counts off-road/e-bike-only or international partners.

## Headline numbers
| | Locations | Covered | Nearby (10-25 mi) | Gap | % covered | % covered or nearby |
|---|---|---|---|---|---|---|
| Own Bintelli Golf Carts stores | 17 | 9 | 2 | 6 | **52.9%** | 64.7% |
| Own-store markets | 15 | 8 | 1 | 6 | 53.3% | 60.0% |
| Dealers | 204 | 26 | 10 | 168 | **12.7%** | 17.6% |
| Dealer markets | 148 | 19 | 5 | 124 | 12.8% | 16.2% |

## Own-store markets
| Market | Stores | Coverage | Golf Cart Maps region (distance) |
|---|---|---|---|
| Myrtle Beach, SC | 2: Bintelli Golf Carts - Myrtle Beach (2606 N Kings Hwy, Myrtle Beach); Bintelli Golf Carts - North Myrtle Beach (115 Hwy 17 N, North Myrtle Beach) | covered | Myrtle Beach / Grand Strand, SC (0.0 mi) |
| Peachtree City, GA | 1: Bintelli Golf Carts - Peachtree (100 N Peachtree Pkwy Suite 8A, Peachtree City) | covered | Peachtree City, GA (0.0 mi) |
| Sarasota, FL | 1: Bintelli Golf Carts - Sarasota (7006 S Tamiami Trail, Sarasota) | covered | Siesta Key / Sarasota keys, FL (0.0 mi) |
| The Villages, FL | 1: Bintelli Golf Carts - The Villages (3411 W Main St., Leesburg) | covered | The Villages, FL (0.0 mi) |
| Fort Myers, FL | 1: Bintelli Golf Carts - Fort Myers (16850 S Tamiami Trl, Fort Myers) | covered | Fort Myers Beach, FL (1.1 mi) |
| Charleston, SC | 2: Bintelli Golf Carts - Summerville (1901 N Main St Summerville, Summerville); Bintelli Powersports (2137 Savannah Hwy, Charleston) | covered | Charleston beach towns, SC (2.3 mi) |
| Largo / Clearwater, FL | 1: Bintelli Golf Carts- Largo (10757 Ulmerton Rd, Largo) | covered | Clearwater Beach & Dunedin, FL (3.1 mi) |
| Nocatee / Ponte Vedra, FL | 1: Bintelli Golf Carts - Nocatee (, Ponte Vedra Beach) | covered | Nocatee / Ponte Vedra, FL (4.8 mi) |
| Daytona (Holly Hill / Ormond), FL | 1: Bintelli Golf Carts - Holly Hill (782 S. Yonge St., Ormond Beach) | partly | New Smyrna Beach, FL (14.1 mi) |
| Orlando (Casselberry), FL | 1: Bintelli Golf Carts - Casselberry (2730 S US Hwy 17 92, Casselberry) | gap | New Smyrna Beach, FL (29.8 mi) |
| Duluth (Atlanta), GA | 1: Bintelli Golf Carts - Duluth (5945 State Bridge Rd Suite 202, Duluth) | gap | Peachtree City, GA (42.4 mi) |
| Virginia Beach, VA | 1: Bintelli Golf Carts - Virginia Beach (2325 Virginia Beach Blvd, Virginia Beach) | gap | Outer Banks, NC (46.8 mi) |
| The Woodlands, TX | 1: Bintelli Golf Carts - Woodlands (I-45, Suite D, The Woodlands) | gap | Bolivar Peninsula, TX (54.0 mi) |
| Pompano Beach, FL | 1: Bintelli Golf Carts - Pompano (2491 N Federal Hwy, Pompano Beach) | gap | Naples / Marco Island, FL (97.9 mi) |
| Greenville, SC | 1: Bintelli Golf Carts - Greenville (627 Congaree Rd Suite A, Greenville) | gap | Peachtree City, GA (157.0 mi) |

## Dealer markets we cover or are near
| Market | Dealers | Coverage | Region (distance) |
|---|---|---|---|
| San Diego coast | 1 | covered | San Diego coast (0.0 mi) |
| Sun City / Sun City West, AZ | 3 | covered | Sun City / Sun City West, AZ (0.0 mi) |
| Emerald Isle & Atlantic Beach, NC | 2 | covered | Emerald Isle & Atlantic Beach, NC (0.0 mi) |
| Cape San Blas & Mexico Beach, FL | 1 | covered | Cape San Blas & Mexico Beach, FL (0.0 mi) |
| Cape May & the Wildwoods, NJ | 3 | covered | Cape May & the Wildwoods, NJ (0.0 mi) |
| Gulf Shores / Orange Beach, AL | 2 | covered | Gulf Shores / Orange Beach, AL (0.0 mi) |
| 30A / South Walton, FL | 1 | covered | 30A / South Walton, FL (0.0 mi) |
| South Bay LA, CA | 1 | covered | South Bay LA, CA (0.0 mi) |
| Bald Head Island / Southport, NC | 1 | covered | Bald Head Island / Southport, NC (0.0 mi) |
| Hilton Head / Bluffton, SC | 2 | covered | Hilton Head / Bluffton, SC (0.0 mi) |
| Fort Myers Beach, FL | 2 | covered | Fort Myers Beach, FL (0.0 mi) |
| New Smyrna Beach, FL | 1 | covered | New Smyrna Beach, FL (0.0 mi) |
| Newport Beach & Balboa, CA | 1 | covered | Newport Beach & Balboa, CA (0.1 mi) |
| Clearwater Beach & Dunedin, FL | 4 | covered | Clearwater Beach & Dunedin, FL (0.3 mi) |
| St. Pete Beach & Treasure Island, FL | 1 | covered | St. Pete Beach & Treasure Island, FL (0.6 mi) |
| Rehoboth, Dewey & Bethany Beach, DE | 2 | covered | Rehoboth, Dewey & Bethany Beach, DE (0.9 mi) |
| Naples / Marco Island, FL | 1 | covered | Naples / Marco Island, FL (2.3 mi) |
| Carolina Beach & Kure Beach, NC | 1 | covered | Carolina Beach & Kure Beach, NC (5.3 mi) |
| Topsail Island, NC | 1 | covered | Topsail Island, NC (8.9 mi) |
| Galveston, TX | 1 | partly | Galveston, TX (11.0 mi) |
| Long Beach Island, NJ | 1 | partly | Long Beach Island, NJ (12.6 mi) |
| Dauphin Island, AL | 1 | partly | Dauphin Island, AL (12.9 mi) |
| Boca Grande, FL | 1 | partly | Boca Grande, FL (13.1 mi) |
| Kelleys Island & Marblehead, OH | 1 | partly | Kelleys Island & Marblehead, OH (15.5 mi) |

## Dealer gaps by state
MI 19, NY 15, OH 13, NC 10, IA 9, VA 8, IL 8, TX 7, PA 6, TN 6, IN 5, KY 5, MS 4, CA 4, SC 4, NH 4, MA 4, WI 4, GA 3, NJ 2, MT 2, WV 2, AL 2, NV 2, LA 2, FL 2, MN 2, NM 1, WY 1, AR 1, ND 1, OK 1, Ontario 1, NE 1, MO 1, AZ 1, Bahamas 1, PR 1, UT 1, CT 1, ME 1. Most gap dealers are inland (Midwest/Northeast lake and RV markets: MI 19, NY 15, OH 13, IA 9, IL 8). The coastal and resort markets, where we've focused, are mostly covered.

## Gap own-store markets: what it would take (not built yet)
Statute numbers below are a starting point and still need checking against the official text before any build (bans and rules need citations).
| Store market | Nearest region now | Fit for a region | Estimate |
|---|---|---|---|
| Daytona (Holly Hill / Ormond Beach), FL | New Smyrna Beach, 14 mi (nearby) | Good: Daytona Beach Shores / Ormond beachside are cart/LSV areas; FL 316.212 + 316.2122 (LSV <=35) and the Volusia County rules already cited for NSB | ~2-3 h: extend NSB north or add 'Daytona Beach & Ormond'; city LSV/cart road lists needed for the v3 bar |
| Virginia Beach, VA | Outer Banks, 47 mi | Fair: VA 46.2-916.2 (carts only on designated roads posted <=25) and LSV <=35 (46.2-908.1); Sandbridge / Oceanfront | ~3-4 h: VA state rule is new to us; city designation list needed, or most streets stay red for carts |
| The Woodlands, TX | Bolivar Peninsula, 54 mi | Fair: TX Transp. Code 551.403/551.404 (master-planned community, <=35) plus The Woodlands Township path network | ~3 h: OSM pathways good; need Township/Montgomery County cart authorization source |
| Orlando (Casselberry), FL | New Smyrna, 30 mi | Weak: suburban arterial market, no single cart community | Skip for now |
| Duluth (north Atlanta), GA | Peachtree City, 42 mi | Weak: suburban; GA needs local designation (O.C.G.A. 40-6-331) | Skip unless a specific community is named |
| Pompano Beach, FL | Naples, 98 mi | Fair: Hillsboro Beach/Lighthouse Point LSV use, but dense urban | ~3 h, lower value |
| Greenville, SC | Peachtree City, 157 mi | Weak: inland metro; SC 56-2-105 permits within 4 mi of address | Skip |

Building Daytona + Woodlands would move own-store coverage to 11/17 covered (64.7%), and adding Virginia Beach too would make it 12/17 (70.6%).

