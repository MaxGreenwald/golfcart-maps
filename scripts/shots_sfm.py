import os
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','http://localhost:8765/').rstrip('/');S='/workspace/gcm-cityurls/shots/'
loc='localhost' in U
def url(slug,id):return U+('/?r='+id if loc else '/'+slug)
with sync_playwright() as p:
  b=p.chromium.launch();c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True);pg=c.new_page()
  pg.goto(url('sandiego','sd'));pg.wait_for_function('window.ready===true',timeout=60000);pg.wait_for_timeout(2000)
  print('idle useme',pg.is_visible('#useme'),'chg in chips',pg.locator('#chips #cChg').count());pg.screenshot(path=S+'sfm_idle.png')
  pg.click('#cSet');pg.wait_for_timeout(500);print('settings',pg.is_visible('#setPanel'),pg.is_visible('#cChg'),pg.inner_text('#rnote')[:60]);pg.screenshot(path=S+'sfm_settings.png')
  pg.mouse.click(250,600);pg.wait_for_timeout(400);print('closed',not pg.is_visible('#setPanel'))
  pg.focus('#qf');pg.wait_for_timeout(500);print('planning useme',pg.is_visible('#useme'),pg.inner_text('#useme'));pg.screenshot(path=S+'sfm_planning.png')
  pg.evaluate("document.activeElement.blur()")
  for w,h in [(390,844),(375,667)]:
    q=b.new_context(viewport={'width':w,'height':h},device_scale_factor=2,has_touch=True,is_mobile=True).new_page();q.goto(url('sandiego','sd'));q.wait_for_function('window.ready===true',timeout=60000);q.wait_for_timeout(1000)
    q.click('#cRisk');q.wait_for_timeout(400);bx=q.locator('#riskWarn .rcard').bounding_box();print('warn shown',q.is_visible('#riskWarn'),'fits',bx['y']>=0 and bx['y']+bx['height']<=h,'risky on',q.evaluate('risky'));q.screenshot(path=S+f'risky_warn_{w}.png')
    q.click('#riskWarn .rok');q.wait_for_timeout(300);print('after ok risky',q.evaluate('risky'),'ack',q.evaluate("localStorage.getItem('gcm-risky-ack')"))
    q.click('#cNorm');q.click('#cRisk');q.wait_for_timeout(300);print('second tap no warn',q.locator('#riskWarn').count()==0)
    q.click('#cSet');q.click('#whatRisky');q.wait_for_timeout(300);print('whatRisky reopens',q.is_visible('#riskWarn'))
  pg.goto(url('naples','naples'));pg.wait_for_function('window.ready===true',timeout=60000);pg.wait_for_timeout(1500);pg.evaluate("map.setView([26.17,-81.77],15)");pg.wait_for_timeout(2500);pg.screenshot(path=S+'sfm_naples_dashed.png')
  for w,h in [(390,844),(375,667)]:
    c2=b.new_context(viewport={'width':w,'height':h},device_scale_factor=2,has_touch=True,is_mobile=True)
    for slug,id in [('sandiego','sd'),('coachella','coachella'),('charleston','chs')]:
      q=c2.new_page();q.goto(url(slug,id));q.wait_for_function('window.ready===true',timeout=60000);q.wait_for_timeout(1500)
      r=q.evaluate("()=>{const R=[...document.querySelectorAll('#chips>*')].filter(e=>e.offsetParent).map(e=>e.getBoundingClientRect());return [Math.max(...R.map(x=>x.right)),new Set(R.map(x=>Math.round(x.top))).size,document.querySelector('#city').selectedOptions[0].text]}")
      print('PASS' if r[0]<=w-8 and r[1]==1 else 'FAIL',w,slug,r);q.screenshot(path=S+f'chips_{w}_{slug}.png');q.close()
    c2.close()
  b.close()
