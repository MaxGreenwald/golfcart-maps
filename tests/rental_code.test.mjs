// Rental code in Settings / CarPlay (Max t449u).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const R = createRequire(import.meta.url)('../public/rental.js');
const read = p => readFileSync(new URL('../' + p, import.meta.url), 'utf8');
const mem = () => { const m = new Map(); return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), m }; };
const answer = { unlocked: true, slug: 'beachmode', code: 'AB12CD3', grant: 'g1', shop: { name: 'Beach Mode', slug: 'beachmode' }, experiences: [{ id: 'e1', title: 'Sunset', stops: [] }], affiliates: [], places: [] };
const okFetch = calls => async url => { calls.push(url); return { ok: true, json: async () => answer }; };

test('normalize: case, spaces and dashes; junk rejected', () => {
  assert.equal(R.normalize(' ab12-cd3 '), 'AB12CD3');
  assert.equal(R.normalize('a'), '');
  assert.equal(R.normalize('<script>'), '');
});

test('enter: one call to the code-only unlock, saves the same record p.js saves', async () => {
  const st = mem(), calls = [];
  const r = await R.enter('ab12cd3', { fetch: okFetch(calls), storage: st, win: {}, nowMs: 5 });
  assert.equal(r.ok, true);
  assert.deepEqual(calls, ['/api/partner/public-code/unlock?code=AB12CD3']);
  const saved = JSON.parse(st.getItem('gcm_partner_access'));
  assert.equal(saved.slug, 'beachmode'); assert.equal(saved.code, 'AB12CD3'); assert.equal(saved.at, 5);
  assert.equal(saved.experiences.length, 1);
  assert.equal(st.getItem('gcm_partner_grant:beachmode'), 'g1');
});

test('enter in the app calls golfcartmap.com', async () => {
  const calls = [];
  await R.enter('AB12CD3', { fetch: okFetch(calls), storage: mem(), win: { Capacitor: { isNativePlatform: () => true } } });
  assert.match(calls[0], /^https:\/\/golfcartmap\.com\/api\/partner\/public-code\/unlock/);
});

test('enter: worker error is shown, nothing saved; bad code never calls the worker', async () => {
  const st = mem(), calls = [];
  const bad = async u => { calls.push(u); return { ok: false, json: async () => ({ error: 'Code already used' }) }; };
  assert.deepEqual(await R.enter('AB12CD3', { fetch: bad, storage: st, win: {} }), { ok: false, reason: 'Code already used' });
  assert.equal(st.getItem('gcm_partner_access'), null);
  await R.enter('x', { fetch: bad, storage: st, win: {} });
  assert.equal(calls.length, 1);
});

test('load expires after 14 days; remove clears the record and grant', async () => {
  const st = mem();
  await R.enter('AB12CD3', { fetch: okFetch([]), storage: st, win: {}, nowMs: 1000 });
  assert.ok(R.load(st, 1000 + 13 * 864e5));
  assert.equal(R.load(st, 1000 + 14 * 864e5), null);
  R.remove(st);
  assert.equal(st.getItem('gcm_partner_access'), null);
  assert.equal(st.getItem('gcm_partner_grant:beachmode'), null);
});

test('worker: code-only unlock checks the code and counts exactly one use', () => {
  const w = read('workers/partner/src/index.js');
  const i = w.indexOf("path === '/public-code/unlock'"), blk = w.slice(i, i + 1400);
  assert.ok(i > 0);
  for (const m of ['Code expired', 'Code already used', 'Code use limit reached', 'disabled=0']) assert.ok(blk.includes(m), m);
  assert.equal((blk.match(/uses=uses\+1/g) || []).length, 1);
  assert.match(w, /u\.pathname === '\/public-code\/unlock'\) return doFetch/);
});

test('settings row, scripts, CarPlay bridge and empty state are wired', () => {
  const h = read('public/index.html');
  for (const id of ['rentRow', 'rentCode', 'rentGo', 'rentRemove', 'rentView']) assert.ok(h.includes(`id="${id}"`), id);
  assert.ok(h.includes('<script src="rental.js"></script>'));
  assert.ok(read('public/p.html').includes('/rental.js'));
  const c = read('public/carplay.js');
  assert.match(c, /async enterCode\(code\)/); assert.match(c, /rental\(\)/); assert.match(c, /removeRental\(\)/);
  assert.match(c, /Tap the gear to enter one/);
});
