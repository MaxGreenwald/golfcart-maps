# Town / region map pages

## Sub-features

- `/map/<slug>` loads the interactive map for that region (`REG.id`)
- City chip (`#city`) lists every visible region A–Z
- SEO page `/<slug>` is static; CTA enters the map (not covered by town sweep)

## How to get to it (user POV)

Open `https://golfcartmap.com/map/sandiego` (or pick a city in the chip). Every beach/golf town in the picker has a slug from `public/data/regions.json`.

## Driving it with Playwright

```bash
URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_town_map_pages.py
# or
scripts/verify_live --only test_town_pages
```

Observable end state: for each visible region, `window.ready===true`, `REG.id` matches, `#city` exists.

## Gotchas

- Dist/local: map is at `/map/`, not `/` (landing). Use `scripts/serve_dist.py`.
- Hidden regions in `regions.json` are skipped.
- Full sweep is slow (~64 pages); use `verify_live --quick` only when iterating another feature.
