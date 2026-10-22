#!/usr/bin/env python3
"""Daily analytics dashboard for the Manager bot: reads the gcm-analytics Worker's /stats and writes
/workspace/gcm/dashboard/YYYY-MM-DD.md (date in America/Los_Angeles).

  python3 scripts/dashboard.py                 # preview Worker (the only one deployed today), last 30 days
  python3 scripts/dashboard.py --prod          # production Worker, once Max approves its deploy
  python3 scripts/dashboard.py --days 7 --out /tmp/x.md

The stats key comes from $GCM_STATS_KEY, else /home/box/.secrets/gcm_stats_key. Uses only the standard library.
All data is anonymous: per-install random IDs, town level, no personal data (see public/privacy.html)."""
import argparse, datetime, json, os, sys, urllib.request
from zoneinfo import ZoneInfo

SUB = "maxgreenwald-assistant.workers.dev"
URLS = {"preview": f"https://gcm-analytics-preview.{SUB}", "production": f"https://gcm-analytics.{SUB}"}


def key():
    k = os.environ.get("GCM_STATS_KEY")
    if not k:
        try: k = open("/home/box/.secrets/gcm_stats_key").read().strip()
        except OSError: sys.exit("no stats key: set GCM_STATS_KEY or create /home/box/.secrets/gcm_stats_key")
    return k


def fetch(base, days):
    req = urllib.request.Request(f"{base}/stats?days={days}", headers={"x-stats-key": key(), "user-agent": "gcm-dashboard"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def table(rows, cols, empty="_none yet_"):
    if not rows: return empty + "\n"
    out = ["| " + " | ".join(h for h, _ in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows: out.append("| " + " | ".join(str(r.get(k) if r.get(k) not in (None, "") else "–") for _, k in cols) + " |")
    return "\n".join(out) + "\n"


def pct(a, b): return f"{100 * a / b:.0f}%" if b else "–"


def render(s, env, base, today):
    t, d = s.get("totals") or {}, s.get("daily") or []
    srch = sum(x.get("routes_searched") or 0 for x in d); found = sum(x.get("routes_found") or 0 for x in d)
    done = sum(x.get("routes_completed") or 0 for x in d)
    md = [f"# Golf Cart Maps analytics: {today}", ""]
    if env == "preview":
        md += ["> **PREVIEW DATA, NOT REAL USERS.** Source: the preview Worker (`gcm-analytics-preview`), which only gets events from",
               "> `*.golfcart-maps.pages.dev` preview builds (our own testing). Production analytics (golfcartmap.com, iOS, CarPlay) is",
               "> not deployed yet; it waits for Max's approval. Do not use these numbers for decisions or reports.", ""]
    md += [f"Source: `{base}/stats` · window: last {s.get('days')} days (days are UTC) · generated {s.get('generated')}", "",
           "## Headline", "",
           f"- Weekly active installs: **{s.get('weekly_active', 0)}** (route users: {s.get('weekly_active_route_users', 0)})",
           f"- {s.get('days')}-day installs: {t.get('installs') or 0} · sessions: {t.get('sessions') or 0} · events: {t.get('events') or 0}",
           f"- Routes searched: {srch} · found a legal route: {found} ({pct(found, srch)}) · completed: {done} ({pct(done, found)} of found)", "",
           "## Daily", "",
           table(d, [("day", "day"), ("active installs", "active_installs"), ("new installs", "new_installs"), ("sessions", "sessions"),
                     ("town views", "town_views"), ("routes searched", "routes_searched"), ("routes found", "routes_found"),
                     ("routes completed", "routes_completed"), ("road reports", "road_reports")]),
           "## Towns", "",
           table(s.get("towns"), [("town", "town"), ("installs", "installs"), ("views", "views"), ("routes searched", "routes_searched"),
                                  ("completed", "routes_completed"), ("road reports", "road_reports")]),
           "## Platforms", "",
           table(s.get("platforms"), [("platform", "platform"), ("PWA", "pwa"), ("installs", "installs"), ("sessions", "sessions")]),
           "## Acquisition (sessions by UTM)", "",
           table(s.get("sources"), [("utm_source", "utm_source"), ("utm_medium", "utm_medium"), ("utm_campaign", "utm_campaign"),
                                    ("sessions", "sessions"), ("installs", "installs")]),
           "## Referrers", "", table(s.get("referrers"), [("referrer host", "ref"), ("sessions", "sessions")]),
           "## First touch (how installs first arrived)", "", table(s.get("first_touch"), [("first-touch source", "ft_source"), ("installs", "installs")]),
           "## Events", "", table(merge_aliases(s.get("events")), [("event", "event"), ("count", "n"), ("installs", "installs")])]
    return "\n".join(md)


ALIASES = {"testflight_click": "app_store_click"}  # old badge event name; counted as the same metric


def merge_aliases(events):
    """Fold legacy event names into their current name (counts summed; installs summed as an upper bound)."""
    out = {}
    for r in events or []:
        name = ALIASES.get(r.get("event"), r.get("event"))
        o = out.setdefault(name, {"event": name, "n": 0, "installs": 0})
        o["n"] += r.get("n") or 0; o["installs"] += r.get("installs") or 0
    return sorted(out.values(), key=lambda r: -r["n"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prod", action="store_true"); ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out"); ap.add_argument("--url", help="override the Worker base URL")
    a = ap.parse_args()
    env = "production" if a.prod else "preview"; base = a.url or URLS[env]
    today = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    md = render(fetch(base, a.days), env, base, today)
    out = a.out or f"/workspace/gcm/dashboard/{today}.md"
    os.makedirs(os.path.dirname(out), exist_ok=True); open(out, "w").write(md)
    print(out)


if __name__ == "__main__":
    main()
