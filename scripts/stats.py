#!/usr/bin/env python3
"""Print a text usage report from /api/stats. Usage: scripts/stats.py [days] (BASE env overrides the site URL)."""
import json, os, sys, urllib.request
base = os.environ.get('BASE', 'https://golfcartmap.com').rstrip('/')
key = open(os.path.expanduser(os.environ.get('KEYFILE', '/home/box/.secrets/gcm_stats_key'))).read().strip()
days = sys.argv[1] if len(sys.argv) > 1 else '30'
req = urllib.request.Request(f'{base}/api/stats?days={days}', headers={'x-stats-key': key, 'User-Agent': 'gcm-stats'})
s = json.load(urllib.request.urlopen(req, timeout=30))
if 'error' in s: sys.exit('error: ' + s['error'])
pct = lambda x: '—' if x is None else f'{x*100:.0f}%'
t = s['totals']
print(f"Golf Cart Map usage, last {s['days']} days ({base})")
print(f"  users {t['users']} · sessions {t['sessions']} · events {t['events']}")
r = s['routes']; print(f"  routes planned {r['planned']} · failed {r['failed']} · success {pct(r['success_rate'])}")
p = s['pwa']; print(f"  home-screen app {p['pwa_users']} users · browser {p['browser_users']} · PWA share {pct(p['pwa_share'])}")
print('\nDaily (UTC):'); [print(f"  {d['day']}  users {d['users']:>4}  sessions {d['sessions']:>4}  events {d['events']:>5}") for d in s['daily'][:14]]
print('\nEvents:'); [print(f"  {e['event']:<24}{e['n']:>6}  ({e['users']} users)") for e in s['events']]
print('\nTop regions:'); [print(f"  {x['region']:<14} users {x['users']:>4}  routes {x['routes']}") for x in s['top_regions']]
print('\nPaywall funnel (users):'); [print(f"  {x['step']:<26}{x['users']}") for x in s['paywall_funnel']]
print(f"  restores {s['restores']}")
print('\nDevices: ' + ', '.join(f"{d['device']} {d['users']}" for d in s['devices']))
print('Countries: ' + ', '.join(f"{c['country']} {c['users']}" for c in s['countries']))
print('Opened via: ' + ', '.join(f"{c['source']} {c['n']}" for c in s['open_sources']))
