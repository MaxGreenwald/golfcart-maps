"""Service worker behaviour of a served build. URL=... python3 scripts/test_sw.py
- Built (dist/, stamped): the active cache is exactly the name in /sw.js (gcm-<hash>), app.js is precached,
  old caches are deleted, and the app still opens offline.
- Raw public/ (unstamped placeholder): the SW registers but caches nothing (cannot go stale)."""
import os, re, urllib.request
from playwright.sync_api import sync_playwright
B = os.environ.get('URL', 'http://localhost:8765/').rstrip('/')
res = []
def ok(n, c, x=''): res.append(bool(c)); print('PASS' if c else 'FAIL', n, x)
sw = urllib.request.urlopen(urllib.request.Request(B + '/sw.js', headers={'User-Agent': 'Mozilla/5.0 gcm-test_sw'})).read().decode()
name = re.search(r"const C='([^']*)'", sw).group(1)
stamped = '__' not in name
print('sw cache name:', name, '(stamped)' if stamped else '(unstamped public/)')
with sync_playwright() as p:
    b = p.chromium.launch(); c = b.new_context(viewport={'width': 390, 'height': 844}); pg = c.new_page()
    pg.goto(B + '/'); pg.wait_for_function('window.ready===true', timeout=60000)
    pg.wait_for_function('navigator.serviceWorker.controller!==null', timeout=30000)
    # simulate a phone that still has a cache from the old manual 'gcm-v40' SW, then a fresh SW install
    pg.evaluate("caches.open('gcm-v40').then(c=>c.put('/stale',new Response('old'))).then(()=>navigator.serviceWorker.getRegistrations()).then(rs=>Promise.all(rs.map(r=>r.unregister())))")
    pg.goto(B + '/'); pg.wait_for_function('window.ready===true', timeout=60000)
    pg.wait_for_function('navigator.serviceWorker.controller!==null', timeout=30000); pg.wait_for_timeout(2000)
    keys = pg.evaluate('caches.keys()')
    if stamped:
        ok('cache name is gcm-<12 hex>', re.fullmatch(r'gcm-[0-9a-f]{12}', name), name)
        ok('only the current cache is kept (old gcm-v40 deleted)', keys == [name], keys)
        ok('app.js is precached', pg.evaluate(f"caches.open('{name}').then(c=>c.match('app.js')).then(r=>!!r)"))
        ok('start page cached without a redirect (Cloudflare 308s /index.html; a redirected response breaks offline open)',
           pg.evaluate(f"caches.open('{name}').then(c=>c.match('./')).then(r=>!!r&&!r.redirected)"))
        c.set_offline(True); pg.goto(B + '/'); pg.wait_for_timeout(4000)
        ok('opens offline', pg.evaluate("!!document.getElementById('city')"))
        if 'localhost' not in B:  # city paths need Cloudflare's _redirects
            pg.goto(B + '/sandiego'); pg.wait_for_timeout(3000); ok('opens /sandiego offline', pg.evaluate("!!document.getElementById('city')"))
        c.set_offline(False)
    else:
        ok('unstamped SW caches nothing', keys == [], keys)
    b.close()
print('RESULT', 'ALL PASS' if all(res) else 'FAIL')
raise SystemExit(0 if all(res) else 1)
