"""Offline city download (public/offline.js). URL=... python3 scripts/test_offline.py against a built dist/.
Download San Diego, go offline, reload /map: roads still draw, a route still computes, the page is marked offline.
Online, data still comes from the network (no X-GCM-Offline header), and a changed live stamp triggers a re-download."""
import os
from playwright.sync_api import sync_playwright
from _check import ck, finish
B = os.environ.get('URL', 'http://localhost:8765/').rstrip('/')
M = os.environ.get('MAP', '/map')
with sync_playwright() as p:
    b = p.chromium.launch(); c = b.new_context(viewport={'width': 390, 'height': 844}); pg = c.new_page()
    pg.goto(B + M); pg.wait_for_function('window.ready===true', timeout=60000)
    pg.wait_for_function('navigator.serviceWorker.controller!==null', timeout=30000)
    pg.wait_for_timeout(1500)
    ck('download button shows size', 'MB' in pg.inner_text('#cOff'), pg.inner_text('#cOff'))
    meta = pg.evaluate("GCMOffline.download('sd')")
    ck('download saved every tile', meta['files'] > 20 and meta['bytes'] > 1_000_000, meta)
    pg.evaluate('paintOffline()'); pg.wait_for_timeout(800)
    ck('downloaded indicator', 'downloaded' in pg.inner_text('#cOff'), pg.inner_text('#cOff'))
    ck('download date shown', 'Saved ' in pg.inner_text('#offNote'), pg.inner_text('#offNote'))
    hdr = pg.evaluate("fetch('data/sd/index.json').then(r=>r.headers.get('X-GCM-Offline'))")
    ck('online still reads the network first (no offline header)', hdr is None, hdr)
    c.set_offline(True)
    pg.goto(B + M); pg.wait_for_function('window.ready===true', timeout=60000)
    pg.evaluate("map.setView([32.84,-117.276],15);0"); pg.wait_for_timeout(4000)
    ck('roads draw offline', pg.evaluate('D.segs.length') > 1000, pg.evaluate('D.segs.length'))
    pg.evaluate("map.fire('click',{latlng:L.latLng(32.8506,-117.2717)});0"); pg.evaluate("map.fire('click',{latlng:L.latLng(32.8305,-117.2805)});0")
    pg.wait_for_timeout(4000)
    s = pg.evaluate('getState()'); ck('route computes offline', s['routed'], s)
    ck('page marked offline (plain background)', pg.evaluate("document.documentElement.classList.contains('gcm-offline')"))
    c.set_offline(False)
    pg.evaluate("(()=>{const m=JSON.parse(localStorage.getItem('gcm-offline-meta'));m.sd.stamp='old';localStorage.setItem('gcm-offline-meta',JSON.stringify(m))})()")
    ch = pg.evaluate('GCMOffline.refreshAll()')
    ck('changed live data re-downloads the city', ch == ['sd'], ch)
    pg.evaluate("GCMOffline.remove('sd')")
    ck('delete removes the copy', pg.evaluate("caches.has('gcm-offline-sd').then(x=>!x&&!GCMOffline.isDownloaded('sd'))"))
    b.close()
finish()
