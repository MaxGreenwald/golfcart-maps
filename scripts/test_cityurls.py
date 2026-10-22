import os
from playwright.sync_api import sync_playwright
B=os.environ.get('URL','https://city-urls.golfcart-maps.pages.dev').rstrip('/');S=os.environ.get('SHOTS','/workspace/gcm-cityurls/shots').rstrip('/')+'/';os.makedirs(S,exist_ok=True)
M=os.environ.get('MAP','/map')   # the map lives at /map/<slug>; plain /<slug> is the static SEO city page (MAP='' for raw public/)
res=[]
def ok(n,c,x=''):res.append(c);print('PASS' if c else 'FAIL',n,x)
with sync_playwright() as p:
  b=p.chromium.launch();c=b.new_context(viewport={'width':1366,'height':900});pg=c.new_page()
  def go(path):pg.goto(B+path);pg.wait_for_function('window.ready===true&&window.REG',timeout=60000);pg.wait_for_timeout(2500)
  go(M+'/naples');ok('/naples selects naples',pg.evaluate('REG.id')=='naples',pg.evaluate('location.pathname'));pg.screenshot(path=S+'cityurl_naples.png')
  go(M+'/tybee');ok('/tybee selects tybee',pg.evaluate('REG.id')=='tybee');pg.screenshot(path=S+'cityurl_tybee.png')
  pg.select_option('#city','galveston');pg.wait_for_timeout(3000)
  ok('picker pushes /galveston',pg.evaluate('location.pathname')==M+'/galveston')
  pg.go_back();pg.wait_for_timeout(3000);ok('back -> tybee',pg.evaluate('REG.id')=='tybee'and pg.evaluate('location.pathname')==M+'/tybee')
  go(M or '/');ok('map root -> slug url',pg.evaluate('location.pathname')==M+'/'+{'sd':'sandiego'}.get(pg.evaluate('REG.id'),pg.evaluate('REG.id')),pg.evaluate('location.pathname'))
  go(M+'/sandiego');ok('/sandiego',pg.evaluate('REG.id')=='sd')
  # offline navigation via SW
  pg.wait_for_function('navigator.serviceWorker.controller!==null',timeout=30000);pg.wait_for_timeout(1500)
  c.set_offline(True);pg.goto(B+M+'/naples');pg.wait_for_timeout(4000)
  ok('offline '+M+'/naples serves app',pg.evaluate("!!document.getElementById('city')"),pg.evaluate('typeof REG!=="undefined"&&REG?REG.id:null'));pg.screenshot(path=S+'cityurl_offline_naples.png')
  if M:
    c.set_offline(False);pg.goto(B+'/naples');ok('/naples is the static city page with a map button',pg.locator('a.cta').count()>0 and pg.locator('#city').count()==0,pg.title())
  b.close()
print('RESULT','ALL PASS' if all(res) else 'FAIL')
