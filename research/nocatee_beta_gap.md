# Nocatee beta-gap v2 (2026-10-22)
Run: origin/beta-gap-v2 research/beta_exit_gap_v2.py against region-nocatee data, with a nocatee entry added to a scratch copy of access_sources.json (not committed here; add it on beta-gap-v2 when that merges):
  "nocatee": {"kind": "county ordinance + community golf cart map", "url": "https://www.nocatee.com/golfcartmap", "applied": "research/regions/nocatee.json rule/bans"}
- Important-road miles: 43.6; sourced 70.5% (70.7% with neighbour inference, 70.8% with trusted OSM); bans 17.0 mi, all sourced
- Assumed-default miles: 12.3; corridors still needed to reach 70%: 0; reports: 0
- Conflicts (neighbour disagrees) to check first: Crosswater Pkwy 0.82 + 0.16 mi at 25, Cross Town Dr 0.64 mi at 25, Preservation Trail 0.38 mi, Landrum Ln 0.13 mi
- Passes the v2 bar by a hair, but stays beta (new region; conflicts open; Nocatee trail map not digitized).
