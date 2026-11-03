// Build 43, La Jolla. The route says "Left onto La Jolla Shores Drive, then Right onto Calle Frescota"
// on the way to Shorehouse Kitchen. Missing that left and continuing north, or turning around and
// driving back down Calle del Oro, used to leave the card frozen: the cart was still on the route
// line, so the distance check never asked for a new route. A search that finds nothing must say so
// instead of going quiet. Real road data: public/data/sd.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const R = require('../public/router.js');
const Rule = require('../public/roadrule.js');
const N = require('../public/nav.js');
const F = require('../public/navfollow.js');
globalThis.GCMNav = N;

function fetchImpl(url) {
  const p = path.join(ROOT, 'public', String(url).replace(/^\//, ''));
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  return Promise.resolve({ ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) });
}
const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
const region = regions.find(r => r.id === 'sd');
const SHORE = { lat: 32.853956, lon: -117.254606 }; // Shorehouse Kitchen, Avenida de la Playa
const FROM = { lat: 32.8547, lon: -117.2483 };     // southeast end of Calle del Oro

function texts(leg, dest) {
  if (!leg || !leg.points) return null;
  return N.buildSteps(leg.runs, dest || 'Shorehouse Kitchen', { continuing: !!leg.ahead }).steps.map(s => s.text);
}
function carplay(route) {
  const win = { GCMFollow: F, navStepsFor: () => route, testRoute: async () => ({ mi: 1, rt: 2, min: 3, range: {} }), _lastDetail: { legs: [], dist: 1 }, ready: true };
  const ctx = { window: win, GCMNav: N, GCMFollow: F, READY: Promise.resolve(), REG: { id: 't', bbox: [-90, -180, 90, 180] }, REGIONS: [], MODE: 'lsv',
    localStorage: { getItem: () => null }, console, setTimeout, Promise, JSON, Math, Date, isFinite, String, Number };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8'), ctx);
  return win.GCMCarPlay;
}
function phoneTrace(route, fixes) {
  const e = F.engine(route);
  const out = [];
  for (const f of fixes) {
    const st = e.fix({ latitude: f.lat, longitude: f.lon, heading: f.course, speed: f.speed }, f.t);
    const rr = e.offCheck(f.t);
    if (rr) e.reset();
    out.push({ reroute: rr, wrong: !!st.wrong, off: st.off, along: st.along });
  }
  return out;
}
function alongFixes(route, stepM) {
  const fixes = [];
  for (let d = 0; d <= route.total; d += stepM) {
    const p = F.pointAt(route, d);
    const q = F.pointAt(route, Math.min(route.total, d + stepM));
    fixes.push({ lat: p[0], lon: p[1], course: N.bearing(p, q), speed: 4, t: fixes.length * 1000, d });
  }
  return fixes;
}

let lsv, cart;
test.before(async () => {
  lsv = await R.openRegion(region, rules, 'lsv', fetchImpl);
  cart = await R.openRegion(region, rules, 'golf_cart', fetchImpl);
});

test('the Shorehouse route is left onto La Jolla Shores, then right onto Calle Frescota', async () => {
  const leg = await lsv.trip(FROM, SHORE);
  const tx = texts(leg);
  assert.ok(tx.some(t => t === 'Turn left onto La Jolla Shores Drive'), tx.join(' | '));
  assert.ok(tx.some(t => t === 'Turn right onto Calle Frescota'), tx.join(' | '));
  assert.equal(tx.some(t => /U-turn/i.test(t)), false);
});

test('missing the left and going north reroutes on both paths, then a route still reaches Shorehouse', async () => {
  const leg = await lsv.trip(FROM, SHORE);
  const route = N.buildSteps(leg.runs, 'Shorehouse Kitchen');
  const turn = route.steps.find(s => s.text === 'Turn left onto La Jolla Shores Drive');
  const fixes = alongFixes(route, 4).filter(f => f.d <= turn.at);
  // Real La Jolla Shores centerline north of the intersection (the missed turn).
  const north = [[32.85922, -117.25349], [32.86097, -117.25338], [32.86342, -117.25317]];
  let prev = fixes[fixes.length - 1];
  for (let i = 1; i < north.length; i++) {
    const a = north[i - 1], b = north[i];
    const n = Math.max(1, Math.round(N.hav(a, b) / 4));
    for (let k = 1; k <= n; k++) {
      const lat = a[0] + (b[0] - a[0]) * k / n, lon = a[1] + (b[1] - a[1]) * k / n;
      const course = N.bearing([prev.lat, prev.lon], [lat, lon]);
      fixes.push({ lat, lon, course, speed: 4, t: fixes.length * 1000 });
      prev = fixes[fixes.length - 1];
    }
  }
  const passed = fixes.findIndex(f => f.d == null);
  const ph = phoneTrace(route, fixes);
  const cp = carplay(route);
  await cp.plan({ lat: FROM.lat, lon: FROM.lon }, SHORE, 'lsv', false, null, 'Shorehouse Kitchen');
  assert.equal(cp.navStart().ok, true);
  const car = fixes.map(f => cp.navFix(f));
  const phoneFire = ph.findIndex(x => x.reroute), carFire = car.findIndex(x => x.reroute);
  assert.ok(phoneFire > passed && phoneFire <= passed + 12, `phone rerouted ${phoneFire - passed}s after leaving the turn`);
  assert.equal(carFire, phoneFire, 'CarPlay reroutes on the same fix');
  // He has left the line, so the log is the distance form. The on-the-line reversal is the next test.
  assert.match(car[carFire].reroute.reason, /^off route \d+ m$/);
  assert.equal(typeof car[carFire].reroute.course, 'number');
  assert.equal(car[carFire].say, 'Rerouting');
  const here = fixes[carFire];
  const back = await lsv.trip({ lat: here.lat, lon: here.lon }, SHORE, { heading: here.course });
  const backText = texts(back);
  assert.ok(backText, 'a route back exists for an LSV');
  assert.ok(N.hav([here.lat, here.lon], back.points[0]) < 20, 'the new line starts where he is');
  const first = N.bearing(back.points[0], back.points[Math.min(3, back.points.length - 1)]);
  assert.ok(Math.abs(((first - here.course + 540) % 360) - 180) < 50, 'it sets off the way he is facing, not back down the old line');
});

test('turning around on Calle del Oro reroutes instead of freezing the distance', async () => {
  const leg = await lsv.trip(FROM, SHORE);
  const route = N.buildSteps(leg.runs, 'Shorehouse Kitchen');
  const turn = route.steps.find(s => s.text === 'Turn left onto La Jolla Shores Drive');
  const fixes = alongFixes(route, 4).filter(f => f.d <= turn.at - 80);
  const backFrom = fixes.length;
  for (let i = fixes.length - 2; i >= 0; i--) {
    const a = fixes[i + 1], b = fixes[i];
    fixes.push({ lat: b.lat, lon: b.lon, course: N.bearing([a.lat, a.lon], [b.lat, b.lon]), speed: 4, t: fixes.length * 1000 });
  }
  const ph = phoneTrace(route, fixes);
  const fire = ph.findIndex(x => x.reroute);
  assert.ok(fire >= backFrom && fire <= backFrom + 8, `rerouted ${fire - backFrom}s after turning around`);
  assert.equal(ph.slice(0, backFrom).some(x => x.reroute), false, 'the ride up to the turn does not reroute');
  const here = fixes[fire];
  const back = await lsv.trip({ lat: here.lat, lon: here.lon }, SHORE, { heading: here.course });
  assert.ok(texts(back), 'there is a route back from the U-turn');
});

test('a dead-end court tells him to make a U-turn, it does not say only Continue', async () => {
  // Del Oro Court ends south of Calle del Oro. Heading into the end, the only way out is back.
  const leg = await lsv.trip({ lat: 32.8585, lon: -117.25243 }, SHORE, { heading: 180 });
  const tx = texts(leg);
  assert.ok(tx.some(t => t === 'Make a U-turn onto Del Oro Court'), tx.join(' | '));
  assert.equal(/\u2014/.test(tx.join(' ')), false);
});

test('no legal golf-cart route is a reason, not an empty failure', async () => {
  // 150 m north of the intersection, La Jolla Shores is 30 mph for longer than the 75 ft waiver.
  const leg = await cart.trip({ lat: 32.8606, lon: -117.2534 }, SHORE, { heading: 5 });
  assert.equal(leg.points, null);
  const rule = Rule.ruleFor(rules, region, 'golf_cart');
  const reason = Rule.noRoute(rule);
  assert.match(reason, /mph road/);
  assert.equal(/\u2014/.test(reason), false);
});

test('CarPlay plan with no route returns that reason for the on-screen alert', async () => {
  const rule = Rule.ruleFor(rules, region, 'lsv');
  const win = {
    ready: true, testRoute: async () => null, _lastDetail: null, RULE: rule, GCMRule: Rule,
    REG: { id: 'sd', bbox: [-90, -180, 90, 180] }, REGIONS: [],
  };
  const ctx = {
    window: win, READY: Promise.resolve(), REG: win.REG, REGIONS: [], RULE: rule, GCMRule: Rule, MODE: 'lsv',
    localStorage: { getItem: () => null }, console, setTimeout, Promise, JSON, Math, Date, isFinite, String, Number,
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8'), ctx);
  const p = await win.GCMCarPlay.plan({ lat: 32.86, lon: -117.253 }, SHORE, 'lsv', false, 5, 'Shorehouse Kitchen');
  assert.equal(p.ok, false);
  assert.equal(p.reason, Rule.noRoute(rule));
  assert.ok(p.reason.length > 0);
});
