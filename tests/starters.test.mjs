// node --test tests/starters.test.mjs
// Ready-made rides: a dashed gap is dropped, and every live region file is a legal loop
// for that vehicle (re-routed for 30a; schema for the rest).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { placesFromPois, clusters, pickLoops, THEMES, TOWN_THEME, legIsLegal } from '../lib/starters.js';

const require = createRequire(import.meta.url);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const regions = JSON.parse(readFileSync(path.join(root, 'public/data/regions.json'), 'utf8'));

function leg(miles) {
  // ~miles of northbound points so the length check can pass or fail on purpose.
  const steps = 4;
  const dLat = (miles * 1609.344 / 6371000) * (180 / Math.PI) / steps;
  const points = [];
  for (let i = 0; i <= steps; i++) points.push([30 + dLat * i, -86]);
  return { dashed: false, points };
}

const beaches = [
  { name: 'Grayton Beach', kind: 'beach', lat: 30.320, lon: -86.180 },
  { name: 'Seaside Beach', kind: 'beach', lat: 30.324, lon: -86.176 },
  { name: 'Inlet Beach', kind: 'beach', lat: 30.316, lon: -86.174 },
];

test('a dashed gap is not a ride, and a legal loop is', async () => {
  const dashed = await pickLoops(beaches, async () => [leg(1), { dashed: true, points: [[30, -86], [30.01, -86]] }, leg(1)], { town: false });
  assert.equal(dashed.length, 0);
  const beachOnly = THEMES.filter(t => t.key === 'beach');
  const ok = await pickLoops(beaches, async () => [leg(1), leg(1), leg(1)], { themes: beachOnly, town: false });
  assert.equal(ok.length, 1);
  assert.equal(ok[0].key, 'beach');
  assert.equal(ok[0].title, 'Beach loop');
  assert.equal(ok[0].stops.length, 3);
  assert.ok(ok[0].miles >= 0.4 && ok[0].miles <= 18);
  assert.equal(legIsLegal({ dashed: false, points: [[1, 2]] }), false);
});

test('places skip schools and duplicate names; a city hall is not an around-town stop', () => {
  const pois = [
    ['Grayton Beach', 'beach', -86.1, 30.3, ''],
    ['Grayton Beach', 'beach', -86.2, 30.4, ''],
    ['Seaside School', 'school', -86.1, 30.31, ''],
    ['', 'restaurant', -86.1, 30.3, ''],
  ];
  const places = placesFromPois(pois);
  assert.deepEqual(places.map(p => p.name), ['Grayton Beach']);
  const halls = [
    { name: 'Fruitland Park City Hall', kind: 'townhall', lat: 28.858, lon: -81.912 },
    { name: 'Fruitland Park Library', kind: 'library', lat: 28.857, lon: -81.909 },
    { name: 'Lake Griffin State Park Campground', kind: 'caravan_site', lat: 28.859, lon: -81.902 },
  ];
  assert.equal(clusters(halls, TOWN_THEME).length, 0);
  assert.ok(THEMES.some(t => t.key === 'beach' && t.key !== 'town'));
});

test('every live region has starter rides with finite stops, and 30a still routes legal', async () => {
  const keys = new Set(['beach', 'food', 'sunset', 'town']);
  for (const region of regions) {
    const p = path.join(root, 'public/data', region.id, 'starters.json');
    assert.ok(existsSync(p), region.id);
    const data = JSON.parse(readFileSync(p, 'utf8'));
    assert.equal(data.region, region.id);
    for (const veh of ['golf_cart', 'lsv']) {
      const rides = data.vehicles[veh];
      assert.ok(Array.isArray(rides) && rides.length <= 3, region.id + ' ' + veh);
      for (const ride of rides) {
        assert.ok(keys.has(ride.key), ride.key);
        assert.ok(ride.title && ride.description);
        assert.ok(ride.miles >= 0.4 && ride.miles <= 18);
        assert.equal(ride.stops.length, 3);
        for (const s of ride.stops) {
          assert.ok(s.label);
          assert.ok(Number.isFinite(s.lat) && Math.abs(s.lat) <= 90);
          assert.ok(Number.isFinite(s.lon) && Math.abs(s.lon) <= 180);
        }
        assert.ok(!JSON.stringify(ride).includes('—'));
      }
    }
  }
  const router = require('../public/router.js');
  const rules = JSON.parse(readFileSync(path.join(root, 'public/data/rules.json'), 'utf8'));
  const region = regions.find(r => r.id === '30a');
  const pois = JSON.parse(readFileSync(path.join(root, 'public/data/30a/pois.json'), 'utf8'));
  const places = placesFromPois(pois);
  const fileFetch = async url => {
    const rel = String(url || '').replace(/^\//, '');
    const fp = path.join(root, 'public', rel);
    if (!existsSync(fp)) return { ok: false, json: async () => null };
    return { ok: true, json: async () => JSON.parse(readFileSync(fp, 'utf8')) };
  };
  const saved = JSON.parse(readFileSync(path.join(root, 'public/data/30a/starters.json'), 'utf8'));
  for (const veh of ['golf_cart', 'lsv']) {
    const reg = await router.openRegion(region, rules, veh, fileFetch);
    const rides = await pickLoops(places, stops => reg.legs(stops));
    assert.deepEqual(rides, saved.vehicles[veh], veh);
    for (const ride of rides) {
      const closed = ride.stops.map(s => ({ lat: s.lat, lon: s.lon }));
      closed.push(closed[0]);
      const legs = await reg.legs(closed);
      assert.equal(legs.length, 3);
      assert.ok(legs.every(legIsLegal), ride.title);
    }
  }
});
