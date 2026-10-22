# Simulated iOS app, unpaid: the home town's legal-roads map loads in full; another town opens the driver plan sheet.
import os
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','http://localhost:8765/')
INIT="""window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios',Plugins:{GCMPurchases:{
 getEntitlement:async()=>window.__paid?{paid:true,product:'com.matchimus.golfcartmaps.driver.yearly'}:{paid:false},
 getProducts:async()=>({products:[{id:'com.matchimus.golfcartmaps.driver.monthly',displayPrice:'$0.99'},{id:'com.matchimus.golfcartmaps.driver.yearly',displayPrice:'$9.99'}]}),
 purchase:async({id})=>{window.__paid=true;return{ok:true,paid:true,product:id}},restore:async()=>({ok:true,paid:!!window.__paid})}}};"""
with sync_playwright() as p:
  b=p.chromium.launch();pg=b.new_page(viewport={'width':390,'height':844});pg.add_init_script(INIT)
  pg.goto(U+'?r=sd');pg.wait_for_function('typeof D!=="undefined"&&!!D&&window.REG&&REG.id==="sd"',timeout=30000)
  assert pg.evaluate('GCMEnt.isPaid()')==False
  assert pg.evaluate('GCMEnt.can("core_map")&&GCMEnt.can("legal_roads")&&GCMEnt.can("legal_routing")')
  assert pg.locator('#drvSheet').count()==0,'paywall shown over the core map'
  pg.select_option('#city','30a');pg.wait_for_selector('#drvSheet .pbtn',timeout=10000)
  t=pg.inner_text('#drvSheet');assert 'Restore purchases' in t and 'Terms of Use' in t and 'Privacy Policy' in t and 'free' not in t.lower(),t
  assert pg.evaluate('REG.id')=='sd'
  pg.click('#drvSheet .pbtn >> nth=1');pg.wait_for_function('window.REG&&REG.id==="30a"',timeout=30000)
  assert pg.evaluate('GCMEnt.isPaid()&&window.GCM_PAID===true')
  print('PASS paywall_ios: core map open unpaid; extra town -> driver sheet -> purchase -> unlocked')
