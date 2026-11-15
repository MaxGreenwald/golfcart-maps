// Golf cart + Risky from La Jolla Shores to either Snooze used to search with no
// cap (about 35s and 2 GB, then the phone web view died). The search now stops
// on a shared time and state budget, and a known route stays the same.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const R = require('../public/router.js');
const Rule = require('../public/roadrule.js');
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

const PASEO = [32.8593172, -117.2542705]; // 8405 Paseo del Ocaso, La Jolla Shores
const SNOOZE_DEL_MAR = [32.9532878, -117.2327422]; // 3435 Del Mar Heights Rd
const SNOOZE_HILLCREST = [32.7492574, -117.1605405]; // 3940 5th Ave

function loadSd(veh, pts) {
  const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
  const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
  const reg = regions.find(r => r.id === 'sd');
  const rule = Rule.ruleFor(rules, reg, veh);
  const idx = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/sd/index.json'), 'utf8'));
  const D = { meta: idx.meta, names: idx.names, segs: [] };
  const tile = idx.meta.tileSize, have = new Set(idx.meta.tiles);
  let south = 90, west = 180, north = -90, east = -180;
  for (const p of pts) {
    south = Math.min(south, p[0]); north = Math.max(north, p[0]);
    west = Math.min(west, p[1]); east = Math.max(east, p[1]);
  }
  const pad = 0.06;
  south -= pad; north += pad; west -= pad; east += pad;
  const buckets = {}, net = R.create();
  const cls = s => Rule.cls(s, rule, false);
  for (let x = Math.floor(west / tile); x <= Math.floor(east / tile); x++) {
    for (let y = Math.floor(south / tile); y <= Math.floor(north / tile); y++) {
      const k = x + '_' + y;
      if (!have.has(k)) continue;
      const segs = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/sd/tiles', k + '.json'), 'utf8'));
      const from = D.segs.length;
      D.segs.push(...segs);
      R.bucketize(buckets, D.segs, from);
      net.build(D, from, { cls, unk: () => false, rule });
    }
  }
  return { D, buckets, net, rule, cls };
}

function search(pack, a, b, risky) {
  const A = pack.net.nearest(pack.D, pack.buckets, { lat: a[0], lng: a[1] }, { cls: pack.cls, G: R.G });
  const B = pack.net.nearest(pack.D, pack.buckets, { lat: b[0], lng: b[1] }, { cls: pack.cls, G: R.G });
  const deadline = Date.now() + R.ROUTE_BUDGET_MS;
  let stateBudget = R.ROUTE_STATE_BUDGET;
  const t0 = Date.now();
  const m0 = process.memoryUsage().heapUsed;
  let parts = null, stat = {}, tries = 0, peak = m0;
  for (const [x, y] of [[A[0], B[0]], [A[2], B[0]], [A[0], B[2]], [A[2], B[2]]]) {
    if (x == null || y == null) continue;
    tries++;
    stat = {};
    parts = pack.net.astar(x, y, { risky, rule: pack.rule, riskyMax: R.RISKY_MAX, deadline, stateBudget, stat });
    stateBudget = Math.max(0, stateBudget - (stat.expanded || 0));
    if (stat.heap && stat.heap > peak) peak = stat.heap;
    if (parts && parts.length) break;
    if (stat.reason === 'timeout' || stat.reason === 'budget') break;
  }
  return { parts, stat, tries, ms: Date.now() - t0, heapMB: Math.round((peak - m0) / 1e6) };
}

function summary(pack, parts) {
  const mask = R.riskyMask(pack.D.segs, parts, pack.rule, pack.cls);
  let dist = 0;
  const names = [];
  parts.forEach(([si]) => {
    const s = pack.D.segs[si];
    dist += s._len;
    const nm = pack.D.names[s[0]] || '';
    if (names[names.length - 1] !== nm) names.push(nm);
  });
  return { ft: R.shownFeet(dist), risky: mask.filter(Boolean).length, names };
}

test('golf cart + Risky to both Snooze shops finishes with no route inside the budget', () => {
  for (const [name, dest] of [['Del Mar', SNOOZE_DEL_MAR], ['Hillcrest', SNOOZE_HILLCREST]]) {
    const pack = loadSd('golf_cart', [PASEO, dest]);
    const got = search(pack, PASEO, dest, true);
    assert.equal(got.parts, null, name + ' must not invent a golf-cart route');
    assert.equal(got.stat.reason, 'none', name + ' reason ' + got.stat.reason);
    assert.ok(got.ms < R.ROUTE_BUDGET_MS, name + ' took ' + got.ms + 'ms');
    assert.ok(got.heapMB < 250, name + ' heap delta ' + got.heapMB + 'MB');
    assert.ok(got.tries <= 4, name);
  }
});

test('golf cart Legal only to Hillcrest Snooze also stops quickly', () => {
  const pack = loadSd('golf_cart', [PASEO, SNOOZE_HILLCREST]);
  const got = search(pack, PASEO, SNOOZE_HILLCREST, false);
  assert.equal(got.parts, null);
  assert.equal(got.stat.reason, 'none');
  assert.ok(got.ms < 1000, 'took ' + got.ms + 'ms');
  assert.ok(got.heapMB < 100, 'heap ' + got.heapMB);
});

