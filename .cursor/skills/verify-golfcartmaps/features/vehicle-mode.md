# Vehicle mode (golf cart / LSV)

## Sub-features

- Settings → Golf cart mode toggle (default LSV)
- Popups and routes follow `GCMRule` for the active vehicle
- `?veh=` and persistence

## How to get to it (user POV)

Open the sheet menu, toggle “Golf cart mode”.

## Driving it with Playwright

```bash
URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_vehicle.py
```

Observable end state: Carlsbad Blvd 35 mph is OK for LSV and Avoid for golf carts; popup wording matches.

## Gotchas

- No vehicle chip in the top chip row (settings only).
- HI/ME: plain golf carts not street-legal.
