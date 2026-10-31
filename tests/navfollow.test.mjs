// Off-route timing, debounce, and heading choice for live navigation (public/navfollow.js).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const F = require('../public/navfollow.js');

test('one far fix does not reroute; 5 s off route does, once', () => {
  const t = F.offTracker();
  assert.equal(t.update(80, 0), false);
  assert.equal(t.update(80, 2000), false);
  assert.equal(t.update(80, 5000), true);
  assert.equal(t.update(80, 5100), false, 'cooldown');
  assert.equal(t.update(80, 9000), false, 'still in cooldown');
});

test('coming back on route resets the clock', () => {
  const t = F.offTracker();
  t.update(80, 0);
  assert.equal(t.update(10, 3000), false);
  assert.equal(t.update(80, 4000), false);
  assert.equal(t.update(80, 8500), false);
  assert.equal(t.update(80, 9000), true);
});

test('30 m is the default edge and constants are tunable', () => {
  assert.equal(F.C.OFF_ROUTE_M, 30);
  assert.equal(F.C.OFF_ROUTE_MS, 5000);
  const t = F.offTracker();
  assert.equal(t.update(29, 0), false);
  assert.equal(t.update(29, 9999), false);
  const q = F.offTracker({ offM: 10, offMs: 100, cooldownMs: 0 });
  q.update(11, 0);
  assert.equal(q.update(11, 100), true);
});

test('heading: GPS course when moving, compass when stopped, none when unknown', () => {
  assert.equal(F.pickHeading({ latitude: 32.8, longitude: -117.2, heading: 90, speed: 5 }, 10, null), 90);
  assert.equal(F.pickHeading({ latitude: 32.8, longitude: -117.2, heading: 90, speed: 0 }, 10, null), 10);
  assert.equal(F.pickHeading({ latitude: 32.8, longitude: -117.2, heading: NaN, speed: 0 }, null, null), null);
  assert.equal(F.pickHeading({ latitude: 32.8, longitude: -117.2, heading: null, speed: null }, null, null), null);
  // No course from GPS but we moved ~111 m north: bearing between fixes.
  const h = F.pickHeading({ latitude: 32.801, longitude: -117.2, heading: null, speed: null }, null, [32.8, -117.2]);
  assert.ok(h < 1 || h > 359, h);
});

test('compass from DeviceOrientation', () => {
  assert.equal(F.compassFrom({ webkitCompassHeading: 270 }), 270);
  assert.equal(F.compassFrom({ absolute: true, alpha: 90 }), 270);
  assert.equal(F.compassFrom({ absolute: false, alpha: 90 }), null);
  assert.equal(F.compassFrom(null), null);
});
