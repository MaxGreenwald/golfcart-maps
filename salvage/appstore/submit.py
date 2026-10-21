#!/usr/bin/env python3
"""Attach the newest VALID build to App Store version 1.0 and (with --submit) send it to App Review.
  /workspace/ascapi/.venv/bin/python /workspace/gcm-appstore/submit.py               # check + attach build only
  /workspace/ascapi/.venv/bin/python /workspace/gcm-appstore/submit.py --build 16    # pin a build number
  /workspace/ascapi/.venv/bin/python /workspace/gcm-appstore/submit.py --submit      # ...then submit for review
Only run --submit after the App Privacy answers are published in the App Store Connect website (no public API exists)."""
import sys, json, argparse
sys.path.insert(0, '/workspace/ascapi'); from asc import call
APP, V = '6823958385', '5eff07f6-75c3-474d-bef7-d0c12a17e21d'
ap = argparse.ArgumentParser(); ap.add_argument('--build'); ap.add_argument('--min-build', type=int, default=16); ap.add_argument('--submit', action='store_true'); a = ap.parse_args()
def ok(s, j, what):
    if s >= 300: sys.exit(f'{what} failed {s}: {json.dumps(j)[:800]}')
    return j
j = ok(*call('GET', f'/v1/builds?filter[app]={APP}&sort=-uploadedDate&limit=10&fields[builds]=version,processingState,expired,usesNonExemptEncryption'), 'list builds')
bs = [b for b in j['data'] if b['attributes']['processingState'] == 'VALID' and not b['attributes']['expired']]
b = next((x for x in bs if x['attributes']['version'] == a.build), None) if a.build else next((x for x in bs if int(x['attributes']['version']) >= a.min_build), None)
if not b: sys.exit(f'no VALID build {a.build or ">= %d" % a.min_build} yet: ' + str([(x["attributes"]["version"], x["attributes"]["processingState"]) for x in j["data"]]))
print('build', b['attributes']['version'], b['id'], 'encryption', b['attributes']['usesNonExemptEncryption'])
if b['attributes']['usesNonExemptEncryption'] is None:
    ok(*call('PATCH', f'/v1/builds/{b["id"]}', {'data': {'type': 'builds', 'id': b['id'], 'attributes': {'usesNonExemptEncryption': False}}}), 'export compliance')
ok(*call('PATCH', f'/v1/appStoreVersions/{V}/relationships/build', {'data': {'type': 'builds', 'id': b['id']}}), 'attach build')
s, j = call('GET', f'/v1/appStoreVersions/{V}/build'); print('attached:', j['data']['attributes']['version'] if j.get('data') else None)
if not a.submit: print('not submitted (pass --submit after App Privacy is published)'); sys.exit(0)
j = ok(*call('POST', '/v1/reviewSubmissions', {'data': {'type': 'reviewSubmissions', 'attributes': {'platform': 'IOS'}, 'relationships': {'app': {'data': {'type': 'apps', 'id': APP}}}}}), 'create review submission')
rs = j['data']['id']; print('reviewSubmission', rs)
ok(*call('POST', '/v1/reviewSubmissionItems', {'data': {'type': 'reviewSubmissionItems', 'relationships': {'reviewSubmission': {'data': {'type': 'reviewSubmissions', 'id': rs}}, 'appStoreVersion': {'data': {'type': 'appStoreVersions', 'id': V}}}}}), 'add version to submission')
j = ok(*call('PATCH', f'/v1/reviewSubmissions/{rs}', {'data': {'type': 'reviewSubmissions', 'id': rs, 'attributes': {'submitted': True}}}), 'submit')
print('SUBMITTED', j['data']['attributes'])
