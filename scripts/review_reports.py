#!/usr/bin/env python3
"""Review queue for in-app road/hazard reports (gcm-reports Worker). Reviewing never edits map data: a confirmed
speed/allow/block report is fixed by hand in scripts/overrides.py with a source; only closures/hazards can get a
temporary routing avoid (max 14 days).
  scripts/review_reports.py list [pending|accepted|rejected|fixed]   [--prod]
  scripts/review_reports.py accept ID [--avoid-days N] [--note TEXT]  [--prod]
  scripts/review_reports.py reject ID [--note TEXT]                   [--prod]
  scripts/review_reports.py fixed ID [--note TEXT]                    [--prod]
Key: /home/box/.secrets/gcm_reports_review_key (preview). Default target is gcm-reports-preview."""
import json,sys,urllib.request,argparse,datetime
p=argparse.ArgumentParser();p.add_argument('cmd');p.add_argument('arg',nargs='?');p.add_argument('--avoid-days',type=float);p.add_argument('--note');p.add_argument('--prod',action='store_true');a=p.parse_args()
base='https://gcm-reports%s.maxgreenwald-assistant.workers.dev'%('' if a.prod else '-preview')
key=open('/home/box/.secrets/gcm_reports_review_key'+('_prod' if a.prod else '')).read().strip()
def call(path,body=None):
  r=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'x-review-key':key,'content-type':'application/json','user-agent':'gcm-review'},method='POST' if body is not None else 'GET')
  with urllib.request.urlopen(r,timeout=20) as f:return json.load(f)
if a.cmd=='list':
  for x in call('/queue'+('?status='+a.arg if a.arg else '')):
    t=datetime.datetime.fromtimestamp(x['ts']/1000).strftime('%b %d %I:%M %p ET')
    print(f"{x['id']}  {t}  {x['status']:<8} {x['issue']:<11} {x['region'] or '?'}  {x['road']}  ({x['lat']},{x['lon']})  speed={x['speed']}  {x['notes'][:80]!r}")
elif a.cmd in ('accept','reject','fixed'):
  d={'id':a.arg,'status':{'accept':'accepted','reject':'rejected','fixed':'fixed'}[a.cmd],'note':a.note}
  if a.avoid_days is not None:d['avoid_days']=a.avoid_days
  print(json.dumps(call('/review',d),indent=1))
else:sys.exit(__doc__)
