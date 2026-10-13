# Multi-region status (branch `multi-region`, local only — not pushed/deployed)
_2026-10-13_

## Phase 1 — done
- Data moved to `public/data/<region>/{index.json,pois.json,tiles/}`; `public/data/regions.json` (1.6 KB) + `public/data/rules.json` (1.3 KB, per-state profiles CA/FL/GA/SC).
- Region choice on load: `?r=<id>` > saved choice (localStorage) > geolocation only if permission is already granted (nearest region within 50 mi) > San Diego. Tapping 📍 in another region switches region. No new permission prompt.
- Header city picker (🌴 dropdown chip) + 🚙 LSV / ⛳ Golf cart toggle (default LSV, saved) + one-line rule note (citation on hover).
- Rules engine: `max_posted`, `designated_only`, `assume` (OSM classes treated as designated, marked unverified), `radius_mi`, `daylight_only` (shown as notes, not enforced), `cross` (false = no crossing faster roads except at cart-path crossings). Cart paths (src `c`) always allowed, drawn teal; OSM `golf_cart=no` blocks roads in golf-cart mode; `golf_cart=yes|designated` roads = designated (src `d`).
- San Diego LSV unchanged: test.py output identical to master, test_regress 12/31 identical route-by-route to master, test_ui ALL PASS, new scripts/test_regions.py ALL PASS.
- Overpass was down all session → new `scripts/pbf_extract.py` clips Geofabrik state .pbf files; `scripts/build_region.py` builds any non-SD region (Mapillary signs via the existing pipeline, 2+ signs to flip).

## Phase 2 — regions built
| Region | ways | cart-path ways | Mapillary-set ways | index gz | pois gz | tiles gz (total, lazy) |
|---|---|---|---|---|---|---|
| San Diego | 58,746 | 0 | 2,209 | 105 KB | 154 KB | 1.84 MB / 17 tiles |
| The Villages FL | 17,099 | 1,287 | 140 | 35 KB | 7 KB | 665 KB / 15 tiles |
| Peachtree City GA | 5,773 | 1,024 | 25 | 11 KB | 6 KB | 225 KB / 6 tiles |
| Hilton Head/Bluffton SC | 8,885 | 382 | 76 | 15 KB | 11 KB | 349 KB / 14 tiles |
Startup = regions+rules (~3 KB) + one region index+pois (SD ~260 KB gz, others ≤ 50 KB) + visible tiles.

**The Villages (priority):** multi-modal paths from OSM `golf_cart=yes/designated` (incl. tunnels/bridges labelled "cart tunnel"/"cart bridge"); golf-cart mode = paths + residential/local streets (assumed designated, per Sumter Co. Sec. 17‑3 + CDD guidance) + no street-level crossing of big roads except where a path meets them; roads tagged golf_cart=no blocked. LSV mode = roads ≤35 + paths. Test route Spanish Springs → north: 2.5 mi both modes.
**OSM maxspeed coverage (computed from the pbf, Overpass still failing):** Villages 27.6% (major 52%), Peachtree City 65.5% (major 82%), Hilton Head 5.0% (major 4.2%).

## Unverified / open questions
- Villages: are all residential streets designated in the Lake/Marion county + Wildwood parts? Are LSVs allowed on the multi-modal paths (CDD memo lists golf cars; app currently allows LSVs on paths)? Untagged paths missing from OSM. Night driving with lights not modelled.
- Peachtree City: golf-cart mode only uses tagged paths; city streets allowed by ordinance not digitized.
- Hilton Head: OSM speed tagging is ~5%, so untagged tertiary roads default to 25 (allowed) and untagged primary/secondary are blocked — needs a Town ordinance/speed list before launch. SC 4‑mile/daylight rules shown as text only. Cross-island trip (Coligny → Shelter Cove) has no legal route because US‑278 is blocked — likely correct but check.
- index.html SEO/about text is still San Diego-only; og descriptions still say "Free."

## Update 2026-10-13 (5 PM PT): Villages golf-cart sourcing, Hilton Head hidden
- Villages golf-cart mode now: streets posted ≤30 (was ≤35), plus a named banned-road list (US 27/441, US 301, SR 44, CR 466/466A/44/42/468/472, CR 25A, El Camino Real, Rainey Trail, Buena Vista Blvd, Morse Blvd, Griffin Ave, Rolling Acres Rd, Powell Rd, Miller St/Blvd, Rose/Willard Ave) on top of OSM golf_cart=no. 1,335 segments blocked for carts. Sources and unverified items: research/regions/villages.json.
- LSVs stay allowed on Villages multi-modal paths (Max).
- Hilton Head hidden from picker/geolocation (data kept, ?r=hhi for testing). Speed-list leads: research/regions/hhi.json.
- SEO/og text unchanged.
