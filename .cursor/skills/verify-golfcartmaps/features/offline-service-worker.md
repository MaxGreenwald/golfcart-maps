# Offline + service worker

## Sub-features

- Stamped cache name `gcm-<12 hex>` from content hash
- Precache map shell; old caches dropped
- Map opens offline; `/sandiego` offline on Cloudflare

## How to get to it (user POV)

Load the map once online, turn on airplane mode, reopen `/map` or `/sandiego`.

## Driving it with Playwright

```bash
URL=https://golfcartmap.com/ python3 scripts/live_notrack.py scripts/test_sw.py
```

Note: `test_sw` wants the **site root** as `URL` (not `/map/`); it sets `MAP=/map` itself.

Observable end state: `caches.keys() == [gcm-…]`, offline navigation still shows `#city`.

## Gotchas

- Raw `public/` (unstamped) caches nothing by design — only stamped `dist/` / prod prove offline.