test('known San Diego routes keep the same length and streets', () => {
  const cart = loadSd('golf_cart', [PASEO, [32.8555, -117.2518]]);
  const near = search(cart, PASEO, [32.8555, -117.2518], false);
  assert.ok(near.parts && near.parts.length);
  assert.deepEqual(summary(cart, near.parts), { ft: 2732, risky: 0, names: ['Paseo del Ocaso', 'Vallecitos'] });

  const lsv = loadSd('lsv', [PASEO, [32.848, -117.273]]);
  const beach = search(lsv, PASEO, [32.848, -117.273], false);
  const sum = summary(lsv, beach.parts);
  assert.equal(sum.ft, 9114);
  assert.equal(sum.risky, 0);
  assert.deepEqual(sum.names.slice(0, 4), ['Camino del Oro', 'El Paseo Grande', 'Lowry Terrace', 'Lowry Place']);
});

test('a state budget stops a long chain instead of walking all of it', () => {
  const segs = [];
  let x = -117.25;
  for (let i = 0; i < 40; i++) {
    const x2 = x + 0.0002;
    segs.push([0, 'residential', 25, 't', 0, i, i + 1, [[x, 32.85], [x2, 32.85]]]);
    x = x2;
  }
  const D = { segs, meta: {} };
  const net = R.create();
  const rule = { max_posted: 25, cross: true, veh: 'lsv' };
  net.build(D, 0, { cls: () => 0, unk: () => false, rule });
  const stat = {};
  const t0 = Date.now();
  const parts = net.astar(0, 40, { risky: false, rule, stateBudget: 8, stat });
  assert.equal(parts, null);
  assert.equal(stat.reason, 'budget');
  assert.ok(stat.expanded <= 12, 'expanded ' + stat.expanded);
  assert.ok(Date.now() - t0 < 1000);
});

test('a long U-turn still cannot split one faster stretch into legal pieces', () => {
  // Two 50 ft faster pieces are one 100 ft stretch. The side street is longer
  // than HOLD_TRAVEL_M, so a hold that simply expired would price each piece
  // as legal. Legal mode must still refuse that split.
  const LSV = { max_posted: 25, cross: true, veh: 'lsv' };
  function offset(p, eastMeters, northMeters) {
    const target = Math.hypot(eastMeters, northMeters);
    let lo = 0, hi = 0.05;
    for (let i = 0; i < 60; i++) {
      const mid = (lo + hi) / 2;
      const q = [p[0] + mid * (eastMeters / target), p[1] + mid * (northMeters / target)];
      if (R.len([p, q]) < target) lo = mid; else hi = mid;
    }
    const mid = (lo + hi) / 2;
    return [p[0] + mid * (eastMeters / target), p[1] + mid * (northMeters / target)];
  }
  const m = ft => ft / 3.281;
  let p = [-117.2, 32.8];
  const pts = [p];
  for (const feet of [40, 50, 50, 40]) { p = offset(p, m(feet), 0); pts.push(p); }
  const side = offset(pts[2], 0, R.HOLD_TRAVEL_M + 80);
  assert.ok(R.len([pts[2], side]) > R.HOLD_TRAVEL_M);
  const segs = [];
  for (let i = 0; i < 4; i++) {
    const fast = i === 1 || i === 2;
    segs.push([0, fast ? 'secondary' : 'residential', fast ? 99 : 25, fast ? 'i' : 't', 0, i, i + 1, [pts[i], pts[i + 1]]]);
  }
  segs.push([1, 'residential', 25, 't', 0, 2, 9, [pts[2], side]]);
  const D = { segs, meta: {} };
  const net = R.create();
  const cls = s => Rule.cls(s, LSV);
  net.build(D, 0, { cls, unk: () => false, rule: LSV });
  assert.equal(R.shownFeet(segs[1]._len), 50);
  assert.equal(R.shownFeet(segs[2]._len), 50);
  const stat = {};
  const parts = net.astar(0, 4, { risky: false, rule: LSV, stat });
  assert.equal(parts, null, 'legal mode must not use the side street to split the faster road');
  assert.equal(stat.reason, 'none');
});

test('the map runs the search off the main thread and keeps a failed tile on screen', () => {
  const app = fs.readFileSync(path.join(ROOT, 'public/app.js'), 'utf8');
  const worker = fs.readFileSync(path.join(ROOT, 'public/route-worker.js'), 'utf8');
  const sw = fs.readFileSync(path.join(ROOT, 'public/sw.js'), 'utf8');
  const rules = fs.readFileSync(path.join(ROOT, 'public/roadrule.js'), 'utf8');
  assert.match(app, /new Worker\(new URL\('route-worker\.js'/);
  assert.match(app, /ROUTE_BUDGET_MS/);
  assert.match(app, /if\(!roadsOk\)\{showTileError\(\)/);
  assert.match(app, /id="tileRetry"/);
  assert.match(app, /routeStop\(RULE/);
  assert.match(worker, /importScripts\('roadrule\.js', 'router\.js'\)/);
  assert.match(worker, /astarAsync/);
  assert.match(sw, /'route-worker\.js'/);
  assert.match(rules, /function routeStop/);
  assert.equal(Rule.routeStop(Rule.ruleFor(
    JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8')),
    JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8')).find(r => r.id === 'sd'),
    'golf_cart'
  ), {}), 'Under 25 mph roads only: only roads posted 25 mph or under. Turn this off for a street-legal LSV.');
});
