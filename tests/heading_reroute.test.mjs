// Max t433u: rerouting while driving the "wrong" way must start ahead of you (continue to the next
// corner, then turn), never with an immediate U-turn on the street you are on. Standing still keeps
// the old behavior (any direction).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const R = require('../public/router.js');
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
function fetchImpl(url) {
  const p = path.join(ROOT, 'public', String(url).replace(/^\//, ''));
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  const body = JSON.parse(fs.readFileSync(p, 'utf8'));
  return Promise.resolve({ ok: true, status: 200, json: async () => body });
}
const brg = (a, b) => R.bearingDeg([a[1], a[0]], [b[1], b[0]]);
const diff = (a, b) => Math.abs(((a - b) % 360 + 540) % 360 - 180);
// Bearing of the route from its start to the point `m` metres along it.
function startBearing(points, m) {
  let d = 0;
  for (let i = 1; i < points.length; i++) {
    d += R.hav([points[i - 1][1], points[i - 1][0]], [points[i][1], points[i][0]]);
    if (d >= m) return brg(points[0], points[i]);
  }
  return brg(points[0], points[points.length - 1]);
}
async function api() {
  const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
  const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
  const region = (regions.regions || regions).find(r => r.id === 'sd');
  return R.openRegion(region, rules, 'golf_cart', fetchImpl);
}
const ME = { lat: 32.7973, lon: -117.24764 };  // mid-block on Hornblend Street, Pacific Beach (runs ~105/285 deg)
const DEST = { lat: 32.7930, lon: -117.2560 };  // to the west and south

function noReversal(points, upTo) {
  let d = 0;
  const b0 = startBearing(points, 10);
  for (let i = 1; i < points.length && d < upTo; i++) {
    const p = points[i - 1], q = points[i], s = R.hav([p[1], p[0]], [q[1], q[0]]);
    d += s;
    if (s > 2) assert.ok(diff(brg(p, q), b0) < 135, 'turned back at ' + d.toFixed(0) + ' m');
  }
}

test('standing still: unchanged, any direction allowed (starts at the nearer corner)', async () => {
  const a = await api();
  const leg = await a.trip(ME, DEST);
  assert.ok(!leg.ahead);
  assert.ok(leg.points && leg.points.length > 2);
});

test('driving the wrong way (east): continue on Hornblend to the corner, then turn; no U-turn', async () => {
  const a = await api();
  const leg = await a.trip(ME, DEST, { heading: 105 });
  assert.ok(leg.ahead, 'used the heading-aware start');
  assert.ok(diff(startBearing(leg.points, 15), 105) < 40, 'first stretch goes the way you drive: ' + startBearing(leg.points, 15));
  assert.equal(leg.runs[0].name, 'Hornblend Street', 'first step: continue on the street you are on');
  const p0 = leg.points[0];
  assert.ok(R.hav([p0[1], p0[0]], [ME.lon, ME.lat]) < 15, 'starts where you are, not at a corner behind');
  noReversal(leg.points, 40);
});

test('driving the right way (west): goes straight on, never back to the corner behind', async () => {
  const a = await api();
  const plain = await a.trip(ME, DEST);
  const leg = await a.trip(ME, DEST, { heading: 285 });
  assert.ok(leg.ahead);
  assert.ok(diff(startBearing(leg.points, 15), 285) < 40, String(startBearing(leg.points, 15)));
  // Root cause in the field: the plain start snapped to the nearer block end even when it was behind.
  const behind = plain.points[0];
  assert.ok(diff(brg([ME.lat, ME.lon], behind), 285) > 90, 'plain route starts behind a westbound driver');
  noReversal(leg.points, 60);
});

test('aheadStart: no heading, no ahead start', () => {
  assert.equal(R.aheadStart({ segs: [] }, {}, { lat: ME.lat, lng: ME.lon }, null, {}), null);
});
