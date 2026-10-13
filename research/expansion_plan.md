# Golf Cart Maps: Expansion Plan (research only, nothing changed or deployed)
_Drafted 2026-10-13. "UNVERIFIED" means the claim still needs checking against the city's ordinance before launch._

## 1. Top 15 regions (ranked)
Ranking factors: how common carts/LSVs are on public streets, the visitor rental market (outreach and revenue), how simple the rules are to model, and whether there is a dealer ecosystem.

| # | Region | Why | Rules that apply |
|---|---|---|---|
| 1 | The Villages, FL | Largest cart community in the US: 50k+ carts (estimate), 90–100+ mi of multi-use paths, cart tunnels and bridges [B][G1] | FL golf cart: designated roads only (316.212). LSV: posted ≤35 (316.2122) [FL1][FL2] |
| 2 | Peachtree City, GA | About 9,300 registered carts across 13k households; 100 mi of car-free paths; all ages [B] | GA: local designation for carts/PTVs; LSV ≤35 statewide [C] |
| 3 | Hilton Head / Bluffton, SC | Big resort rental market; strict state law creates real "can I drive here?" questions (US-278 banned) [IP] | SC permitted cart: secondary roads ≤35, within 4 mi of registration address, daylight unless local ordinance says otherwise (2025 change); LSV ≤35 [SC1][SC2] |
| 4 | Myrtle Beach / Grand Strand, SC | Very large beach rental market | SC rules above. Local ordinances UNVERIFIED |
| 5 | Charleston beach towns (Isle of Palms, Folly, Sullivan's), SC | Called a cart "mecca" [G2]; IOP publishes clear rules (IOP Connector at 45 is banned for LSVs) [IOP] | SC rules plus town rules |
| 6 | 30A / South Walton, FL | Dense LSV rentals (Seaside appears on cart-town lists [P]) | FL. Walton County designations UNVERIFIED |
| 7 | Gulf Shores / Orange Beach, AL | Beach rentals. Orange Beach requires permit, inspection, insurance, and designated streets ≤25 (from search synthesis, UNVERIFIED primary source) | AL is local-ordinance driven. UNVERIFIED |
| 8 | Port Aransas, TX | City licenses carts; "the beach is a city street"; carts banned on Hwy 361 south of Ave G [PA] | TX: carts allowed in master-planned communities, on beaches, and on ≤35 roads by local authorization (551.403); NEV ≤45 posted (551.303) [TX1][TX2] |
| 9 | Sun City / Sun City West, AZ | The original active-adult cart community; NEVs ride on public roads [G1][G2] | AZ NEV: posted ≤35, max 25 mph (28-966) [AZ1][AZ2] |
| 10 | Coachella Valley (Palm Desert, La Quinta), CA | Palm Desert has a city golf cart program; many 55+ residents [B] | CA: carts on ≤25 roads or locally designated routes; LSV ≤35. Same engine as San Diego [R] |
| 11 | Naples / Marco Island, FL | Retirement and resort area, cart-heavy HOAs | FL. City designations UNVERIFIED |
| 12 | St. Simons / Jekyll / Tybee Island, GA | Island towns on cart-friendly lists [P] | GA local designation |
| 13 | Galveston, TX | Beach rental market | TX; city ordinance UNVERIFIED |
| 14 | Lake Havasu City, AZ | Plausible resort and retirement market | AZ NEV rules. Cart legality UNVERIFIED (search found no confirmation) |
| 15 | Laguna Woods + Orange County coast, CA | Laguna Woods is a known cart city [B]; close to San Diego | CA, same engine as today |

Also worth considering: Hot Springs Village AR, Bald Head Island NC, Put-in-Bay OH, Southport NC, Sarasota/Anna Maria FL [B][P].

**Shop counts:** NOT MEASURED in this pass. The next step is a Google Maps / Apify count of "golf cart rental" and "golf cart dealer" results within each region's bounding box. The San Diego list has about 14 email contacts plus 4 contact forms for comparison.

**OSM maxspeed coverage:** NOT MEASURED. The Overpass API returned empty or error responses during this session. To rerun, use the `osmcov.sh` query pattern on the box (counts of maxspeed-tagged major and residential ways per bounding box). Expect weaker tagging in FL, SC, and AL residential areas than in CA, which means more reliance on the default rules plus city designation lists.

### Recommended first 3
1. **The Villages, FL:** the biggest audience and dealer base. The cart-path network is a mapping feature competitors don't have.
2. **Peachtree City, GA:** the path network is a single, well-defined dataset, and the city registers carts, which gives a clear audience. A good PR story.
3. **Hilton Head, SC:** high-value tourist rentals, which fit the "included with rental" monetization idea. The SC 4-mile and ≤35 rules are clearly stated and easy to compute.

Coachella Valley or Orange County is the cheapest *technical* next step because it uses the same CA rules, but the market is smaller.

## 2. Rules engine generalization
- **Vehicle mode per user:** `golf_cart` vs `lsv`, chosen in the UI. Today's app is LSV-only.
- **Per-state rule profile** (JSON):
  - `lsv_max_posted`: 35 in FL, AZ, SC, GA, CA; 45 in TX (NEV)
  - `cart_mode`: `designated_only` (FL, GA, AL), `posted_le` 35 with permit (SC), or `local` (TX, CA)
  - `cross_at_intersection`: true in most states
  - `radius_miles` (SC: 4 mi from registered or rental address)
  - `daylight_only` (SC default)
  - `default_unknown_speed` (currently 25)
- **Region layer:** a whitelist or blacklist of designated streets. FL and GA designated-road lists come from city/county ordinances and maps (manual digitizing). Explicit bans go in an overrides file (e.g., US-278 HHI, Hwy 361 Port Aransas).
- **Cart paths:** a separate edge class with the highest priority and routing preference. OSM `highway=path|cycleway` with `golf_cart=yes` or `motor_vehicle` tags. The Peachtree City and The Villages paths need an audit and possibly a city GIS import (license UNVERIFIED).
- **Data priority:** keep the current order (overrides → Mapillary 2+ signs → OSM → default) and add `designation list` above OSM for designated-only states.

## 3. Data pipeline and effort per region
Steps:
1. Geofabrik state extract
2. Clip to region bbox
3. Existing tile builder (0.1° tiles)
4. Mapillary sign pull (tiles endpoint)
5. Corridor sweep
6. Ordinance research and overrides
7. Regression routes
8. Street View spot checks

Effort estimates:
- Same-state (CA): about 0.5–1 day each.
- New state: about 2–4 days. Most of that is ordinance research and digitizing designated roads; the engine profile is one-time.
- Dollar cost for OSM + Mapillary: about $0 per region. TomTom/HERE are not needed at launch (see §4).

## 4. Data-source limits and costs at scale
- **OSM / Geofabrik:** free, ODbL (attribution required; any public derived database must stay ODbL) [OSM]. US state extracts are free from download.geofabrik.de [GF]. Avoid heavy Overpass use; it was unreliable in this session.
- **Mapillary:** free with a registered client_id.
  - Rate limits: entity API 60k requests/min, search API 10k/min, tiles 50k/day per app [M1].
  - Terms: the app must "materially supplement" Mapillary rather than redistribute it, attribution is required, and Mapillary may throttle or revoke access [M2].
  - Fit: one region at z14 is roughly hundreds to a few thousand tiles, so all 15 regions fit within days at 50k/day. Run the bulk pull offline and ship derived speed values, not Mapillary content.
- **TomTom:**
  - Public free tier: 2,500 non-tile requests/day (some pages say per month) [TT1][TT2].
  - Unified Speed Restrictions is enterprise/automotive with no public price [TT3].
  - Storing data for offline nationwide use almost certainly needs a custom contract (price UNKNOWN; likely five figures/yr).
  - Recommended use: verification only, e.g., Snap-to-Roads on suspect corridors.
- **HERE:**
  - Freemium: roughly 250k transactions/month, about $1 per 1k over that, around 5 RPS (from search synthesis) [H].
  - Some use cases are excluded from base plans, and storing or caching data is typically restricted.
  - Offline licensing needs a contract (UNKNOWN price).
- **Verification cost for all 15 regions:**
  - Mapillary + OSM: $0.
  - Optional TomTom/HERE spot checks on about 2,000 suspect corridors per region (30k calls total): fits in free tiers if spread out, or about $30 HERE overage.
  - The main cost is labor: about 2–4 days per new-state region.
- **Hosting:**
  - GitHub Pages: 1 GB site, 100 GB/mo soft bandwidth. Its terms also disallow sites "primarily directed at commercial transactions or SaaS" [GH]. That is a problem once paid, so move hosting before charging.
  - Cloudflare Pages: unmetered static bandwidth on the free tier [K].
  - Cloudflare R2: $0 egress, 10 GB and 10M reads/mo free, then $0.015/GB and $0.36 per million reads [R2].
- **Serving estimate:** a session is about 1.5 MB gz (index 105 KB + POIs 156 KB + about 5 tiles at roughly 150 KB) and about 10 requests.

| Monthly users | Bandwidth | GitHub Pages | Cloudflare Pages/R2 |
|---|---|---|---|
| 1k | about 1.5–5 GB | OK | $0 |
| 10k | about 15–50 GB | OK (soft limit) | $0 |
| 100k | about 150–500 GB | Over the soft limit | about $0–5/mo (Class B reads about 1–3M stay in the free tier) |

## 5. Keeping load fast
**Measured today (public/data):**
- index.json: 535 KB (105 KB gz)
- pois.json: 555 KB (156 KB gz)
- 18 tiles at 0.1°: 6.8 KB to 1.64 MB raw, 1.6–338 KB gz; about 10 MB total raw, about 2 MB gz

The app already loads tiles lazily (`loadTile`). The weak point is index.json, which holds all of San Diego's metadata and would grow with every region.

**Recommendation (phase 1):**
- Per-region folders: `data/<region>/index.json`, `tiles/`, and `pois.json`.
- A tiny `regions.json` manifest (about 2 KB: id, name, bbox, center, state profile).
- On load:
  1. Read `?r=` or localStorage.
  2. Otherwise use navigator.geolocation (only if permission is already granted, or after a tap). Pick the region whose bbox contains the user, or the nearest region within about 50 mi.
  3. Otherwise default to San Diego.
- A city picker in the header lets users switch at any time.
- Store `.json` files pre-compressed with gzip or brotli. Pages/CDN already compress JSON.
- Cost: no new tooling, the routing graph code stays the same, and startup loads only one region (about 260 KB plus visible tiles).

**Phase 2 (if nationwide or many regions):** PMTiles vector tiles on R2 for map display, with routing still on per-region JSON graphs.
- Pros: a single file per region, HTTP range requests, no server, and smooth zoom.
- Cons: the client needs to decode MVT to build the routing graph (extra complexity), and a build step is needed (tippecanoe).
- Don't use one nationwide GeoJSON file: it would be far too large.

## Sources
- [FL1] https://www.flsenate.gov/Laws/Statutes/2026/0316.212
- [FL2] https://www.flsenate.gov/Laws/Statutes/2025/316.2122 ; https://www.flhsmv.gov/pdf/proc/tl/tl-63.pdf
- [AZ1] https://www.azleg.gov/ars/28/00966.htm  [AZ2] https://apps.azdot.gov/files/mvd/mvd-forms-lib/96-0124.pdf
- [TX1] https://texas.public.law/statutes/tex._transp._code_section_551.403  [TX2] https://statutes.capitol.texas.gov/docviewer/?docName=TN.551.htm
- [SC1] https://scdps.sc.gov/drivinginsc/golf-cart-law  [SC2] https://law.justia.com/codes/south-carolina/title-56/chapter-2/section-56-2-105/
- [IOP] https://www.isleofpalms.gov/police/golf-carts-low-speed-vehicles  [IP] https://www.islandpacket.com/news/local/article301916509.html
- [PA] https://cityofportaransas.org/wp-content/uploads/2023/12/Golf-Cart-Application-2024-fillable.pdf
- [C] https://costacarts.com/are-golf-carts-street-legal-by-state/ (GA, SC summary; GA statute O.C.G.A. 40-6-331)
- [R] https://revengegolfcartparts.com/state-golf-cart-laws/ (CA summary)
- [B] https://www.bloomberg.com/features/2023-golf-cart-kingdom/  [G1] https://www.eacarts.com/blogs/blog/best-golf-cart-communities-us-cart-friendly-towns  [G2] https://golfcarts.org/top-7-golf-cart-communities-in-the-us/  [P] https://panethos.wordpress.com/2024/08/08/working-list-golf-cart-friendly-cities-and-towns/
- [M1] https://www.mapillary.com/developer/api-documentation/  [M2] https://www.mapillary.com/terms
- [TT1] https://docs.tomtom.com/pricing/  [TT2] https://apis.io/plans/tomtom/tomtom-plans-pricing/  [TT3] https://www.tomtom.com/products/unified-speed-restrictions/
- [H] https://www.here.com/get-started/pricing/rps-limits-excluded-use-cases
- [GH] https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- [R2] https://developers.cloudflare.com/r2/pricing/  [K] https://kbaise.com/compare?slugs=cloudflare-pages-workers%2Cgithub-pages%2Caws-amplify-hosting
- [OSM] https://www.openstreetmap.org/copyright  [GF] https://download.geofabrik.de/north-america/us.html
