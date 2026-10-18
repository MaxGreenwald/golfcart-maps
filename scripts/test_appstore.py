"""App Store review guards for the iOS build, run against the built dist/ with a simulated Capacitor iOS bridge.
- 3.1.1: no Stripe paywall, restore or Venmo tip link inside the iOS app.
- 2.2: no visible "beta" labels inside the iOS app.
- 4.2: native share sheet and haptics are wired (calls reach the Share/Haptics plugins).
- Offline launch: the app needs nothing from third-party hosts to start (Leaflet is bundled, not loaded from unpkg).
- The website (no Capacitor) is unchanged: Venmo link, chargers chip and beta badge still show there.
Usage: URL=http://localhost:8765/ python scripts/test_appstore.py"""
import os, re, sys
from playwright.sync_api import sync_playwright
U = os.environ.get('URL', 'http://localhost:8765/').rstrip('/') + '/'
STUB = """window.__calls=[];window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios',Plugins:{
 Haptics:{impact:o=>{__calls.push(['Haptics.impact',o]);return Promise.resolve()},notification:o=>{__calls.push(['Haptics.notification',o]);return Promise.resolve()}},
 Share:{share:o=>{__calls.push(['Share.share',o]);return Promise.resolve({})}}}};"""
A, B = [28.9478, -81.9573], [28.9093, -81.9715]   # The Villages: Spanish Springs -> Lake Sumter Landing
ok = True
def check(name, cond, extra=''):
    global ok; ok &= bool(cond); print('PASS' if cond else 'FAIL', name, extra)
def vis(pg, sel): return pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}');return !!(e&&e.offsetParent!==null&&getComputedStyle(e).display!=='none')}})()")
with sync_playwright() as p:
    b = p.chromium.launch()
    # --- simulated iOS app, offline from every third-party host ---
    c = b.new_context(viewport={'width': 440, 'height': 956}, device_scale_factor=1)
    c.add_init_script(STUB)
    ext = []
    def block(route):
        if not route.request.url.startswith(U): ext.append(route.request.url); return route.abort()
        return route.continue_()
    c.route('**/*', block)
    pg = c.new_page(); pg.goto(U + '?r=villages')
    pg.wait_for_function('window.ready===true&&window.REG', timeout=60000); pg.wait_for_timeout(800)
    check('iOS: Leaflet loads with third-party hosts blocked', pg.evaluate('!!window.L&&!!window.map'))
    check('iOS: no unpkg request', not any('unpkg' in u for u in ext), str([u for u in ext if 'unpkg' in u][:2]))
    check('iOS: Venmo tip link hidden', not vis(pg, '#tip'))
    check('iOS: chargers (paywalled) chip hidden', not vis(pg, '#cChg'))
    check('iOS: beta badge hidden', not vis(pg, '#cityBeta'))
    opts = pg.eval_on_selector_all('#city option', 'o=>o.map(x=>x.text)')
    check('iOS: no "(beta)" in area picker', not any('beta' in t.lower() for t in opts))
    pg.evaluate("window.PAY&&PAY.sheet()")
    check('iOS: paywall sheet never opens', pg.locator('#paySheet').count() == 0)
    r = pg.evaluate(f'testRoute({A},{B})')
    check('iOS: route found', r and r.get('mi', 0) > 0, str(r))
    pg.evaluate("setMenu(true)"); pg.wait_for_timeout(300)
    txt = pg.inner_text('body')
    check('iOS: no visible "beta" text', not re.search(r'\bbeta\b', txt, re.I), str(re.findall(r'.{30}\bbeta\b.{30}', txt, re.I)[:2]))
    check('iOS: no visible Venmo/Stripe/$ price', not re.search(r'venmo|stripe|\$\d', txt, re.I))
    check('iOS: haptic fired on route', any(k.startswith('Haptics.') for k, _ in pg.evaluate('__calls')))
    check('iOS: Share button visible after route', vis(pg, '#share'))
    pg.click('#share'); pg.wait_for_timeout(300)
    sh = [o for k, o in pg.evaluate('__calls') if k == 'Share.share']
    check('iOS: Share opens native share sheet with town link', sh and sh[0]['url'] == 'https://golfcartmap.com/villages' and 'min' in sh[0]['text'], str(sh[:1]))
    c.close()
    # --- website: unchanged ---
    c = b.new_context(viewport={'width': 440, 'height': 956})
    pg = c.new_page(); pg.goto(U + '?r=villages')
    pg.wait_for_function('window.ready===true&&window.REG', timeout=60000); pg.wait_for_timeout(800)
    check('web: Venmo tip link still present', pg.locator('#tip').count() == 1)
    pg.evaluate("setMenu(true)"); pg.wait_for_timeout(300)
    check('web: chargers chip still shown', vis(pg, '#cChg'))
    check('web: beta badge still shown', vis(pg, '#cityBeta'))
    check('web: native helpers report web', pg.evaluate('window.GCM_IOS===false&&window.GCM_NATIVE===false'))
    c.close(); b.close()
print('RESULT', 'ALL PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
