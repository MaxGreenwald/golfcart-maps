# Golf Cart Maps (coastal North San Diego)

Static web app showing which roads a golf cart (≤25 mph) or LSV (≤35 mph) can legally use, with client-side routing restricted to those roads.

## Rebuild data
    python3 scripts/build_data.py     # stdlib only; caches Overpass tiles in ./cache (delete to refresh)
Output: `public/data/roads.json` (compact array format: [nameIdx, highway, mph|null, srcFlag, oneway, fromNode, toNode, [[lon,lat]...]]).

Classification: OSM `maxspeed` (mph) when tagged; else residential/living_street/service/unclassified → 25 (inferred); tertiary → unknown; secondary and above → assumed >35 (forbidden).
A short piece of a road can't be red on its own when the same road is posted ≤35 on both sides (scripts/islands.py; CI checks every region against research/red_island_allowlist.json).

## Run locally
    cd public && python3 -m http.server 8000      # raw source; the service worker caches nothing here
    python3 scripts/build_web.py && (cd dist && python3 -m http.server 8000)   # exactly what gets deployed

## Build and deploy
`public/` is the only source of the web app. `scripts/build_web.py` copies it to `dist/` (gitignored) and stamps the
service worker cache name (`gcm-<hash of every precached file>`), so there is no manual version bump. `dist/` is what
Cloudflare Pages serves and what the iOS/Android apps bundle (Capacitor `webDir`). Never commit `dist/` or the
Capacitor copies (`ios/App/App/public`, `android/app/src/main/assets/public`); CI fails if you do.

The one deploy command (needs `CLOUDFLARE_API_TOKEN`):

    scripts/deploy_web.sh preview <branch>   # https://<branch>.golfcart-maps.pages.dev
    scripts/deploy_web.sh production --max-ok <Max chat or card id>
        # https://golfcartmap.com — refuses unless HEAD equals origin/master
    scripts/deploy_worker.sh preview partner|analytics
    scripts/deploy_worker.sh production partner|analytics --max-ok <Max chat or card id>

## Legal notes (not legal advice)
- Golf carts: roads posted ≤25 mph (CVC 21716) or city-designated golf cart routes (CVC 21115 golf-course combined use, 21115.1, S&H 1950x).
- LSVs: may not operate on roads with speed limit >35 mph (CVC 21260/21266); may cross them at intersections.
- OSM is volunteer data; posted signs and local rules always win.
