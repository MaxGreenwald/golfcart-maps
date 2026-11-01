// Nearest-stop start for partner experiences (Max t441u).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const S = createRequire(import.meta.url)('../public/stoporder.js');

// Six stops in a line running north along the PB coast (stop 1 south, stop 6 north).
const line = [0, 1, 2, 3, 4, 5].map(i => ({ label: 'S' + (i + 1), lat: 32.79 + i * 0.006, lon: -117.255 }));

test('rider near stop 3 of 6 starts at 3', () => {
  const p = S.plan(line, { lat: line[2].lat + 0.0005, lon: -117.254 }, true);
  assert.equal(p.order[0], 2);
  assert.equal(p.reordered, true);
  assert.deepEqual([...p.order].sort(), [0, 1, 2, 3, 4, 5]);
  // From stop 3 the short side is south (1,2), then north 4..6.
  assert.deepEqual(p.order, [2, 1, 0, 3, 4, 5]);
});

test('rider near stop 5 finishes the short north side first', () => {
  const p = S.plan(line, { lat: line[4].lat, lon: -117.254 }, true);
  assert.deepEqual(p.order, [4, 5, 3, 2, 1, 0]);
});

test('setting off, or no location: partner order', () => {
  const near3 = { lat: line[2].lat, lon: -117.254 };
  assert.deepEqual(S.plan(line, near3, false).order, [0, 1, 2, 3, 4, 5]);
  assert.equal(S.plan(line, near3, false).reordered, false);
  assert.deepEqual(S.plan(line, null, true).order, [0, 1, 2, 3, 4, 5]);
});

test('rider nearest stop 1 keeps partner order', () => {
  const p = S.plan(line, { lat: 32.785, lon: -117.255 }, true);
  assert.deepEqual(p.order, [0, 1, 2, 3, 4, 5]);
  assert.equal(p.reordered, false);
});

test('loop wraps around', () => {
  // Square loop: 1 SW, 2 NW, 3 NE, 4 SE, 5 back near 1.
  const loop = [[32.79, -117.26], [32.80, -117.26], [32.80, -117.25], [32.79, -117.25], [32.7902, -117.2598]]
    .map(([lat, lon], i) => ({ label: 'L' + (i + 1), lat, lon }));
  assert.equal(S.isLoop(loop), true);
  assert.equal(S.isLoop(line), false);
  const p = S.plan(loop, { lat: 32.8001, lon: -117.2501 }, true); // at stop 3
  assert.equal(p.order[0], 2);
  assert.match(p.mode, /^loop/);
  assert.equal(p.order.length, 5);
  // Wrapping: consecutive partner neighbors, mod 5.
  const step = (p.order[1] - p.order[0] + 5) % 5;
  for (let i = 1; i < 5; i++) assert.equal((p.order[i] - p.order[i - 1] + 5) % 5, step);
});

test('stops without pins go last and keep order', () => {
  const s = [...line.slice(0, 3), { label: 'nopin' }];
  const p = S.plan(s, { lat: line[2].lat, lon: -117.254 }, true);
  assert.deepEqual(p.order, [2, 1, 0, 3]);
});
