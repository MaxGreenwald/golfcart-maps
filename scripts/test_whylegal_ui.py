# UI test: road popup has a "Why it's OK" box (rule, statute, source, data date); live strip shows during a route with GPS.
import os,sys
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','http://localhost:8765/');fails=[]
def ck(n,c,x=''):print(('PASS ' if c else 'FAIL ')+n,'' if c else x);c or fails.append(n)
with sync_playwright() as p:
  b=p.chromium.launch();c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True,geolocation={'latitude':32.7976,'longitude':-117.2531},permissions=['geolocation'])
  c.add_init_script("localStorage.setItem('gcm-notrack','1')");pg=c.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
  pg.goto(U+'?lat=32.7976&lon=-117.2531&z=17');pg.wait_for_function('window.ready===true',timeout=60000);pg.wait_for_timeout(1500)
  # open the popup of a known allowed segment programmatically through Leaflet (click on its line)
  pg.evaluate("""(()=>{const segs=[];map.eachLayer(l=>{if(l instanceof L.Polyline&&l.listens&&l.listens('click')&&!l._popup)segs.push(l)});const l=segs.find(l=>l.options.color==='#12a150');const ll=l.getLatLngs()[0];l.fire('click',{latlng:ll,originalEvent:{}})})()""")
  pg.wait_for_timeout(500);html=pg.inner_html('.leaflet-popup-content')
  ck('popup has why box',"Why it’s OK" in html,html[:300])
  pg.click('.whyd summary');pg.wait_for_timeout(300)
  t=pg.inner_text('.leaflet-popup-content')
  ck('rule + statute',"35 mph or less" in t and 'CVC 21260' in t,t)
  ck('speed source',"Speed source:" in t,t)
  ck('data date shown, no invented verified date','Map data updated 2026-' in t and 'Last verified' not in t,t)
  if os.environ.get('SHOT'):pg.screenshot(path='shots/why-popup.png')
  r=pg.evaluate("testRoute([32.7976,-117.2531],[32.8090,-117.2580])");ck('route ok',bool(r),r)
  pg.evaluate("whyNow(L.latLng(32.7976,-117.2531))");pg.wait_for_timeout(200)
  w=pg.inner_text('#whynow') if pg.is_visible('#whynow') else ''
  ck('live why strip on route',"Why it's OK" in w or 'Why it' in w,w)
  pg.evaluate("resetRoute()");ck('strip hides after reset',not pg.is_visible('#whynow'))
  ck('no page errors',not errs,errs)
  b.close()
print('RESULT','ALL PASS' if not fails else 'FAIL '+str(fails));sys.exit(1 if fails else 0)
