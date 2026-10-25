// Stop connectors and the start-to-first-stop leg use the shared router.
// A straight chord between stops is the La Jolla water bug and must not come back.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const GCMRouter = require('../public/router.js');
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

function fetchImpl(url) {
  const rel = String(url).replace(/^\//, '');
  const p = path.join(ROOT, 'public', rel);
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  const body = JSON.parse(fs.readFileSync(p, 'utf8'));
  return Promise.resolve({ ok: true, status: 200, json: async () => body });
}

function distToChord(lat, lon, a, b) {
  const kx = Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180);
  const bx = (b.lon - a.lon) * kx * 111320;
  const by = (b.lat - a.lat) * 111320;
  const px = (lon - a.lon) * kx * 111320;
  const py = (lat - a.lat) * 111320;
  const L2 = bx * bx + by * by;
  let t = L2 ? (px * bx + py * by) / L2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - t * bx, py - t * by);
}

function maxGap(points, a, b) {
  let m = 0;
  for (const p of points) m = Math.max(m, distToChord(p[0], p[1], a, b));
  return m;
}

function isStopChord(leg, a, b) {
  if (!leg.points || leg.points.length !== 2 || leg.dashed) return false;
  const near = (p, q) => Math.abs(p[0] - q.lat) < 1e-4 && Math.abs(p[1] - q.lon) < 1e-4;
  return near(leg.points[0], a) && near(leg.points[1], b);
}

test('short miss is a dash and a long miss is omitted', () => {
  const net = GCMRouter.create();
  const D = { segs: [], meta: {} };
  const o = { cls: () => 0, unk: () => false, rule: { max_posted: 25, cross: true }, risky: false, G: GCMRouter.G };
  const a = { lat: 32.85, lon: -117.25 };
  const near = { lat: 32.8502, lon: -117.2502 };
  const dash = GCMRouter.routePair(net, D, {}, a, near, o);
  assert.equal(dash.dashed, true);
  assert.equal(dash.points.length, 2);
  const far = { lat: 32.88, lon: -117.22 };
  const skip = GCMRouter.routePair(net, D, {}, a, far, o);
  assert.equal(skip.points, null);
  assert.equal(skip.dashed, false);
});

test('an L-shaped road does not chord the corner', () => {
  const D = {
    meta: {},
    segs: [
      [0, 'residential', 25, 't', 0, 'a', 'b', [[-117.27, 32.85], [-117.26, 32.85]]],
      [0, 'residential', 25, 't', 0, 'b', 'c', [[-117.26, 32.85], [-117.26, 32.86]]],
    ],
  };
  const buckets = {};
  GCMRouter.bucketize(buckets, D.segs, 0);
  const net = GCMRouter.create();
  const o = { cls: () => 0, unk: () => false, rule: { max_posted: 25, cross: true }, risky: false, G: GCMRouter.G };
  net.build(D, 0, o);
  const a = { lat: 32.85, lon: -117.27 };
  const b = { lat: 32.86, lon: -117.26 };
  const leg = GCMRouter.routePair(net, D, buckets, a, b, o);
  assert.equal(leg.dashed, false);
  assert.ok(leg.points && leg.points.length >= 3);
  assert.ok(maxGap(leg.points, a, b) > 200);
  assert.equal(isStopChord(leg, a, b), false);
});

test('La Jolla seals ride stays on roads, not across the water', { timeout: 60000 }, async () => {
  const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
  const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
  const region = regions.find(r => r.id === 'sd');
  const api = await GCMRouter.openRegion(region, rules, 'golf_cart', fetchImpl);
  assert.equal(api.veh, 'golf_cart');
  assert.equal(typeof api.cover, 'function');
  assert.equal(typeof api.segments, 'function');
  assert.equal(api.roadStyle([0, 'path', null, 'c', 0, 'a', 'b', [[0, 0], [1, 1]]]).color, '#0b9fb3');
  assert.equal(api.roadStyle([0, 'primary', 45, 't', 0, 'a', 'b', [[0, 0], [1, 1]]]).color, '#e5484d');
  assert.equal(api.roadStyle([0, 'residential', 25, 't', 0, 'a', 'b', [[0, 0], [1, 1]]]).color, '#12a150');

  const stops = [
    { lat: 32.8488, lon: -117.2736 },
    { lat: 32.8535, lon: -117.2615 },
    { lat: 32.8660, lon: -117.2548 },
  ];
  const legs = await api.legs(stops);
  assert.equal(legs.length, 2);
  legs.forEach((leg, i) => {
    assert.ok(leg.points && leg.points.length > 2, 'leg ' + i);
    assert.equal(leg.dashed, false);
    assert.equal(isStopChord(leg, stops[i], stops[i + 1]), false);
    assert.ok(maxGap(leg.points, stops[i], stops[i + 1]) > 200, 'gap ' + i);
  });

  const from = { lat: 32.8452, lon: -117.2748 };
  const start = await api.legs([from, stops[0]]);
  assert.equal(start.length, 1);
  assert.ok(start[0].points && start[0].points.length > 2);
  assert.equal(isStopChord(start[0], from, stops[0]), false);

  const bayA = { lat: 32.7725, lon: -117.2480 };
  const bayB = { lat: 32.7925, lon: -117.2205 };
  const bay = await api.legs([bayA, bayB]);
  const leg = bay[0];
  assert.equal(isStopChord(leg, bayA, bayB), false);
  if (leg.points) {
    assert.ok(leg.points.length > 2);
    assert.ok(maxGap(leg.points, bayA, bayB) > 200);
  } else {
    assert.equal(leg.points, null);
  }
});
