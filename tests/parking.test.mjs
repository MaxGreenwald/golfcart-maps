// Park-here pins: navigation ends at the parking spot, not the street address.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { parkPoint, withPark, PARK_MAX_M } from '../lib/partner.js';

const require = createRequire(import.meta.url);
const P = require('../public/parking.js');
const worker = fs.readFileSync(new URL('../workers/partner/src/index.js', import.meta.url), 'utf8');

const near = { label: 'Pier', lat: 32.8, lon: -117.25, note: 'Seals', park_lat: 32.8003, park_lon: -117.25 };
const far = { label: 'Pier', lat: 32.8, lon: -117.25, park_lat: 32.81, park_lon: -117.25 };

test('browser and worker agree, and a far pin is dropped', () => {
  assert.equal(P.PARK_MAX_M, PARK_MAX_M);
  assert.deepEqual(P.parkPoint(near), parkPoint(near));
  assert.equal(P.parkPoint(far), null);
  assert.equal(parkPoint(far), null);
  const kept = withPark(near);
  assert.equal(kept.note, 'Seals');
  assert.equal(kept.park_lat, near.park_lat);
  const dropped = withPark(far);
  assert.equal(dropped.park_lat, undefined);
  assert.equal(dropped.label, 'Pier');
  assert.equal(P.dest(near).parked, true);
  assert.equal(P.dest(near).lat, near.park_lat);
  assert.equal(P.dest({ lat: 1, lon: 2 }).parked, false);
  assert.match(worker, /body\.stops\.map\(withPark\)/);
});

test('CarPlay stop coordinates are the parking pin', async () => {
  const park = fs.readFileSync(new URL('../public/parking.js', import.meta.url), 'utf8');
  const src = fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8');
  const access = JSON.stringify({
    slug: 'beachmode', code: 'T', at: Date.now(), shop: { name: 'Beach' },
    experiences: [{ id: 'e1', title: 'Loop', stops: [
      { name: 'Crystal Pier', lat: 32.8, lon: -117.25, park_lat: 32.8002, park_lon: -117.2501 },
    ] }],
    affiliates: [],
  });
  const store = { gcm_partner_access: access };
  const ls = { getItem: k => (k in store ? store[k] : null), setItem() {} };
  const win = {};
  const ctx = { window: win, self: win, localStorage: ls, console, Promise, JSON, Math, Date, isFinite, String, Number };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(park, ctx);
  vm.runInContext(src, ctx);
  const r = await win.GCMCarPlay.stops('e1', 32.8, -117.25);
  assert.equal(r.stops[0].parked, true);
  assert.equal(r.stops[0].lat, 32.8002);
  assert.equal(r.stops[0].place_lat, 32.8);
  assert.equal(r.stops[0].name, 'Crystal Pier');
});
