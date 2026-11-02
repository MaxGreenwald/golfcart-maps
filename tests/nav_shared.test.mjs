// One nav engine for phone and CarPlay (Max t459u). The same GPS trace goes through the phone path
// (GCMFollow.engine, which the phone controller and app.js use) and the CarPlay path (carplay.js navStart/navFix,
// which CarPlaySceneDelegate.swift calls for every fix). Both must give the same answers, fix by fix.
// Scenario (Max, build 42, La Jolla, t453u): the route starts behind the cart (first turn ~400 ft back), loops
// around the block and comes back up his road through the start in his direction; he drives straight away.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const N = require('../public/nav.js');
globalThis.GCMNav = N;
const F = require('../public/navfollow.js');

const S = [32.85, -117.25], dLat = 1 / 110540, dLon = 1 / (Math.cos(32.85 * Math.PI / 180) * 111320);
const at = (x, y) => [S[0] + y * dLat, S[1] + x * dLon];
const RUNS = [
  { name: 'Calle Frescota', points: [at(0, 0), at(0, -122)] },
  { name: 'La Jolla Shores Drive', points: [at(0, -122), at(60, -122), at(60, -200)] },
  { name: 'Avenida de la Playa', points: [at(60, -200), at(0, -200)] },
  { name: 'Calle Frescota', points: [at(0, -200), at(0, 400), at(0, 800)] }];
const trace = n => Array.from({ length: n }, (_, t) => ({ lat: S[0] + t * 4 * dLat, lon: S[1], course: 0, speed: 4, t: t * 1000 }));

function carplay(route) {
  const win = { GCMFollow: F, navStepsFor: () => route, testRoute: async () => ({ mi: 1, rt: 2, min: 3, range: {} }), _lastDetail: { legs: [], dist: 1 }, ready: true };
  const ctx = { window: win, GCMNav: N, GCMFollow: F, READY: Promise.resolve(), REG: { id: 't', bbox: [-90, -180, 90, 180] }, REGIONS: [], MODE: 'lsv',
    localStorage: { getItem: () => null }, console, setTimeout, Promise, JSON, Math, Date, isFinite, String, Number };
  vm.createContext(ctx); vm.runInContext(fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8'), ctx);
  return win.GCMCarPlay;
}
function phone(route, fixes) {
  const e = F.engine(route), plan = F.promptPlan(), out = [];
  for (const f of fixes) {
    const st = e.fix({ latitude: f.lat, longitude: f.lon, heading: f.course, speed: f.speed }, f.t);
    const rr = e.offCheck(f.t); if (rr) e.reset();
    const say = rr ? 'Rerouting' : st.arrived ? null : plan.update(st, f.speed);
    out.push({ say, idx: st.idx, off: Math.round(st.off), reroute: rr, bearing: st.bearing == null ? null : Math.round(st.bearing) });
  }
  return out;
}

test('wrong way away from a looping route: phone and CarPlay reroute on the same fix, within 15 s', async () => {
  const route = N.buildSteps(RUNS, 'Destiny Coast');
  const fixes = trace(30);
  const ph = phone(route, fixes);
  const cp = carplay(route);
  const p = await cp.plan({ lat: S[0], lon: S[1] }, { lat: 0, lon: 0 }, 'lsv', false, null, 'Destiny Coast');
  assert.equal(p.ok, true);
  assert.equal(p.maneuvers.length, route.steps.length, 'one CarPlay maneuver per shared step');
  assert.equal(cp.navStart().ok, true);
  const car = fixes.map(f => cp.navFix(f));
  const phoneFire = ph.findIndex(x => x.reroute), carFire = car.findIndex(x => x.reroute);
  assert.ok(phoneFire > 0 && phoneFire <= 15, `phone rerouted at fix ${phoneFire}`);
  assert.equal(carFire, phoneFire, 'CarPlay reroutes on the same fix as the phone');
  assert.deepEqual(car.map(x => x.idx), ph.map(x => x.idx), 'same turn card index on every fix');
  assert.deepEqual(car.map(x => x.off), ph.map(x => x.off), 'same off-route distance on every fix');
  assert.deepEqual(car.map(x => x.bearing), ph.map(x => x.bearing), 'same map heading target on every fix');
  assert.deepEqual(car.map(x => x.say), ph.map(x => x.say), 'same spoken prompts on every fix (one voice plan)');
  assert.ok(car[carFire].reroute.course === 0, 'reroute keeps the driving direction');
});

test('the bug before t453u: whole-line matching sees the loop and never reroutes', () => {
  const route = N.buildSteps(RUNS, 'x');
  const t = F.offTracker();
  let fired = false;
  for (const f of trace(30)) if (t.update(N.project(route, [f.lat, f.lon]).off, f.t)) fired = true;
  assert.equal(fired, false);
});

test('driving the looping route correctly never reroutes and reaches the end on both paths', async () => {
  const route = N.buildSteps(RUNS, 'x');
  const fixes = []; let t = 0;
  for (let i = 1; i < route.pts.length; i++) {
    const a = route.pts[i - 1], b = route.pts[i], n = Math.max(1, Math.round(N.hav(a, b) / 4)), c = N.bearing(a, b);
    for (let k = 0; k < n; k++) fixes.push({ lat: a[0] + (b[0] - a[0]) * k / n, lon: a[1] + (b[1] - a[1]) * k / n, course: c, speed: 4, t: (t++) * 1000 });
  }
  const ph = phone(route, fixes);
  const cp = carplay(route); await cp.plan({ lat: 0, lon: 0 }, { lat: 0, lon: 0 }); cp.navStart();
  const car = fixes.map(f => cp.navFix(f));
  assert.equal(ph.some(x => x.reroute), false);
  const bad = car.findIndex(x => x.reroute); assert.equal(bad, -1, JSON.stringify([car[bad], ph[bad], fixes[bad]]));
  assert.equal(car[car.length - 1].idx, route.steps.length - 1, 'last card is arrive');
});
