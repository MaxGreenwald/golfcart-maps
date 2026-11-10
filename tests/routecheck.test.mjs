// Route check while editing: miles, time, battery, and legal-road flags.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
require('../public/router.js');
const RC = require('../public/routecheck.js');

function fetchImpl(url) {
  const rel = String(url).replace(/^\//, '');
  try {
    const body = readFileSync(join(root, 'public', rel), 'utf8');
    return Promise.resolve({ ok: true, json: async () => JSON.parse(body) });
  } catch {
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  }
}

test('one mile is about 5 min and 3% of a 30 mi golf cart charge', () => {
  const s = RC.summarize(
    [{ label: 'A', lat: 1, lon: 1 }, { label: 'B', lat: 2, lon: 2 }],
    [{ points: [[32.8, -117.25], [32.8 + 1 / 69, -117.25]], dashed: false }],
    'golf_cart',
  );
  assert.ok(Math.abs(s.miles - 1) < 0.02, s.miles);
  assert.equal(s.mph, 12);
  assert.ok(Math.abs(s.minutes - 5) < 0.2, s.minutes);
  assert.ok(Math.abs(s.batteryPct - (100 / 30)) < 0.2, s.batteryPct);
  assert.equal(s.flags.length, 0);
  const text = RC.lines(s).headline;
  assert.match(text, /About 1\.0 mi/);
  assert.match(text, /5 min at 12 mph/);
  assert.match(text, /3% of a 30 mi charge/);
  assert.doesNotMatch(RC.html(s), /\u2014/);
});

test('a missing hop is flagged and a short dashed gap is not', () => {
  const stops = [
    { label: 'Shop', lat: 32.8, lon: -117.2 },
    { label: 'Cove', lat: 32.81, lon: -117.21 },
    { label: 'Inland', lat: 33.2, lon: -117.0 },
  ];
  const s = RC.summarize(stops, [
    { points: [[32.8, -117.2], [32.81, -117.21]], dashed: true },
    { points: null, dashed: false },
  ], 'lsv');
  assert.equal(s.gaps, 1);
  assert.equal(s.flags.length, 1);
  assert.equal(s.flags[0].label, 'Inland');
  assert.equal(s.flags[0].index, 2);
  assert.match(RC.html(s), /Stop 3 Inland: no legal street-legal LSV route/);
  assert.match(RC.lines(s).detail, /short gap/);
  assert.match(RC.lines(s).detail, /18 mph|Posted signs/);
  assert.match(RC.lines(s).headline, /18 mph/);
});

test('fewer than two stops does not invent a route', () => {
  const s = RC.summarize([{ label: 'Only', lat: 1, lon: 2 }], [], 'golf_cart');
  assert.equal(s.miles, 0);
  assert.match(RC.lines(s).headline, /Add two placed stops/);
});

test('San Diego legal roads: a 25 mph hop counts, open water does not', async () => {
  const near = [
    { label: 'South', lat: 32.66683, lon: -117.24285 },
    { label: 'North', lat: 32.67643, lon: -117.24319 },
  ];
  const cart = await RC.check({ regionId: 'sd', vehicle: 'golf_cart', stops: near, fetchImpl });
  assert.equal(cart.flags.length, 0, JSON.stringify(cart.flags));
  assert.ok(cart.miles > 0.4 && cart.miles < 3, cart.miles);
  assert.match(RC.html(cart), /12 mph/);

  const lsv = await RC.check({ regionId: 'sd', vehicle: 'lsv', stops: near, fetchImpl });
  assert.equal(lsv.flags.length, 0);
  assert.match(RC.html(lsv), /18 mph/);

  const blocked = await RC.check({
    regionId: 'sd', vehicle: 'golf_cart', stops: [near[0], { label: 'Offshore', lat: 32.67, lon: -117.55 }], fetchImpl,
  });
  assert.equal(blocked.flags.length, 1);
  assert.equal(blocked.flags[0].label, 'Offshore');
  assert.match(RC.html(blocked), /no legal golf cart route/);
});

test('Grand Ave: an LSV shop gets a route on the 35 mph street', async () => {
  const stops = [
    { label: 'Grand and Mission', lat: 32.7965, lon: -117.2525 },
    { label: 'Grand and Ingraham', lat: 32.7990, lon: -117.2330 },
  ];
  const lsv = await RC.check({ regionId: 'sd', vehicle: 'lsv', stops, fetchImpl });
  assert.equal(lsv.flags.length, 0, JSON.stringify(lsv));
  assert.ok(lsv.miles > 0.5, lsv.miles);
  const cart = await RC.check({ regionId: 'sd', vehicle: 'golf_cart', stops, fetchImpl });
  // Golf carts are not allowed on this posted-35 street. A route, if one exists, has to use other legal roads.
  if (cart.flags.length) assert.equal(cart.flags[0].reason, 'no_legal_route');
  else assert.ok(cart.miles > 0);
});
