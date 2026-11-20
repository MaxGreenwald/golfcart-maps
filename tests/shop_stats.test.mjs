// node --test tests/shop_stats.test.mjs
// Shop activity uses the same install denylist and internal filter as /stats.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { ensureSchema } from '../lib/analytics_store.js';
import { computeShopStats, fetchShopStats, shopStatsRequest } from '../lib/shop_stats.js';
import { EXCLUDE_IIDS } from '../lib/analytics_exclude.js';

const NOW = Date.parse('2026-11-10T18:00:00Z');
const DAY = '2026-11-10';
const PREV = '2026-11-09';
const REAL = '11111111-1111-4111-8111-111111111111';
const OTHER = '99999999-9999-4999-8999-999999999999';
const DENY = EXCLUDE_IIDS[0];

function dbWith(rows) {
  const db = new DatabaseSync(':memory:');
  const exec = (s, ...a) => { db.prepare(s).run(...a); };
  ensureSchema(exec, (s, ...a) => db.prepare(s).all(...a));
  const ins = db.prepare('INSERT INTO events(ts, day, event, town, platform, pwa, iid, sid, props) VALUES (?,?,?,?,?,?,?,?,?)');
  for (const r of rows) ins.run(r.ts || NOW, r.day || DAY, r.event, r.town ?? 'sd', r.platform || 'web', 0, r.iid ?? REAL, r.sid || 'sess-aaaaaaaa', JSON.stringify(r.props || {}));
  ensureSchema(exec, (s, ...a) => db.prepare(s).all(...a));   // flags rows stored without a check, as the Worker does on wake
  return db;
}
const qOf = db => (sql, ...params) => db.prepare(sql).all(...params);

function rows() {
  return [
    { iid: REAL, event: 'partner_unlock', props: { shop: 'beachmode', code: 'ab12cd3' } },
    { iid: REAL, event: 'partner_unlock', day: PREV, props: { shop: 'beachmode', code: 'ab12cd3' } },
    { iid: REAL, event: 'partner_unlock', props: { shop: 'beachmode', code: 'zz99' } },
    { iid: REAL, event: 'experience_started', props: { shop: 'beachmode', ride: 'e1' } },
    { iid: REAL, event: 'experience_finished', props: { shop: 'beachmode', ride: 'e1' } },
    { iid: REAL, event: 'experience_started', day: PREV, props: { shop: 'beachmode', ride: 'e1' } },
    { iid: REAL, event: 'affiliate_tap', props: { shop: 'beachmode', pin: 'a1' } },
    { iid: REAL, event: 'affiliate_tap', props: { shop: 'beachmode', pin: 'a1' } },
    { iid: OTHER, event: 'partner_unlock', props: { shop: 'other-shop', code: 'ab12cd3' } },
    { iid: OTHER, event: 'experience_started', props: { shop: 'other-shop', ride: 'e9' } },
    { iid: DENY, event: 'partner_unlock', props: { shop: 'beachmode', code: 'ab12cd3' } },
    { iid: DENY, event: 'experience_started', props: { shop: 'beachmode', ride: 'e1' } },
    { iid: DENY, event: 'experience_finished', props: { shop: 'beachmode', ride: 'e1' } },
    { iid: DENY, event: 'affiliate_tap', props: { shop: 'beachmode', pin: 'a1' } },
    { iid: '22222222-2222-4222-8222-222222222222', event: 'partner_unlock', props: { shop: 'beachmode', code: 'ab12cd3', internal: 'sim' } },
    { iid: '33333333-3333-4333-8333-333333333333', event: 'session', props: { internal: 'e2e', shop: 'beachmode' } },
    { iid: '33333333-3333-4333-8333-333333333333', event: 'affiliate_tap', props: { shop: 'beachmode', pin: 'a1' } },
    { iid: REAL, event: 'route_searched', props: { ok: true, shop: 'beachmode' } },
  ];
}

