// Sales mode for dealers: settings on the real partner Worker, the public /s/ answer, links,
// and the shared router's reachable-roads search on real Pacific Beach roads.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { makePartner } from './partner_worker_harness.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const S = require('../public/sales.js');
const R = require('../public/router.js');

test('clean: defaults, https link, phone, reach choices', () => {
  assert.deepEqual(S.clean({}).sales, S.DEFAULTS);
  const ok = S.clean({ on: true, headline: ' Drive  to the beach ', url: 'https://beachmode.example/carts', phone: '(619) 555-0142', reach_mi: 3, cta: '' }).sales;
  assert.equal(ok.headline, 'Drive to the beach');
  assert.equal(ok.url, 'https://beachmode.example/carts');
  assert.equal(ok.cta, 'Buy from this shop');
  assert.equal(ok.reach_mi, 3);
  assert.match(S.clean({ url: 'http://x.example' }).error, /https/);
  assert.match(S.clean({ url: 'javascript:alert(1)' }).error, /https/);
  assert.match(S.clean({ phone: 'call me' }).error, /phone/);
  assert.match(S.clean({ reach_mi: 7 }).error, /Reach/);
  assert.match(S.clean({ headline: 'x'.repeat(81) }).error, /Headline/);
});

test('links round-trip through the page URL', () => {
  const l = S.link('https://golfcartmap.com', 'beachmode', { lat: 32.796512345, lon: -117.254, label: '4500 Ocean Blvd' });
  assert.equal(l, 'https://golfcartmap.com/s/beachmode?at=32.79651%2C-117.254&home=4500+Ocean+Blvd');
  const u = new URL(l);
  assert.deepEqual(S.parse(u.pathname, u.search), { slug: 'beachmode', home: { lat: 32.79651, lon: -117.254, label: '4500 Ocean Blvd' } });
  assert.deepEqual(S.parse('/s/BeachMode', '?at=999,1'), { slug: 'beachmode', home: null });
  assert.deepEqual(S.parse('/s/beachmode', ''), { slug: 'beachmode', home: null });
});

test('Worker: owner saves sales settings; /public/<slug>/sales answers only when on', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop({ patch: { phone: '619-555-0100' } });
  assert.equal((await p.call('/public/lajollacartco/sales')).status, 404);
  const bad = await p.call('/shop', { as: owner, method: 'PATCH', json: { sales: { on: true, url: 'http://insecure.example' } } });
  assert.equal(bad.status, 400);
  const on = await p.call('/shop', { as: owner, method: 'PATCH', json: { sales: { on: true, headline: 'Your home, by cart', url: 'https://lajollacartco.example/buy', reach_mi: 3 } } });
  assert.equal(on.status, 200, JSON.stringify(on.body));
  assert.equal(on.body.shop.sales.on, true);
  await p.call('/shop/places', { as: owner, json: { name: 'Crystal Pier', category: 'views', lat: 32.795, lon: -117.256, note: 'secret note' } });
  const pub = await p.call('/public/lajollacartco/sales');
  assert.equal(pub.status, 200);
  assert.equal(pub.body.sales.headline, 'Your home, by cart');
  assert.equal(pub.body.sales.phone.replace(/\D/g, ''), '6195550100', 'falls back to the shop phone');
  assert.equal(pub.body.sales.reach_mi, 3);
  assert.equal(pub.body.sales.on, undefined);
  assert.deepEqual(pub.body.places, [{ name: 'Crystal Pier', category: 'views', lat: 32.795, lon: -117.256 }]);
  assert.ok(!JSON.stringify(pub.body).includes('owner@example.com'));
  assert.ok(!JSON.stringify(pub.body).includes('secret note'));
  // Other PATCH fields leave sales alone; turning it off hides the page again.
  await p.call('/shop', { as: owner, method: 'PATCH', json: { blurb: 'New blurb' } });
  assert.equal((await p.call('/public/lajollacartco/sales')).status, 200);
  await p.call('/shop', { as: owner, method: 'PATCH', json: { sales: { ...on.body.shop.sales, on: false } } });
  assert.equal((await p.call('/public/lajollacartco/sales')).status, 404);
});

function fetchImpl(url) {
  const p = path.join(ROOT, 'public', String(url).replace(/^\//, ''));
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  return Promise.resolve({ ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) });
}
const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
const SD = regions.find(r => r.id === 'sd');
const HOME = { lat: 32.7965, lon: -117.2540 }; // Pacific Beach

test('router: reachable legal roads from a home grow with the reach and with an LSV', async () => {
  const cart = await R.openRegion(SD, rules, 'golf_cart', fetchImpl);
  const r2 = await cart.reachable(HOME, 2);
  const r5 = await cart.reachable(HOME, 5);
  assert.equal(r2.ok, true);
  assert.ok(r2.snapM < 50);
  assert.ok(r2.roadMiles > 10 && r5.roadMiles > r2.roadMiles, `${r2.roadMiles} < ${r5.roadMiles}`);
  assert.ok(r2.segs.length > 100 && r2.segs.every(s => s.length >= 2 && Math.abs(s[0][0] - HOME.lat) < 0.1));
  const pier = r2.at(32.7950, -117.2560);
  assert.ok(pier != null && pier < 0.5, 'Crystal Pier is a short ride: ' + pier);
  assert.equal(r2.at(32.8475, -117.2742), null, 'La Jolla Cove is past 2 miles');
  assert.equal(r2.at(32.72, -117.16), null, 'downtown is far');
  // A path on the reach map is a road the router would also drive.
  const leg = (await cart.legs([HOME, { lat: 32.7950, lon: -117.2560 }]))[0];
  assert.ok(leg && leg.points);
  const lsv = await R.openRegion(SD, rules, 'lsv', fetchImpl);
  assert.ok((await lsv.reachable(HOME, 2)).roadMiles >= r2.roadMiles);
  const sea = await cart.reachable({ lat: 32.79, lon: -117.30 }, 2);
  assert.equal(sea.ok, false, 'a point in the ocean has no road');
});
