// Seasonal experiences: show-from / show-until dates saved by the Worker, kept off the unlock
// answer when clearly out of season, and filtered by the renter's own date on the phone and CarPlay.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { makePartner } from './partner_worker_harness.mjs';

const require = createRequire(import.meta.url);
const S = require('../public/season.js');
const STOP = { label: 'Seal rock', lat: 32.847, lon: -117.278 };

test('clean: dates, empties, order and span', () => {
  assert.deepEqual(S.clean({}), { skip: true });
  assert.deepEqual(S.clean({ starts_on: '2026-12-01', ends_on: '2027-01-02' }), { starts_on: '2026-12-01', ends_on: '2027-01-02' });
  assert.deepEqual(S.clean({ starts_on: '', ends_on: '' }), { starts_on: '', ends_on: '' });
  assert.match(S.clean({ starts_on: '2026-02-30' }).error, /Show from/);
  assert.match(S.clean({ ends_on: '12/01/2026' }).error, /Show until/);
  assert.match(S.clean({ starts_on: '2026-12-05', ends_on: '2026-12-01' }).error, /before/);
  assert.match(S.clean({ starts_on: '2026-01-01', ends_on: '2027-06-01' }).error, /year/);
});

test('inSeason uses the device date, both ends included', () => {
  const ex = { starts_on: '2026-12-01', ends_on: '2026-12-31' };
  assert.equal(S.inSeason(ex, new Date(2026, 10, 30, 23, 59)), false);
  assert.equal(S.inSeason(ex, new Date(2026, 11, 1, 0, 1)), true);
  assert.equal(S.inSeason(ex, new Date(2026, 11, 31, 23, 0)), true);
  assert.equal(S.inSeason(ex, new Date(2027, 0, 1, 0, 1)), false);
  assert.equal(S.inSeason({}, new Date()), true);
  assert.equal(S.inSeason({ starts_on: '2026-12-01', ends_on: '' }, new Date(2030, 0, 1)), true);
});

test('labels in English and Spanish', () => {
  assert.equal(S.label({ starts_on: '2026-12-01', ends_on: '2027-01-02' }), 'Dec 1 to Jan 2');
  assert.equal(S.label({ starts_on: '2026-12-01', ends_on: '2027-01-02' }, 'es'), '1 dic al 2 ene');
  assert.equal(S.label({ starts_on: '2026-12-01' }), 'From Dec 1');
  assert.equal(S.label({ ends_on: '2027-01-02' }, 'es'), 'Hasta el 2 ene');
  assert.equal(S.label({}), '');
});

async function withNow(ms, fn) {
  const real = Date.now;
  Date.now = () => ms;
  try { return await fn(); } finally { Date.now = real; }
}

test('Worker saves season dates, rejects bad ones, and leaves out-of-season rides off the unlock', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop();
  const always = await p.call('/shop/experiences', { as: owner, json: { title: 'Seal loop', stops: [STOP] } });
  assert.equal(always.status, 201);
  assert.equal(always.body.experience.starts_on, '');
  const lights = await p.call('/shop/experiences', { as: owner, json: { title: 'Holiday lights', stops: [STOP], starts_on: '2026-12-01', ends_on: '2026-12-31' } });
  assert.equal(lights.status, 201);
  assert.equal(lights.body.experience.starts_on, '2026-12-01');
  assert.equal(lights.body.experience.ends_on, '2026-12-31');
  const bad = await p.call('/shop/experiences', { as: owner, json: { title: 'Bad', stops: [STOP], starts_on: '2026-12-09', ends_on: '2026-12-01' } });
  assert.equal(bad.status, 400);
  assert.match(bad.body.error, /before/);
  const badPatch = await p.call('/shop/experiences/' + always.body.experience.id, { as: owner, method: 'PATCH', json: { ends_on: 'soon' } });
  assert.equal(badPatch.status, 400);

  // A PATCH without dates keeps them; a PATCH with empty dates clears them.
  const kept = await p.call('/shop/experiences/' + lights.body.experience.id, { as: owner, method: 'PATCH', json: { title: 'Holiday lights tour' } });
  assert.equal(kept.status, 200);
  const shop = await p.call('/shop', { as: owner });
  const row = shop.body.experiences.find(e => e.id === lights.body.experience.id);
  assert.equal(row.title, 'Holiday lights tour');
  assert.equal(row.starts_on, '2026-12-01');

  assert.equal((await p.call('/shop/codes', { as: owner, json: { code: 'SEASON', multi_use: true, max_uses: 50 } })).status, 201);
  p.db.prepare("UPDATE codes SET expires_at=NULL WHERE code='SEASON'").run(); // the test jumps the clock months ahead
  const titles = async ms => withNow(ms, async () => {
    const u = await p.call('/public/lajollacartco/unlock?code=SEASON');
    assert.equal(u.status, 200, JSON.stringify(u.body));
    return u.body.experiences.map(e => e.title).sort();
  });
  // Nov 19 2026 noon PT: not yet. Dec 10: on. Jan 5 2027: over.
  assert.deepEqual(await titles(Date.UTC(2026, 10, 19, 20)), ['Seal loop']);
  const teaser = await withNow(Date.UTC(2026, 10, 19, 20), () => p.call('/public/lajollacartco'));
  assert.equal(teaser.body.experience_count, 1, 'the locked page counts only rides in season');
  assert.deepEqual(await titles(Date.UTC(2026, 11, 10, 20)), ['Holiday lights tour', 'Seal loop']);
  assert.deepEqual(await titles(Date.UTC(2027, 0, 5, 20)), ['Seal loop']);
  // Nov 30 at 6 PM PT is already Dec 1 in UTC: the Worker keeps it, the phone hides it until midnight.
  assert.deepEqual(await titles(Date.UTC(2026, 11, 1, 2)), ['Holiday lights tour', 'Seal loop']);

  const cleared = await p.call('/shop/experiences/' + lights.body.experience.id, { as: owner, method: 'PATCH', json: { starts_on: '', ends_on: '' } });
  assert.equal(cleared.status, 200);
  assert.deepEqual(await titles(Date.UTC(2026, 10, 19, 20)), ['Holiday lights tour', 'Seal loop']);
});

test('CarPlay lists only rides in season by the device date (real carplay.js + season.js)', async () => {
  const { readFileSync } = await import('node:fs');
  const vm = await import('node:vm');
  const exps = [
    { id: 'a', title: 'Seal loop', stops: [STOP] },
    { id: 'b', title: 'Holiday lights', stops: [STOP], starts_on: '2000-12-01', ends_on: '2000-12-31' },
    { id: 'c', title: 'Always from 2000', stops: [STOP], starts_on: '2000-01-01' },
  ];
  const store = { gcm_partner_access: JSON.stringify({ slug: 'lajollacartco', code: 'X', at: Date.now(), shop: { name: 'Shop' }, experiences: exps }) };
  const win = {};
  const ctx = { window: win, self: win, localStorage: { getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = String(v); } },
    location: { protocol: 'capacitor:' }, console, setTimeout, Promise, JSON, Math, Date, isFinite, String };
  vm.createContext(ctx);
  vm.runInContext(readFileSync(new URL('../public/season.js', import.meta.url), 'utf8').replace("typeof module === 'object'", 'false'), ctx);
  ctx.GCMSeason = win.GCMSeason; // in a browser window and the global are one object
  vm.runInContext(readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8'), ctx);
  assert.ok(win.GCMSeason, 'season.js loaded');
  const r = await win.GCMCarPlay.experiences();
  assert.equal(r.ok, true);
  assert.deepEqual(r.experiences.map(e => e.id), ['a', 'c']);
});
