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

// Heading-up (Max t412u): the map bearing follows the road ahead, ignores tiny changes, and eases the short way.
const N = require('../public/nav.js');
test('route bearing: east-going road is ~90, then the north leg after the corner is ~0', () => {
  const route = { pts: [[32.8, -117.21], [32.8, -117.2], [32.81, -117.2]] };
  const b1 = F.routeBearing(route, [32.8, -117.205], 25, N.project);
  assert.ok(Math.abs(b1 - 90) < 1, b1);
  const b2 = F.routeBearing(route, [32.805, -117.2], 25, N.project);
  assert.ok(b2 < 1 || b2 > 359, b2);
  assert.equal(F.routeBearing(route, [32.9, -117.0], 25, N.project), null, 'off route: no route bearing');
  assert.equal(F.routeBearing(null, [32.8, -117.2]), null);
});

test('course heading ignores the compass', () => {
  assert.equal(F.courseHeading({ latitude: 32.8, longitude: -117.2, heading: 45, speed: 5 }, null), 45);
  assert.equal(F.courseHeading({ latitude: 32.8, longitude: -117.2, heading: null, speed: 0 }, null), null);
});

test('next bearing: deadband, short way round, unwrapped', () => {
  assert.equal(F.nextBearing(null, 90), 90);
  assert.equal(F.nextBearing(90, 93), 90, 'under the deadband');
  assert.equal(F.nextBearing(90, 180), 180);
  assert.equal(F.nextBearing(350, 10), 370, '350 -> 10 turns +20, not -340');
  assert.equal(F.nextBearing(10, 350), -10);
  assert.equal(F.nextBearing(90, NaN), 90);
});

// Spoken guidance (Max t419u): fake speech engine where each sentence takes time to finish.
function fakeEngine() {
  const log = [];
  let active = 0, maxActive = 0, cancels = 0, done = null;
  return {
    speak(t, d) { active++; maxActive = Math.max(maxActive, active); log.push(t); done = () => { active--; d(); }; },
    cancel() { cancels++; },
    finish() { const d = done; done = null; d && d(); },
    log, get maxActive() { return maxActive; }, get cancels() { return cancels; },
  };
}
test('voice: one sentence at a time, never cut off, newer waiting prompt replaces older', () => {
  const e = fakeEngine(), v = F.voice(e);
  v.say('In 400 ft, turn left onto Garnet Avenue');
  v.say('Rerouting');
  v.say('In 300 ft, turn right onto Bayard Street'); // supersedes "Rerouting" while the first still talks
  assert.deepEqual(e.log, ['In 400 ft, turn left onto Garnet Avenue']);
  assert.equal(e.cancels, 0, 'never cancels mid-sentence');
  e.finish();
  assert.deepEqual(e.log, ['In 400 ft, turn left onto Garnet Avenue', 'In 300 ft, turn right onto Bayard Street']);
  e.finish();
  v.say('In 300 ft, turn right onto Bayard Street'); // fine to say again later only if asked; planner prevents it
  assert.equal(e.maxActive, 1, 'no overlap');
  v.stop();
  assert.equal(e.cancels, 1, 'End/mute stops');
});

const N2 = require('../public/nav.js');
function drive(speed) {
  // East 600 m, then a left turn north 300 m.
  const runs = [{ name: 'Garnet Avenue', points: [[32.8, -117.26], [32.8, -117.2536]] }, { name: 'Bayard Street', points: [[32.8, -117.2536], [32.8027, -117.2536]] }];
  const r = N2.buildSteps(runs, 'the pier');
  const plan = F.promptPlan(), said = [];
  const turnAt = r.steps.find(s => s.kind === 'turn').at;
  for (let d = 0; d < r.total - 40; d += speed) { // one fix per second
    const ll = F.pointAt(r, d);
    const st = N2.status(r, ll);
    const t = plan.update(st, speed);
    if (t) said.push({ t, d, toTurn: turnAt - d });
  }
  return { said, turnAt };
}
test('one prompt per turn, about 12 s ahead at cart speed', () => {
  for (const mph of [15, 25]) {
    const v = mph * 0.447, { said } = drive(v);
    const turn = said.filter(s => /left/i.test(s.t));
    assert.equal(turn.length, 1, JSON.stringify(said));
    const secs = turn[0].toTurn / v;
    assert.ok(secs >= 9 && secs <= 13.5, mph + ' mph: ' + secs.toFixed(1) + ' s before the turn');
    assert.match(turn[0].t, /^In \d+ ft, turn left onto Bayard Street/);
  }
});
test('missed the early prompt: one short "Turn left" at the turn, then silence', () => {
  const plan = F.promptPlan();
  const st = { idx: 1, next: { at: 600, text: 'Turn left onto Bayard Street' }, toNext: 12, text: 'Now' };
  assert.equal(plan.update(st, 8), 'Turn left onto Bayard Street');
  assert.equal(plan.update({ ...st, toNext: 5 }, 8), null);
  assert.equal(plan.update({ ...st, toNext: 150 }, 8), null, 'far away: wait');
});
