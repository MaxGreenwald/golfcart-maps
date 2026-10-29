"""Native app loads towns from https://golfcartmap.com; the website keeps bundled files.

Simulates Capacitor iOS (the same bridge test_appstore.py uses) against a local map.
The live origin is intercepted: its region list is the bundled list plus Live Town, which
is not in public/data/regions.json. CarPlay's status() reads that same list.

Usage: URL=http://localhost:8765/map/ python scripts/test_live_regions.py
"""
import json, os
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from _check import ck, fail, finish

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
U = os.environ.get('URL', 'http://localhost:8765/map/').rstrip('/') + '/'
SHOTS = os.environ.get('SHOTS') or os.environ.get('SHOTS_DIR') or ''
STUB = "window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios',Plugins:{}};"
HDR = {'content-type': 'application/json', 'access-control-allow-origin': '*'}
LIVE_REGION = {
    'id': 'livetown', 'name': 'Live Town', 'short': 'Live Town', 'state': 'FL',
    'center': [26.05, -81.95], 'zoom': 16, 'bbox': [26.0, -82.1, 26.1, -81.9],
}
LIVE_INDEX = {
    'meta': {
        'bbox': [26.0, -82.1, 26.1, -81.9], 'generated': '2026-10-29', 'ways': 1, 'segments': 1,
        'stats': {}, 'region': 'livetown', 'tileSize': 0.1, 'tiles': ['-820_260'], 'xnodes': [],
    },
    'names': ['Live Town Road'], 'sources': [],
}
LIVE_TILE = [[0, 'residential', 25, 'i', 0, 0, 1, [[-81.95, 26.05], [-81.949, 26.051]]]]
BUNDLED = json.load(open(os.path.join(ROOT, 'public', 'data', 'regions.json'), encoding='utf-8'))
LIVE_REGIONS = BUNDLED + [LIVE_REGION]


def shot(pg, name):
    if not SHOTS:
        return
    os.makedirs(SHOTS, exist_ok=True)
    pg.screenshot(path=os.path.join(SHOTS, name))


def fulfill_json(route, obj, status=200):
    route.fulfill(status=status, body=json.dumps(obj), headers=HDR)


def fulfill_file(route, path):
    with open(path, 'rb') as handle:
        route.fulfill(status=200, body=handle.read(), headers=HDR)


def handle(route, state):
    url = route.request.url
    if state['down']:
        state['aborted'].append(url)
        route.abort()
        return
    state['hits'].append(url)
    path = urlparse(url).path
    if path == '/data/schema.json':
        fulfill_json(route, {'schema': state['schema'], 'note': 'test'})
        return
    if path == '/data/regions.json':
        fulfill_json(route, state['regions'])
        return
    if path == '/data/livetown/index.json':
        fulfill_json(route, LIVE_INDEX)
        return
    if path == '/data/livetown/tiles/-820_260.json':
        fulfill_json(route, LIVE_TILE)
        return
    if path.startswith('/data/livetown/'):
        fulfill_json(route, {}, 404)
        return
    local = os.path.join(ROOT, 'public', path.lstrip('/'))
    if os.path.isfile(local):
        fulfill_file(route, local)
        return
    fulfill_json(route, {}, 404)


def watch(pg):
    pg.on('pageerror', lambda err: fail('js error', str(err)))


def open_native(browser, state):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
    ctx.add_init_script(STUB)
    ctx.route('https://golfcartmap.com/**', lambda route: handle(route, state))
    pg = ctx.new_page()
    watch(pg)
    return ctx, pg


def picker(pg):
    return pg.eval_on_selector_all('#city option', 'nodes => nodes.map(n => n.value)')


