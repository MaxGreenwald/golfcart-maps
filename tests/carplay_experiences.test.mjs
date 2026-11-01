// CarPlay Experiences bridge (public/carplay.js experiences()/stops()): reads the renter access the phone saved.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const SRC = fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8');
const UNLOCK = { unlocked: true, code: 'TEST123', shop: { name: 'Beach Mode Rentals', vehicle: 'lsv' },
  experiences: [
    { id: 'e1', title: 'PB Sunset', description: 'long text never shown', stops: [
      { name: 'Crystal Pier', category: 'views', lat: 32.7950, lon: -117.2560 },
      { name: 'Bar One', category: 'restaurant', lat: 32.80, lon: -117.25 },
      { name: 'No coords', lat: null, lon: null }] },
    { id: 'e2', title: 'Empty', stops: [] }],
  affiliates: [{ id: 'a1', name: 'Bar One', offer: '10% off', coupon: 'BAR10' }] };

function load(store, fetchImpl) {
  const calls = [];
  const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const win = {};
  const ctx = { window: win, localStorage: ls, location: { protocol: 'capacitor:' }, console,
    fetch: async (u, o) => { calls.push(u); return fetchImpl(u, o); }, setTimeout, Promise, JSON, Math, Date, isFinite, String };
  vm.createContext(ctx); vm.runInContext(SRC, ctx);
  return { cp: win.GCMCarPlay, calls };
}
const ok = j => ({ ok: true, json: async () => j });
const access = (at = Date.now()) => ({ gcm_partner_access: JSON.stringify({ slug: 'beachmode', code: 'TEST123', at, ...UNLOCK }) });

test('no access: short message to open the shop link, no network', async () => {
  const { cp, calls } = load({}, () => ok(UNLOCK));
  const r = await cp.experiences();
  assert.equal(r.ok, false); assert.match(r.reason, /shop link on your phone/); assert.equal(calls.length, 0);
});
test('expired access (over 14 days) is ignored', async () => {
  const { cp } = load(access(Date.now() - 15 * 864e5), () => ok(UNLOCK));
  assert.equal((await cp.experiences()).ok, false);
});
test('experiences: shop vehicle, titles, stop counts, empty ones dropped, no descriptions', async () => {
  const { cp, calls } = load(access(), () => ok(UNLOCK));
  const r = await cp.experiences();
  assert.equal(r.ok, true); assert.equal(r.shop.vehicle, 'lsv'); assert.equal(r.shop.name, 'Beach Mode Rentals');
  assert.deepEqual(JSON.parse(JSON.stringify(r.experiences)), [{ id: 'e1', title: 'PB Sunset', stops: 2 }]);
  assert.ok(!JSON.stringify(r).includes('long text'));
  assert.equal(calls.length, 0, 'never calls unlock again (it counts a code use)');
});
test('stops: in order, distance from here, coupon from the matching offer', async () => {
  const { cp } = load(access(), () => ok(UNLOCK));
  const r = await cp.stops('e1', 32.7950, -117.2560);
  assert.equal(r.ok, true);
  assert.deepEqual(r.stops.map(s => s.name), ['Crystal Pier', 'Bar One']);
  assert.equal(r.stops[0].meters, 0); assert.ok(r.stops[1].meters > 500 && r.stops[1].meters < 1000);
  assert.equal(r.stops[1].coupon, 'BAR10'); assert.equal(r.stops[0].coupon, '');
});
test('old access without saved experiences: not ok', async () => {
  const { cp } = load({ gcm_partner_access: JSON.stringify({ slug: 'beachmode', code: 'X', at: Date.now() }) }, () => ok(UNLOCK));
  assert.equal((await cp.experiences()).ok, false);
});