test('counts unlocks per code, rides and offer taps by day, for this shop only', () => {
  const s = computeShopStats(qOf(dbWith(rows())), { shop: 'BeachMode', days: 30, now: NOW });
  assert.equal(s.shop, 'beachmode');
  assert.equal(s.filter, 'internal-test-excluded');
  assert.deepEqual(s.totals, { unlocks: 3, started: 2, finished: 1, affiliate_taps: 2, opens: 0, routes: 2, experience_opens: 0, stop_opens: 0 });
  const plain = v => JSON.parse(JSON.stringify(v));
  assert.deepEqual(plain(s.codes).map(c => [c.code, c.unlocks]), [['ab12cd3', 2], ['zz99', 1]]);
  assert.deepEqual(plain(s.rides), [{ ride: 'e1', opened: 0, started: 2, finished: 1 }]);
  assert.deepEqual(plain(s.pins), [{ pin: 'a1', taps: 2 }]);
  assert.equal(s.daily[0].day, DAY);
  assert.equal(s.daily[0].unlocks, 2);
  assert.equal(s.daily[1].day, PREV);
  assert.equal(s.daily[1].started, 1);
  assert.ok(!JSON.stringify(s).includes(DENY));
  assert.ok(!JSON.stringify(s).includes('other-shop'));
});

test('a denylisted install is what the live list drops, and a bad slug is refused', () => {
  assert.ok(DENY);
  const s = computeShopStats(qOf(dbWith(rows())), { shop: 'beachmode', days: 7, now: NOW });
  assert.equal(s.totals.unlocks, 3);
  assert.throws(() => computeShopStats(qOf(dbWith([])), { shop: '../x', now: NOW }), /bad shop/);
});

test('fetch uses the stats key and refuses another shop or a missing key', async () => {
  const req = shopStatsRequest('https://gcm-analytics.example/stats', 'secret', 'BeachMode', 7);
  assert.equal(req.url, 'https://gcm-analytics.example/shop-stats?shop=beachmode&days=7');
  assert.equal(req.headers['x-stats-key'], 'secret');
  assert.equal(shopStatsRequest('https://gcm-analytics.example', '', 'beachmode', 30), null);
  const calls = [];
  const ok = await fetchShopStats(async (url, o) => {
    calls.push([url, o.headers['x-stats-key']]);
    return { ok: true, json: async () => ({ shop: 'beachmode', days: 7, totals: { unlocks: 1, started: 0, finished: 0, affiliate_taps: 0 } }) };
  }, { base: 'https://gcm-analytics.example', key: 'secret', shop: 'beachmode', days: 7 });
  assert.equal(ok.ready, true);
  assert.equal(ok.totals.unlocks, 1);
  assert.deepEqual(calls, [['https://gcm-analytics.example/shop-stats?shop=beachmode&days=7', 'secret']]);
  const missing = await fetchShopStats(async () => { throw new Error('called'); }, { base: 'https://x', key: '', shop: 'beachmode' });
  assert.equal(missing.ready, false);
  assert.equal(missing.reason, 'not_configured');
  const wrong = await fetchShopStats(async () => ({ ok: true, json: async () => ({ shop: 'other-shop' }) }), { base: 'https://x', key: 'k', shop: 'beachmode' });
  assert.equal(wrong.ready, false);
  assert.equal(wrong.reason, 'unavailable');
});

