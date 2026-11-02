// Finish flag, trimmed route line, arrival celebration (public/navfx.js, Max t446u).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const X = require('../public/navfx.js');

const line = [[32.79, -117.25], [32.79, -117.249], [32.791, -117.249]]; // east ~94 m, then north ~111 m

test('trim: the line starts under the rider and gets shorter as they drive', () => {
  const full = X.length(line);
  assert.ok(Math.abs(X.length(X.trim(line, 0)) - full) < 0.01);
  const a = X.trim(line, 50), b = X.trim(line, 150);
  assert.ok(Math.abs(X.length(a) - (full - 50)) < 0.5, X.length(a));
  assert.ok(Math.abs(X.length(b) - (full - 150)) < 0.5, X.length(b));
  assert.ok(X.length(b) < X.length(a));
  assert.equal(a.length, 3, 'snap point + the rest');
  assert.ok(Math.abs(a[0][1] - (-117.25 + 0.001 * 50 / X.hav(line[0], line[1]))) < 1e-9);
  assert.ok(X.length(X.trim(line, 9999)) < 0.01, 'past the end: nothing left');
});

test('arrive: once per trip, again after a new trip', () => {
  const seen = [];
  const off = globalThis.GCM.onArrive(d => seen.push(d.place));
  const trip = {};
  assert.equal(X.arrive(trip, { place: 'Crystal Pier' }), true);
  assert.equal(X.arrive(trip, { place: 'Crystal Pier' }), false, 'second fix at the destination');
  X.resetTrip();
  assert.equal(X.arrive(trip, { place: 'Crystal Pier' }), true);
  off();
  assert.deepEqual(seen, ['Crystal Pier', 'Crystal Pier']);
});

test('celebration text: no em dash, life not live', () => {
  assert.equal(X.LINE1, 'You have Arrived!');
  assert.equal(X.LINE2, 'Have a wonderful life you LEGEND 🦄');
  assert.ok(!/\u2014/.test(X.TEXT));
});
