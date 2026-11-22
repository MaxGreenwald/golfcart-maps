// Outside our mapped towns (Max t590u/t591u): any US spot still gets a route from general road data, with one warning.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const A = require('../public/anywhere.js');
const REGIONS = JSON.parse(readFileSync(new URL('../public/data/regions.json', import.meta.url)));
const BOISE = JSON.parse(readFileSync(new URL('./fixtures/valhalla_boise.json', import.meta.url)));
const ll = (lat, lng) => ({ lat, lng });

test('US check: unmapped US towns are in; Canada, Mexico and overseas are out', () => {
  for (const [lat, lon] of [[43.615, -116.2], [30.27, -97.74], [38.47, -98.78], [31.77, -106.44], [42.33, -83.05], [24.55, -81.78],
    [21.3, -157.85], [61.2, -149.9], [58.3, -134.4], [18.46, -66.1], [44.8, -68.8], [32.85, -117.27]]) assert.ok(A.inUS(lat, lon), `${lat},${lon} should be US`);
  for (const [lat, lon] of [[43.65, -79.38], [49.28, -123.12], [31.69, -106.42], [32.5, -117.0], [42.3, -83.02], [45.96, -66.64],
    [25.05, -77.35], [51.5, -0.1], [43.09, -79.08]]) assert.ok(!A.inUS(lat, lon), `${lat},${lon} should not be US`);
});

test('a point inside a town box finds that town; Boise finds none', () => {
  assert.equal(A.regionCovering(REGIONS, 32.85, -117.27).id, 'sd');
  assert.equal(A.regionCovering(REGIONS, 43.615, -116.2), null);
  assert.equal(A.regionCovering(REGIONS, 30.2672, -97.7431), null, 'Austin is not inside Horseshoe Bay');
});

test('request keeps off freeways and prefers smaller roads', () => {
  const q = A.request(ll(43.615, -116.2023), ll(43.608, -116.193), 'lsv');
  assert.equal(q.costing, 'motor_scooter');  // Valhalla scooter profile: no motorways
  assert.equal(q.costing_options.motor_scooter.use_primary, 0);
  assert.equal(q.costing_options.motor_scooter.top_speed, 56);
  assert.equal(A.request(ll(1, 1), ll(1, 1.01), 'golf_cart').costing_options.motor_scooter.top_speed, 40);
});

test('Valhalla trip becomes app segments with street names, end to end', () => {
  const { names, segs } = A.toSegs(BOISE.trip);
  assert.ok(segs.length >= 2);
  assert.ok(names.includes('West Main Street'));
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i];
    assert.equal(s[3], 'g'); assert.equal(s[2], 0); assert.ok(s[7].length >= 2);
    if (i) assert.deepEqual(segs[i - 1][7].at(-1), s[7][0], 'segments join');
    if (i) assert.equal(segs[i - 1][6], s[5], 'node ids chain');
  }
  const first = segs[0][7][0], last = segs.at(-1)[7].at(-1);
  assert.ok(Math.abs(first[1] - 43.615) < 0.002 && Math.abs(first[0] + 116.2023) < 0.002, 'starts at A');
  assert.ok(Math.abs(last[1] - 43.608) < 0.002 && Math.abs(last[0] + 116.193) < 0.002, 'ends at B');
});

test('general segments count as allowed (no risky marks) under both vehicle rules', () => {
  const R = require('../public/roadrule.js');
  const s = A.toSegs(BOISE.trip).segs[0];
  for (const veh of ['lsv', 'golf_cart']) assert.notEqual(R.cls(s, R.ruleFor({ _any: A.RULES }, { state: '_any' }, veh)), 3);
});

test('route(): ok with a fake server; too far, server error and network failure are reported', async () => {
  const ok = async () => ({ ok: true, json: async () => BOISE });
  const r = await A.route(ll(43.615, -116.2023), ll(43.608, -116.193), { fetch: ok });
  assert.equal(r.ok, true); assert.ok(r.segs.length);
  let called = false;
  const far = await A.route(ll(43.6, -116.2), ll(44.2, -116.2), { fetch: async () => { called = true; } });
  assert.deepEqual(far, { ok: false, reason: 'too_far' }); assert.equal(called, false);
  const bad = await A.route(ll(43.615, -116.2023), ll(43.608, -116.193), { fetch: async () => ({ ok: false, json: async () => ({ error_code: 442 }) }) });
  assert.deepEqual(bad, { ok: false, reason: 'no_route' });
  const down = await A.route(ll(43.615, -116.2023), ll(43.608, -116.193), { fetch: async () => { throw new Error('offline'); } });
  assert.deepEqual(down, { ok: false, reason: 'network' });
});

test('route(): POST text/plain so there is no preflight and the service worker never caches it', async () => {
  let seen;
  await A.route(ll(43.615, -116.2023), ll(43.608, -116.193), { fetch: async (u, init) => { seen = { u, init }; return { ok: true, json: async () => BOISE }; } });
  assert.equal(seen.u, A.ENDPOINT); assert.equal(seen.init.method, 'POST'); assert.equal(seen.init.headers['Content-Type'], 'text/plain');
});

test('warning copy: short, plain, says what is missing and what to check; no em dashes', () => {
  for (const t of [A.WARNING, A.BANNER, A.US_ONLY, A.TOO_FAR]) { assert.ok(!t.includes('\u2014'), t); assert.ok(t.length < 200, t); }
  assert.match(A.WARNING, /golf cart and LSV speed data/);
  assert.match(A.WARNING, /isn\u2019t checked against local rules/);
  assert.match(A.WARNING, /posted speed limits and local laws/);
});
