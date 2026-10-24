# Road popups & legal labels

## Sub-features

- Tap a road → popup with speed, source, **OK for …** or **Avoid: …**
- Color: green `#12a150` OK, red `#e5484d` Avoid, amber dashed safety caution
- Status must match `GCMRule.cls(seg, RULE)` from `public/roadrule.js`

## How to get to it (user POV)

Zoom in, tap a colored road line, read the bold status line in the popup.

## Driving it with Playwright

```bash
URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_road_labels.py
scripts/verify_live --only test_road_labels
```

Observable end state: for sampled Avoid segments, popup/status contains `Avoid` and is not green “OK for”; for OK segments, opposite. Plus one SD `testRoute` success.

## Gotchas

- **Worst failure:** Avoid per module but UI shows legal. `scripts/prove_bad_road_fail.py` plants that locally and expects FAIL.
- Safety cautions (dashed orange) are separate from Avoid; see `test_safety_caution.py`.
- Run in golf cart mode for denser Avoid samples in CA.
