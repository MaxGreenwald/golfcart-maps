// Local-first search (Max t413u): near results first, far ones never above near ones.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const G = createRequire(import.meta.url)('../public/geosearch.js');
const PB = { lat: 32.797, lon: -117.252 }; // Pacific Beach
const sb = (city, lat, lon) => ({ type: 'Feature', properties: { name: 'Starbucks', city }, geometry: { coordinates: [lon, lat] } });
const ms = (city, lat, lon) => ({ type: 'Feature', properties: { name: 'Main St', city }, geometry: { coordinates: [lon, lat] } });
const fake = (bounded, unbounded) => async u => (u.includes('bbox=') ? bounded : unbounded);

test('bias: my location beats start beats map center', () => {
  const me = { lat: 1, lon: 1 }, st = { lat: 2, lon: 2 }, c = { lat: 3, lon: 3 };
  assert.equal(G.biasPoint(me, st, c), me);
  assert.equal(G.biasPoint(null, st, c), st);
  assert.equal(G.biasPoint(null, null, c), c);
});

test('geocoder URL carries proximity and a ~50 mi box around the bias point', () => {
  const u = G.photonUrl('Starbucks', PB);
  assert.match(u, /lat=32\.797&lon=-117\.252/);
  const b = u.match(/bbox=([^&]+)/)[1].split(',').map(Number);
  assert.ok(b[0] < PB.lon && b[2] > PB.lon && b[1] < PB.lat && b[3] > PB.lat);
  assert.ok(G.miles({ lat: b[1], lon: b[0] }, PB) < 80);
  assert.match(G.nominatimUrl('x', PB), /bounded=1/);
});

test('Starbucks near San Diego: nearest first, Seattle and New York not above them', async () => {
  const res = await G.remote('Starbucks', PB, fake({ features: [sb('New York', 40.75, -73.99), sb('San Diego', 32.75, -117.22), sb('Seattle', 47.6, -122.33), sb('San Diego', 32.80, -117.25)] }));
  const r = G.rank(res, PB);
  assert.deepEqual(r.near.map(x => x.lat), [32.80, 32.75]);
  assert.equal(r.far.length, 2);
  assert.ok(r.near.every(n => n.mi < 50) && r.far.every(f => f.mi > 50));
});

test('Main St: local street index and remote merge, ranked by distance', () => {
  const r = G.rank([{ name: 'Main St', lat: 33.19, lon: -117.37, score: 0 }, { name: 'Main St', lat: 32.70, lon: -117.17, score: 0.5 }, { name: 'Main St', lat: 34.05, lon: -118.24, score: 0 }], PB);
  assert.equal(r.near[0].lat, 32.70);
  assert.equal(r.far[0].lat, 34.05);
});

test('nothing nearby: falls back to an unbounded search (shown under "Farther away")', async () => {
  const res = await G.remote('Space Needle', PB, fake({ features: [] }, { features: [ms('Seattle', 47.62, -122.35)] }));
  const r = G.rank(res, PB);
  assert.equal(r.near.length, 0);
  assert.equal(r.far.length, 1);
});

test('stale request aborts propagate so old results never land', async () => {
  const ac = new AbortController(); ac.abort();
  await assert.rejects(G.remote('x', PB, async (u, s) => { if (s.aborted) throw new Error('aborted'); }, ac.signal));
});
