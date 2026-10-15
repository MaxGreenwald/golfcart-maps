import os,re,time
from playwright.sync_api import sync_playwright
U=os.environ.get('URL','https://paywall-chargers.golfcart-maps.pages.dev/');S='/workspace/gcm-paywall/shots/'
EM='paywall-test+%d@example.com'%int(time.time())
with sync_playwright() as p:
  b=p.chromium.launch();c=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2);pg=c.new_page()
  pg.goto(U);pg.wait_for_timeout(4000)
  chg=[]; pg.on('request',lambda r:'chargers.json' in r.url and chg.append(r.url))
  assert 'locked' in pg.get_attribute('#cChg','class');pg.screenshot(path=S+'1_locked_chip.png')
  pg.click('#cChg');pg.wait_for_selector('#paySheet');pg.screenshot(path=S+'2_sheet.png')
  assert not chg,'charger data loaded while locked'
  txt=pg.inner_text('#paySheet');assert '$10/year' in txt and 'free' not in txt.lower()
  pg.click('#paySub');pg.wait_for_url(re.compile('checkout.stripe.com'),timeout=30000);pg.wait_for_timeout(4000)
  pg.fill('#email',EM)
  pg.screenshot(path=S+'3a_checkout_open.png')
  pg.eval_on_selector('[data-testid=card-accordion-item-button]','e=>e.click()');pg.wait_for_timeout(2000)
  pg.fill('#cardNumber','4242424242424242');pg.fill('#cardExpiry','12/34');pg.fill('#cardCvc','123')
  pg.fill('#billingName','Test Buyer')
  if pg.locator('#billingPostalCode').count():pg.fill('#billingPostalCode','92101')
  cb=pg.locator('#enableStripePass')
  if cb.count() and cb.is_checked():cb.uncheck(force=True)
  pg.screenshot(path=S+'3_checkout.png')
  pg.click('button[type=submit]');pg.wait_for_timeout(12000);pg.screenshot(path=S+'3b_after_submit.png',full_page=True);pg.wait_for_url(re.compile(r'pages\.dev'),timeout=90000);pg.wait_for_timeout(7000)
  assert 'locked' not in (pg.get_attribute('#cChg','class') or '')
  assert 'on' in pg.get_attribute('#cChg','class');pg.screenshot(path=S+'4_unlocked.png')
  print('markers',pg.locator('.chg').count())
  # restore on a fresh device
  c2=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2);q=c2.new_page();q.goto(U);q.wait_for_timeout(4000)
  q.click('#cChg');q.click('#payRest summary');q.fill('#payEmail','nobody-%d@example.com'%time.time());q.click('#payRestBtn');q.wait_for_timeout(3000)
  print('bad restore:',q.inner_text('#payMsg'));q.screenshot(path=S+'5_restore_none.png')
  q.fill('#payEmail',EM);q.click('#payRestBtn');q.wait_for_timeout(5000)
  assert q.locator('#paySheet').count()==0 and 'locked' not in q.get_attribute('#cChg','class');q.screenshot(path=S+'6_restored.png')
  print('restored markers',q.locator('.chg').count())
  # simulated iOS app: no price / subscribe
  c3=b.new_context(viewport={'width':390,'height':844});r=c3.new_page()
  r.add_init_script("window.Capacitor={isNativePlatform:()=>true,getPlatform:()=>'ios'}");r.goto(U);r.wait_for_timeout(4000);r.click('#cChg')
  t=r.inner_text('#paySheet');assert '$' not in t and r.locator('#paySub').count()==0;r.screenshot(path=S+'7_ios_sheet.png')
  print('ALL OK',EM)
