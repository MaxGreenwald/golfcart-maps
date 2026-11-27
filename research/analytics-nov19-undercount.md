# gcm-analytics undercount on 19 Nov 2026

Observed daily counts from the production gcm-analytics Worker, set next to the
7-day pre-Nov-19 baseline. This is not an invented lost-event figure. Any
difference is baseline minus observed, and is an approximation.

## Source

- Endpoint: production `https://gcm-analytics.maxgreenwald-assistant.workers.dev/stats?days=30`
  (same store as `/daily.csv`; days are UTC). The stats key was read the same
  way as `scripts/dashboard.py`.
- Response `generated`: 2026-11-20T16:33:15.428Z (08:33 PT on 20 Nov 2026).
- Filter: `internal-test-excluded` (the Worker's default /stats filter).
- `/stats` daily rows and `/daily.csv` do not include a per-day total events
  column. The columns they do expose are listed below. This note does not
  infer a per-day events total from the 30-day `totals.events` figure or by
  prorating the outage window.

## Gap window (Pacific Time)

- About 6:23 AM PT to 5:32 PM PT on 19 Nov 2026.
- 6:23 AM PT (14:23 UTC, 19 Nov): gcm-analytics Durable Object rows read
  reached the Workers Free plan cap of 5,000,000 rows read per day. Further
  DO row reads failed until the cap reset.
- 4:00 PM PT (00:00 UTC, 20 Nov): free-plan daily caps reset.
- 5:32 PM PT (01:32 UTC, 20 Nov): the `/workspace/gcm/dashboard/2026-11-19.md`
  file was generated at 2026-11-20T01:32:11.145Z, after the reset. That is
  the timestamp used here for the end of the gap window. The cap itself
  reset at 4:00 PM PT; this note does not claim how long /stats stayed
  unreachable after the reset.

The Worker stores days in UTC. UTC 19 Nov 2026 is 4:00 PM PT on 18 Nov
through 4:00 PM PT on 19 Nov. The 6:23 AM PT trip and the outage until the
4:00 PM PT reset fall on UTC 19 Nov. 4:00 PM PT to 5:32 PM PT is already
UTC 20 Nov, after the reset.

## Observed daily rows (UTC)

From the /stats response generated at 2026-11-20T16:33:15.428Z. UTC 19 Nov
is a complete day in this response.

| UTC day | active installs | new installs | sessions | town views | routes searched | routes found | routes completed | road reports |
|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | 56 | 50 | 67 | 61 | 9 | 6 | 0 | 0 |
| 2026-11-13 | 54 | 45 | 64 | 80 | 30 | 16 | 0 | 0 |
| 2026-11-14 | 51 | 49 | 70 | 96 | 41 | 35 | 1 | 0 |
| 2026-11-15 | 65 | 61 | 81 | 100 | 38 | 17 | 0 | 0 |
| 2026-11-16 | 38 | 27 | 63 | 51 | 7 | 3 | 0 | 0 |
| 2026-11-17 | 72 | 64 | 88 | 85 | 4 | 2 | 0 | 0 |
| 2026-11-18 | 46 | 44 | 59 | 62 | 23 | 14 | 0 | 0 |
| 2026-11-19 | 18 | 15 | 22 | 39 | 6 | 5 | 0 | 0 |

## 7-day pre-Nov-19 baseline vs observed 19 Nov

The baseline is the arithmetic mean of the seven complete UTC days
2026-11-12 through 2026-11-18. Observed is the 2026-11-19 row above.
Difference is baseline minus observed, an approximation. It is not a count
of events lost inside the 6:23 AM to 5:32 PM PT window, and it is not a
per-day events total.

| field | observed 19 Nov (UTC) | baseline mean (12-18 Nov UTC) | baseline minus observed (approximation) |
|---|---|---|---|
| active_installs | 18 | 54.5714 | 36.5714 |
| new_installs | 15 | 48.5714 | 33.5714 |
| sessions | 22 | 70.2857 | 48.2857 |
| town_views | 39 | 76.4286 | 37.4286 |
| routes_searched | 6 | 21.7143 | 15.7143 |
| routes_found | 5 | 13.2857 | 8.2857 |
| routes_completed | 0 | 0.1429 | 0.1429 |
| road_reports | 0 | 0.0000 | 0.0000 |

Sessions on UTC 19 Nov were 22, which is 31.3 percent of the 70.2857
baseline mean (a shortfall of 48.2857 sessions, baseline minus observed, an
approximation). That is below the recovery threshold used by
`scripts/cf_headroom.py --recovery`: a day is near the baseline when it is
at least 75 percent of this mean.

The 30-day /stats window in the same response reports `totals.events` =
5277. That figure is for the whole 30-day window, not for 19 Nov, and is
not used to invent a 19 Nov event count.

## Related: Durable Object rows read on UTC 19 Nov

A separate, observed figure from Cloudflare's GraphQL Analytics API (read-only
headroom check, complete UTC day 19 Nov 2026): gcm-analytics Durable Object
rows read used=7179564, which is 143.6 percent of the 5,000,000 free-plan
daily cap. This is a usage counter, not a count of product events, and is not
used as a lost-event figure.
