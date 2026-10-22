// Runs public/entitlements.js in a fake browser and checks the gates.
import vm from 'node:vm'; import fs from 'node:fs'; import assert from 'node:assert/strict';
const src = fs.readFileSync(new URL('../public/entitlements.js', import.meta.url), 'utf8');
function env(native, entitlement) {
  const store = {}, cls = new Set();
  const w = { addEventListener() {}, dispatchEvent() {}, CustomEvent: class { constructor(t, o) { this.detail = o && o.detail } } };
  w.window = w; w.localStorage = { getItem: k => k in store ? store[k] : null, setItem: (k, v) => { store[k] = String(v) } };
  w.document = { documentElement: { classList: { toggle: (c, v) => v ? cls.add(c) : cls.delete(c) } }, getElementById: () => null };
  if (native) { w.GCM_IOS = true; w.Capacitor = { Plugins: { GCMPurchases: { getEntitlement: async () => entitlement } } } }
  w.CustomEvent = w.CustomEvent; vm.createContext(w); vm.runInContext(src, w); return w;
}
const flush = () => new Promise(r => setTimeout(r, 0));
const E0 = env(true, { paid: false }); await flush(); const E = E0.GCMEnt;
assert.equal(E.CORE.filter(f => E.PAID.includes(f)).length, 0, 'CORE and PAID overlap');
assert.deepEqual([...E.PAID].sort(), ['extra_towns', 'offline_maps', 'voice_routing']);
for (const f of E.CORE) assert.equal(E.can(f), true, `core feature ${f} is gated for an unpaid user`);
for (const f of E.PAID) assert.equal(E.can(f), false, `${f} should need the driver plan in the app`);
E0.REG = { id: 'sd' }; assert.equal(E.canTown('sd'), true, 'home town open'); assert.equal(E.canTown('30a'), false, 'extra town gated');
E.setHome('30a'); assert.equal(E.canTown('30a'), true, 'switching home town keeps every legal map reachable');
assert.equal(E0.GCM_PAID, false);
E._set({ paid: true }); for (const f of E.PAID) assert.equal(E.can(f), true); assert.equal(E.canTown('sd'), true); assert.equal(E0.GCM_PAID, true);
const P = env(true, { paid: true, product: 'com.matchimus.golfcartmaps.driver.yearly' }); await flush();
assert.equal(P.GCMEnt.isPaid(), true, 'StoreKit entitlement reaches the web side'); assert.equal(P.GCM_PAID, true);
const W = env(false).GCMEnt;  // website: never gated
for (const f of [...W.CORE, ...W.PAID]) assert.equal(W.can(f), true); assert.equal(W.canTown('anything'), true);
console.log('paywall gate OK');