test('workers expose shop stats behind the stats key and the shop session', () => {
  const analytics = readFileSync(new URL('../workers/analytics/src/index.js', import.meta.url), 'utf8');
  const partner = readFileSync(new URL('../workers/partner/src/index.js', import.meta.url), 'utf8');
  const web = readFileSync(new URL('../public/p.js', import.meta.url), 'utf8');
  const page = readFileSync(new URL('../public/p.html', import.meta.url), 'utf8');
  assert.match(analytics, /\/shop-stats/);
  const gate = analytics.indexOf("if (!env.STATS_KEY || !eq(k, env.STATS_KEY))");
  const shopRoute = analytics.indexOf("u.pathname === '/shop-stats'", gate);
  assert.ok(gate > 0 && shopRoute > gate);
  assert.match(analytics, /computeShopStats/);
  assert.match(partner, /pathname === '\/shop\/stats'/);
  assert.match(partner, /fetchShopStats/);
  assert.match(partner, /ANALYTICS_STATS_KEY/);
  assert.match(partner, /bundle\.shop\.slug/);
  assert.ok(page.indexOf('/track.js') < page.indexOf('/p.js'));
  assert.match(web, /partner_unlock/);
  assert.match(web, /experience_started/);
  assert.match(web, /experience_finished/);
  assert.match(web, /affiliate_tap/);
  assert.match(web, /if \(!handoffParam\) trackShop\('partner_unlock'/);
});

test('weekly renter opens, routes, ride and stop opens; Max installs and other shops left out', () => {
  const MON = '2026-11-09', SUN = '2026-11-15', NEXT = '2026-11-16', LAST = '2026-11-08';
  const now = Date.parse('2026-11-17T18:00:00Z');
  const ev = (event, day, props, iid = REAL) => ({ iid, event, day, props: { shop: 'beachmode', ...props } });
  const db = dbWith([
    ev('partner_open', MON, { code: 'ab12' }), ev('partner_open', SUN, { code: 'ab12' }), ev('partner_open', NEXT, { code: 'ab12' }),
    ev('partner_open', LAST, { code: 'ab12' }),
    ev('experience_opened', MON, { ride: 'e1' }), ev('experience_opened', SUN, { ride: 'e2' }),
    ev('stop_opened', SUN, { ride: 'e1', pin: '2' }), ev('stop_opened', SUN, { ride: 'e1', pin: '2' }), ev('stop_opened', NEXT, { ride: 'e1', pin: '1' }),
    ev('experience_started', MON, { ride: 'e1' }), ev('partner_route', NEXT, {}),
    ev('partner_open', MON, { code: 'ab12' }, DENY), ev('stop_opened', MON, { ride: 'e1', pin: '2' }, DENY),
    { iid: OTHER, event: 'partner_open', day: MON, props: { shop: 'other-shop' } },
  ]);
  const s = computeShopStats(qOf(db), { shop: 'beachmode', days: 30, now });
  const plain = v => JSON.parse(JSON.stringify(v));
  assert.equal(s.totals.opens, 4);
  assert.equal(s.totals.routes, 2, 'experience starts plus free routes');
  assert.equal(s.totals.experience_opens, 2);
  assert.equal(s.totals.stop_opens, 3);
  assert.deepEqual(plain(s.weekly).map(w => [w.week, w.opens, w.routes, w.experience_opens, w.stop_opens]), [
    ['2026-11-16', 1, 1, 0, 1],
    ['2026-11-09', 2, 1, 2, 2],
    ['2026-11-02', 1, 0, 0, 0],
  ]);
  assert.deepEqual(plain(s.stops)[0], { ride: 'e1', pin: '2', opens: 2 });
  assert.deepEqual(plain(s.rides).find(r => r.ride === 'e2'), { ride: 'e2', opened: 1, started: 0, finished: 0 });
  // Extra denylisted ids from the analytics Worker (EXCLUDE_IIDS env) are left out too.
  const t = computeShopStats(qOf(db), { shop: 'beachmode', days: 30, now, extraIids: [REAL] });
  assert.equal(t.totals.opens, 0);
});

test('new shop events carry tokens only', async () => {
  const { sanitize } = await import('../lib/analytics.js');
  const base = { pl: 'web', i: REAL, s: 'sess-aaaaaaaa', t: 'sd' };
  assert.deepEqual(sanitize({ ...base, e: 'partner_open', p: { shop: 'beachmode', code: 'AB12', lat: 32.8, name: 'Jamie' } }).props, { shop: 'beachmode', code: 'ab12' });
  assert.deepEqual(sanitize({ ...base, e: 'stop_opened', p: { shop: 'beachmode', ride: 'e1', pin: '2', label: 'Seals' } }).props, { shop: 'beachmode', ride: 'e1', pin: '2' });
  assert.deepEqual(sanitize({ ...base, e: 'partner_route', p: { shop: 'beachmode', mi: 3 } }).props, { shop: 'beachmode' });
  assert.deepEqual(sanitize({ ...base, e: 'experience_opened', p: { shop: 'beachmode', ride: 'e1' } }).props, { shop: 'beachmode', ride: 'e1' });
});
