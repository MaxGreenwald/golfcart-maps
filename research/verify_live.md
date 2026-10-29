# verify_live — standing live verification

Manager coaching Oct 24 2026: one command drives golfcartmap.com like a user and prints a single PASS/FAIL. `scripts/deploy_web.sh production` runs it and appends one line (time PT, commit, Max OK ref, PASS or FAIL) to `$GCM_BOT_LOG` (default `/workspace/gcm/bot-log.md`).

## Command

```bash
# Against production (sets window.NO_TRACK=1 via scripts/live_notrack.py)
scripts/verify_live

# Against a local stamped build
python3 scripts/build_web.py
python3 scripts/serve_dist.py 8765 dist &
URL=http://localhost:8765/ scripts/verify_live

# Faster iteration (skip 64-region town sweep)
scripts/verify_live --quick

# One suite
scripts/verify_live --only test_road_labels
```

Summary line shape:

```
verify_live PASS commit=<12hex> time=<YYYY-MM-DD HH:MM PT> suites=N url=https://golfcartmap.com/
```

## What it runs

Through `scripts/live_notrack.py` (NO_TRACK):

| Suite | Checks |
|-------|--------|
| test_town_pages (`scripts/test_town_map_pages.py`) | Every visible `/map/<slug>` loads the right REG |
| test_road_labels | Popups match `GCMRule.cls` (Avoid must not show as OK) + one SD route search |
| test_ui | Route UX, browse popups, swap, Mexico/inland reject |
| test_vehicle | Golf cart / LSV toggle vs road-rule module |
| test_sw | Cache name, offline open, `/sandiego` offline |
| test_safety_caution | Dashed orange + popup/route caution text |
| test_delmar_warning | Time-boxed Del Mar advisory |
| test_chips / test_layout / test_city_chip / test_islands_ui / test_regions | Existing UI coverage |

## Proof it catches a wrong-legal road

```bash
python3 scripts/prove_bad_road_fail.py
```

Builds `dist/`, plants a display-only bug (Avoid segments drawn/popup as OK while `GCMRule.cls` still returns 3), serves locally, runs `verify_live --only test_road_labels`, expects FAIL, rebuilds a clean `dist/`. Output lands in `research/verify_live_evidence/planted_bad_road_fail.txt`. Never deploy that plant.

## Skill

`.cursor/skills/verify-golfcartmaps/` — Launch / Doctor / Drive / Evidence / Cleanup for agents. Feature map under `features/`.
