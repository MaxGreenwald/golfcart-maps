// Shop off-limits zones (public/offlimits.js): validation, which roads count as inside, warnings,
// and the shared router (public/router.js) going around a zone on real Pacific Beach roads.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const O = require('../public/offlimits.js');
const R = require('../public/router.js');
const seg = pts => [0, '', 25, 'r', 0, 'a', 'b', pts.map(([lat, lon]) => [lon, lat])];
const box = (c, d, extra = {}) => ({ kind: 'area', name: 'Block', points: [[c[0] - d, c[1] - d], [c[0] - d, c[1] + d], [c[0] + d, c[1] + d], [c[0] + d, c[1] - d]], ...extra });

test('clean: kinds, names, point counts, size', () => {
  assert.ok(O.clean(box([32.8, -117.25], 0.001)).zone);
  assert.match(O.clean({ kind: 'circle', name: 'x', points: [] }).error, /area or a road segment/);
  assert.match(O.clean({ kind: 'area', name: ' ', points: [] }).error, /Name/);
  assert.match(O.clean({ kind: 'area', name: 'x', points: [[1, 1], [1, 2]] }).error, /at least 3/);
  assert.match(O.clean({ kind: 'line', name: 'x', points: [[1, 1]] }).error, /at least 2/);
  assert.match(O.clean({ kind: 'line', name: 'x', points: [[1, 1], [200, 1]] }).error, /coordinates/);
  assert.match(O.clean(box([32.8, -117.25], 0.05)).error, /too big/);
  const z = O.clean({ kind: 'line', name: '  Ocean   Front Walk ', note: 'No carts.', points: [{ lat: 32.8, lon: -117.25 }, [32.801, -117.25]] }).zone;
  assert.equal(z.name, 'Ocean Front Walk');
  assert.deepEqual(z.points, [[32.8, -117.25], [32.801, -117.25]]);
});

test('a road runs inside an area, along a drawn segment, but not across it', () => {
  const area = O.segAvoid([box([32.85, -117.275], 0.002)]);
  assert.equal(area(seg([[32.85, -117.276], [32.85, -117.274]])), true);
  assert.equal(area(seg([[32.86, -117.276], [32.86, -117.274]])), false);
  const line = O.segAvoid([{ kind: 'line', name: 'Boardwalk', points: [[32.80, -117.25], [32.81, -117.25]] }]);
  assert.equal(line(seg([[32.802, -117.25], [32.805, -117.25]])), true, 'along it');
  assert.equal(line(seg([[32.805, -117.25], [32.805, -117.248]])), false, 'a cross street at the corner');
  assert.equal(line(seg([[32.805, -117.25], [32.805, -117.2498]])), false, 'a short cross stub');
  assert.equal(line(seg([[32.802, -117.2495], [32.805, -117.2495]])), false, 'a parallel street 45 m away');
  assert.equal(O.segAvoid([]), null);
});

test('route hits, stops inside, live nearness and the warning line', () => {
  const zones = [box([32.85, -117.275], 0.002, { id: 'z', name: 'Pier lot', note: 'Walkers only.' })];
  const hits = O.routeHits([[32.846, -117.275], [32.854, -117.275]], zones);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].name, 'Pier lot');
  assert.ok(hits[0].meters > 400 && hits[0].meters < 470);
  assert.deepEqual(O.routeHits([[32.846, -117.28], [32.854, -117.28]], zones), []);
  assert.deepEqual(O.stopsInside([{ label: 'A', lat: 32.85, lon: -117.275 }, { label: 'B', lat: 32.9, lon: -117.2 }], zones), [{ index: 0, label: 'A', zone: 'Pier lot' }]);
  assert.equal(O.near({ lat: 32.85, lon: -117.275 }, zones).meters, 0);
  assert.ok(O.near({ lat: 32.8522, lon: -117.275 }, zones, 40));
  assert.equal(O.near({ lat: 32.86, lon: -117.275 }, zones, 40), null);
  assert.equal(O.warnText(hits), '⛔ This route goes through Pier lot, which the shop marked off limits. There is no other legal way here. Shop note: Walkers only.');
  assert.equal(O.warnText([]), '');
});

function fetchImpl(url) {
  const p = path.join(ROOT, 'public', String(url).replace(/^\//, ''));
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  return Promise.resolve({ ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(p, 'utf8')) });
}
const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
const SD = regions.find(r => r.id === 'sd');
const A = { lat: 32.7965, lon: -117.2540 }, B = { lat: 32.8010, lon: -117.2430 }; // Pacific Beach grid
const streets = leg => [...new Set((leg.runs || []).map(r => r.name).filter(Boolean))];

test('router goes around an off-limits block when the grid has another legal way', async () => {
  const plain = await R.openRegion(SD, rules, 'golf_cart', fetchImpl);
  const [leg] = await plain.legs([A, B]);
  assert.ok(leg && leg.points && leg.points.length > 5);
  const mid = leg.points[Math.floor(leg.points.length / 2)];
  const zone = box(mid, 0.0007, { id: 'z1', name: 'Block party' });
  assert.ok(O.routeHits(leg.points, [zone]).length, 'the plain route goes through the block');
  const avoid = await R.openRegion(SD, rules, 'golf_cart', fetchImpl, { avoid: O.segAvoid([zone]) });
  const [leg2] = await avoid.legs([A, B]);
  assert.ok(leg2 && leg2.points);
  assert.deepEqual(O.routeHits(leg2.points, [zone]), [], 'the new route stays out: ' + streets(leg2).join(' > '));
  assert.notDeepEqual(streets(leg2), streets(leg));
  // Free-ride trip() takes the same graph.
  const t = await avoid.trip(A, B);
  assert.deepEqual(O.routeHits(t.points, [zone]), []);
});

test('a drawn road segment is avoided, and a stop inside a zone is still reached (with a warning)', async () => {
  const plain = await R.openRegion(SD, rules, 'golf_cart', fetchImpl);
  const [leg] = await plain.legs([A, B]);
  const run = leg.runs.find(r => r.name === 'Cass Street') || leg.runs.filter(r => r.name).sort((a, b) => b.points.length - a.points.length)[0];
  const lineZone = { id: 'z2', kind: 'line', name: run.name, points: run.points };
  const avoid = await R.openRegion(SD, rules, 'golf_cart', fetchImpl, { avoid: O.segAvoid([lineZone]) });
  const [leg2] = await avoid.legs([A, B]);
  assert.deepEqual(O.routeHits(leg2.points, [lineZone]), [], 'stays off ' + run.name + ': ' + streets(leg2).join(' > '));

  const dest = box([B.lat, B.lon], 0.0008, { id: 'z3', name: 'Dest block' });
  const api = await R.openRegion(SD, rules, 'golf_cart', fetchImpl, { avoid: O.segAvoid([dest]) });
  const [leg3] = await api.legs([A, B]);
  assert.ok(leg3 && leg3.points, 'still routes when there is no way around');
  assert.equal(O.routeHits(leg3.points, [dest]).length, 1);
  assert.match(O.warnText(O.routeHits(leg3.points, [dest])), /no other legal way/);
});

test('no zones: openRegion routes exactly as before', async () => {
  const a = await R.openRegion(SD, rules, 'golf_cart', fetchImpl);
  const b = await R.openRegion(SD, rules, 'golf_cart', fetchImpl, { avoid: O.segAvoid([]) });
  const [l1] = await a.legs([A, B]);
  const [l2] = await b.legs([A, B]);
  assert.deepEqual(l2.points, l1.points);
});
