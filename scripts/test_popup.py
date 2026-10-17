import os
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','http://localhost:8765/');S='/workspace/gcm-cityurls/shots/'
with sync_playwright() as p:
  b=p.chromium.launch();c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True);pg=c.new_page()
  pg.goto(U);pg.wait_for_function('window.ready===true',timeout=60000);pg.wait_for_timeout(2000)
  pg.evaluate("snapTo&&snapTo('collapsed')") if pg.evaluate("typeof snapTo==='function'") else None
  pg.wait_for_timeout(600)
  tb=pg.evaluate("document.getElementById('top').getBoundingClientRect().bottom")
  # find a road pixel just below the top UI by trying taps
  hit=None
  for y in range(int(tb)+8,int(tb)+120,8):
    for x in range(40,360,12):
      pg.mouse.click(x,y);pg.wait_for_timeout(250)
      if pg.locator('.leaflet-popup').count():hit=(x,y);break
    if hit:break
  pg.wait_for_timeout(800)
  r=pg.evaluate("(()=>{const p=document.querySelector('.leaflet-popup');return p?p.getBoundingClientRect().top:null})()")
  sh=pg.evaluate("document.getElementById('sheet').getBoundingClientRect().top")
  pb=pg.evaluate("(()=>{const p=document.querySelector('.leaflet-popup');return p?p.getBoundingClientRect().bottom:null})()")
  print('tap',hit,'topUI',tb,'popup',r,pb,'sheetTop',sh)
  print('PASS' if r and r>=tb and pb<=sh+1 else 'FAIL')
  pg.screenshot(path=S+'popup_390_top.png');b.close()
