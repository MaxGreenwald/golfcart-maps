import sys,json
from playwright.sync_api import sync_playwright
U='http://localhost:18431/'
STUB="window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios',Plugins:{Haptics:{impact:()=>Promise.resolve(),notification:()=>Promise.resolve()},Share:{share:()=>Promise.resolve({})}}};"
W,H,S=int(sys.argv[1]),int(sys.argv[2]),float(sys.argv[3])
JOBS=json.load(open(sys.argv[4]))
with sync_playwright() as p:
  b=p.chromium.launch()
  for j in JOBS:
    c=b.new_context(viewport={'width':W,'height':H},device_scale_factor=S,has_touch=True,is_mobile=W<700)
    c.add_init_script(STUB)
    pg=c.new_page();pg.goto(U+'?r='+j['r']);pg.wait_for_function('window.ready===true&&window.REG',timeout=60000);pg.wait_for_timeout(1500)
    for js in j.get('pre',[]): pg.evaluate("()=>{"+js+";return 0}"); pg.wait_for_timeout(700)
    if 'a' in j:
      r=pg.evaluate(f"testRoute({j['a']},{j['b']})");print(j['name'],r)
      if j.get('qa'): pg.evaluate(f"document.getElementById('qf').value={json.dumps(j['qa'])};document.getElementById('q').value={json.dumps(j['qb'])}")
    for js in j.get('post',[]): pg.evaluate("()=>{"+js+";return 0}"); pg.wait_for_timeout(700)
    if j.get('type'): pg.click('#q');pg.keyboard.type(j['type'],delay=60);pg.wait_for_timeout(3500)
    pg.wait_for_timeout(j.get('wait',4000))
    pg.screenshot(path=f"/workspace/gcm-appstore/raw/{j['name']}_{W}x{H}.png");c.close()
  b.close()
