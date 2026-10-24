# Route search

## Sub-features

- Two taps / `testRoute(from, to)` builds a legal route
- Reset, swap, GPS “Your location”
- No legal route → clear message (not a silent empty map)

## How to get to it (user POV)

On the map, tap a start and end on legal streets (or use the From/To fields). San Diego default is fine for smoke.

## Driving it with Playwright

```bash
URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_ui.py
```

Observable end state: `getState().routed`, `#title`/`#sub` populated, screenshots under `SHOTS_DIR`.

## Gotchas

- Mexico / inland taps must be rejected (covered in `test_ui`).
- Golf cart mode in CA refuses roads over 25 mph (`test_vehicle`).
