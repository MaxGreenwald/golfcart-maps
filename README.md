# Golf Cart Maps (coastal North San Diego)

Static web app showing which roads a golf cart (≤25 mph) or LSV (≤35 mph) can legally use, with client-side routing restricted to those roads.

## Rebuild data
    python3 scripts/build_data.py     # stdlib only; caches Overpass tiles in ./cache (delete to refresh)
Output: `public/data/roads.json` (compact array format: [nameIdx, highway, mph|null, srcFlag, oneway, fromNode, toNode, [[lon,lat]...]]).

Classification: OSM `maxspeed` (mph) when tagged; else residential/living_street/service/unclassified → 25 (inferred); tertiary → unknown; secondary and above → assumed >35 (forbidden).

## Run locally
    cd public && python3 -m http.server 8000

## Deploy
`public/` is a plain static site: GitHub Pages, Netlify drop, etc.

## Legal notes (not legal advice)
- Golf carts: roads posted ≤25 mph (CVC 21115) or city-designated golf cart routes (CVC 21115.1, 1950x).
- LSVs: may not operate on roads with speed limit >35 mph (CVC 21260/21266); may cross them at intersections.
- OSM is volunteer data; posted signs and local rules always win.
