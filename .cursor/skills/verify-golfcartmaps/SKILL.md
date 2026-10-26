---
name: verify-golfcartmaps
description: Drive the Golf Cart Maps web app (golfcartmap.com / local dist) like a user with Playwright + live_notrack (NO_TRACK), and prove town pages, routes, road legal/caution labels vs roadrule.js, and offline/SW. Use after any web deploy or when changing map, routing, road rules, or service worker.
---

# verify-golfcartmaps

Primary surface: the **web map** at `/map` (and `/map/<slug>`), plus SEO town pages at `/<slug>`. iOS/Android wrap the same `dist/`; this skill verifies the web build users and the native WebView share.

## Launch

**Production (read-only checks):** no server to start. Target `https://golfcartmap.com/`.

**Local stamped build (preferred for plants and pre-merge):**

```bash
cd /workspace/gcm-verify-live   # or the repo root / worktree
python3 scripts/build_web.py
python3 scripts/serve_dist.py 8765 dist &
# ready when: curl -sf http://localhost:8765/map/ succeeds and HTML mentions the map shell
```

Teardown local: kill the `serve_dist.py` PID you started (never `pkill -f python` by name).

Env:

- `URL` — site root (`https://golfcartmap.com/` or `http://localhost:8765/`) or `/map/` form; `scripts/verify_live` normalizes it.
- Evidence dir default: `research/verify_live_evidence/`.

## Doctor

Read-only. Run before Drive when anything looks off:

```bash
# 1) Target answers
curl -sI "$URL" | head -5
# 2) SW cache name looks stamped on prod/preview (gcm-<12 hex>), not placeholder
curl -s "${URL%/}/sw.js" | head -c 200
# 3) Road-rule module present
curl -s "${URL%/}/roadrule.js" | head -c 80
# 4) Playwright + chromium available
python3 -c "from playwright.sync_api import sync_playwright; print('ok')"
```

Worth driving only if the map shell loads (`window.ready===true` within 120s) and `sw.js` is reachable. A 5xx or empty `regions.json` → stop and report; do not “fix” by skipping suites.

## Drive

Prefer the standing command (bundles suites through `scripts/live_notrack.py` so `window.NO_TRACK=1` on every context):

```bash
scripts/verify_live                          # full; paste PASS into /workspace/gcm/bot-log.md after a prod deploy
scripts/verify_live --quick                  # skip 64-region town sweep
scripts/verify_live --only test_road_labels  # labels vs GCMRule.cls
```

Harness: Playwright sync scripts under `scripts/test_*.py`. Stable handles: `#city`, `#chips`, `#qf`/`#q`, `.leaflet-popup-content`, `window.ready`, `window.REG`, `window.GCMRule`, `testRoute([...],[...])`, `MODE`.

One-suite examples (always wrap with live_notrack against prod):

```bash
URL=https://golfcartmap.com/map/ python3 scripts/live_notrack.py scripts/test_ui.py
URL=https://golfcartmap.com/ python3 scripts/live_notrack.py scripts/test_sw.py
```

Feature journeys live in `features/`. A proof that only hits San Diego is incomplete when the map lists other regions — run `test_town_pages` or full `verify_live` before calling a deploy verified.

### Prove the worst failure still fails

```bash
python3 scripts/prove_bad_road_fail.py
```

Expect `verify_live FAIL` and a log under `research/verify_live_evidence/planted_bad_road_fail.txt`. The plant is local `dist/` only; the script rebuilds a clean `dist/` afterward.

## Evidence

Keep under `research/verify_live_evidence/` (survives Cleanup):

- `last_summary.txt` — PASS/FAIL line from `verify_live`
- Screenshots from suites (`SHOTS` / `SHOTS_DIR`)
- `planted_bad_road_fail.txt` + `planted_summary.txt` from the plant proof

Proof standards:

- Exercise the real UI path (map click → popup, `testRoute`, city chip), not internal setters alone.
- Capture action + resulting state (popup text, `REG.id`, offline `#city`).
- Legal/caution labels must match `GCMRule.cls` / `public/roadrule.js` (see `test_road_labels.py`).
- Against production, always use `live_notrack.py` (or `verify_live`) so analytics stay clean.

## Cleanup

- Stop only the `serve_dist.py` (or preview) process this run started.
- Do **not** delete `research/verify_live_evidence/`.
- After `prove_bad_road_fail.py`, confirm `dist/app.js` no longer contains `__plant` (script rebuilds dist).

## Helpers

| Helper | Invocation |
|--------|------------|
| Standing check | `scripts/verify_live` |
| NO_TRACK wrapper | `python3 scripts/live_notrack.py scripts/test_ui.py` |
| Town sweep | `URL=…/map/ python3 scripts/test_town_pages.py` |
| Labels vs module | `URL=…/map/ python3 scripts/test_road_labels.py` |
| Planted wrong-legal proof | `python3 scripts/prove_bad_road_fail.py` |
| Local server | `python3 scripts/serve_dist.py 8765 dist` |

Maintenance: `/maintain-verification-skill` when routes, chips, or road-rule behavior change.