def run(browser):
    ck('bundle has no Live Town', all(r['id'] != 'livetown' for r in BUNDLED), str(len(BUNDLED)))

    state = {'down': False, 'schema': 1, 'regions': LIVE_REGIONS, 'hits': [], 'aborted': []}
    ctx, pg = open_native(browser, state)
    pg.goto(U + '?r=livetown')
    pg.wait_for_function("window.ready===true && window.REG && window.REG.id==='livetown'", timeout=60000)
    pg.wait_for_function("document.getElementById('cityLbl').textContent==='Live Town'", timeout=10000)
    opts = picker(pg)
    mode = pg.evaluate('window.GCMLiveData && window.GCMLiveData.mode')
    st = pg.evaluate('GCMCarPlay.status()')
    ov = pg.evaluate('GCMCarPlay.overlay(26.0,-82.1,26.1,-81.9,20)')
    roads = len((ov or {}).get('ok') or []) + len((ov or {}).get('bad') or [])
    ck('app mode prefers the live region list', 'livetown' in opts, ','.join(opts[-3:]))
    ck('app mode opens the live-only town', pg.evaluate('REG.id') == 'livetown' and pg.inner_text('#cityLbl') == 'Live Town')
    ck('loader mode is live', mode == 'live', mode)
    ck('CarPlay lists the live-only town', any(r.get('id') == 'livetown' for r in (st or {}).get('regions') or []), (st or {}).get('region'))
    ck('CarPlay current region is the live town', (st or {}).get('region') == 'livetown')
    ck('live origin served the new town index', any(u.endswith('/data/livetown/index.json') for u in state['hits']))
    ck('live origin served the new town road tile', any(u.endswith('/data/livetown/tiles/-820_260.json') for u in state['hits']))
    ck('live road geometry is on the map', roads >= 1, roads)
    print('EVIDENCE app-mode picker has livetown', 'livetown' in opts, 'mode', mode, 'region', pg.evaluate('REG.id'))
    print('EVIDENCE carplay', (st or {}).get('region'), 'towns', len((st or {}).get('regions') or []))
    print('EVIDENCE live paths', sorted({urlparse(u).path for u in state['hits'] if 'livetown' in u or u.endswith('schema.json') or u.endswith('regions.json')}))
    shot(pg, 'live-town-app-mode.png')
    keys = pg.evaluate("caches.open('gcm-live-data-s1').then(c => c.keys()).then(ks => ks.map(k => k.url))")
    print('EVIDENCE cache keys before reload', keys)

    # The phone app does not rewrite the URL (capacitor://). A fresh open with no ?r= uses the
    # saved town, which only resolves when the cached region list still contains it.
    seen = len(state['hits'])
    state['down'] = True
    pg.goto(U)
    pg.wait_for_function("window.ready===true && window.REG && window.REG.id==='livetown'", timeout=60000)
    cached = pg.evaluate('window.GCMLiveData && window.GCMLiveData.mode')
    ck('offline after first fetch still shows the live town', pg.evaluate('REG.id') == 'livetown' and 'livetown' in picker(pg))
    ck('offline reload uses the cache', cached == 'cache', cached)
    ck('offline reload does not use the live origin', len(state['aborted']) > 0 and len(state['hits']) == seen, str(len(state['aborted'])))
    print('EVIDENCE offline reload region', pg.evaluate('REG.id'), 'mode', cached, 'aborted', len(state['aborted']))
    shot(pg, 'live-town-offline-cache.png')
    ctx.close()

    mismatch = {'down': False, 'schema': 99, 'regions': LIVE_REGIONS, 'hits': [], 'aborted': []}
    ctx, pg = open_native(browser, mismatch)
    pg.goto(U + '?r=putinbay')
    pg.wait_for_function("window.ready===true && window.REG && window.REG.id==='putinbay'", timeout=60000)
    mm = pg.evaluate('window.GCMLiveData && window.GCMLiveData.mode')
    ck('schema mismatch falls back to the bundle', mm == 'mismatch', mm)
    ck('schema mismatch hides the live-only town', 'livetown' not in picker(pg))
    ck('schema mismatch does not apply the live region list', not any(u.endswith('/data/regions.json') for u in mismatch['hits']))
    print('EVIDENCE schema mismatch mode', mm, 'region', pg.evaluate('REG.id'), 'live list fetched', any(u.endswith('/data/regions.json') for u in mismatch['hits']))
    ctx.close()

    down = {'down': True, 'schema': 1, 'regions': LIVE_REGIONS, 'hits': [], 'aborted': []}
    ctx, pg = open_native(browser, down)
    pg.goto(U + '?r=putinbay')
    pg.wait_for_function("window.ready===true && window.REG && window.REG.id==='putinbay'", timeout=60000)
    dm = pg.evaluate('window.GCMLiveData && window.GCMLiveData.mode')
    ck('network failure falls back to the bundle', dm == 'bundled', dm)
    ck('network failure hides the live-only town', 'livetown' not in picker(pg))
    ck('network failure still opens a bundled town', pg.evaluate('REG.id') == 'putinbay')
    print('EVIDENCE network down mode', dm, 'region', pg.evaluate('REG.id'), 'aborted', len(down['aborted']))
    ctx.close()

    web_state = {'down': False, 'schema': 1, 'regions': LIVE_REGIONS, 'hits': [], 'aborted': []}
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
    ctx.route('https://golfcartmap.com/**', lambda route: handle(route, web_state))
    pg = ctx.new_page()
    watch(pg)
    pg.goto(U + '?r=putinbay')
    pg.wait_for_function("window.ready===true && window.REG && window.REG.id==='putinbay'", timeout=60000)
    ck('website does not install the live loader', pg.evaluate('!window.GCMLiveData && window.GCM_NATIVE===false'))
    ck('website does not request the live origin', len(web_state['hits']) == 0, str(len(web_state['hits'])))
    ck('website picker has no live-only town', 'livetown' not in picker(pg))
    print('EVIDENCE website live requests', len(web_state['hits']), 'region', pg.evaluate('REG.id'))
    ctx.close()


with sync_playwright() as p:
    try:
        run(p.chromium.launch())
    except Exception as exc:
        fail('live regions run', repr(exc))
finish()
