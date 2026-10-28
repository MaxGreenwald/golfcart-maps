import os
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','http://localhost:8765/').rstrip('/');S=os.environ.get('SHOTS','/workspace/gcm-cityurls/shots/')
ok=True
with sync_playwright() as p:
  b=p.chromium.launch()
  for w,h in [(390,844),(375,667)]:
    c=b.new_context(viewport={'width':w,'height':h},device_scale_factor=2,has_touch=True,is_mobile=True)
    for slug,id in [('sandiego','sd'),('coachella','coachella'),('charleston','chs')]:
      pg=c.new_page();pg.goto(U+('/?r='+id if 'localhost' in U else '/map/'+slug));pg.wait_for_function('window.ready===true&&window.REG',timeout=60000);pg.wait_for_timeout(1500)
      r=pg.evaluate("""()=>{const ch=[...document.querySelectorAll('#chips>*')].filter(e=>e.offsetParent);const R=ch.map(e=>e.getBoundingClientRect());return {right:Math.max(...R.map(x=>x.right)),rows:new Set(R.map(x=>Math.round(x.top))).size,vw:innerWidth,city:document.querySelector('#city').getBoundingClientRect().width,txt:document.querySelector('#city').selectedOptions[0].text,ids:ch.map(e=>e.id||e.className)}}""")
      good=r['right']<=r['vw']-8 and r['rows']==1;ok&=good
      print('PASS' if good else 'FAIL',w,h,slug,r)
      if id!='charleston':pg.screenshot(path=S+f'chips_{w}_{slug}.png')
      pg.close()
    c.close()
  b.close()
print('RESULT','ALL PASS' if ok else 'FAIL')
import sys as _sys; _sys.exit(0 if ok else 1)
