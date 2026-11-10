// Stop stories: the shop note is spoken after the arrival callout, on the phone and on CarPlay.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const S = require('../public/stories.js');

test('story line trims, drops an em dash, and caps length', () => {
  assert.equal(S.storyLine('  Park by the blue umbrellas.  '), 'Park by the blue umbrellas.');
  assert.equal(S.storyLine('Look west \u2014 then north'), 'Look west, then north');
  assert.equal(S.storyLine(''), '');
  assert.equal(S.storyLine(null), '');
  assert.equal(S.storyLine('a'.repeat(800)).length, S.MAX);
});

test('arrival lines: callout first, note second, next stop stays on the callout', () => {
  const a = S.arrivalLines('Crystal Pier', 'Park by the blue umbrellas.', 'Tourmaline');
  assert.equal(a.callout, 'You\u2019ve arrived at Crystal Pier. Next stop: Tourmaline.');
  assert.equal(a.story, 'Park by the blue umbrellas.');
  assert.equal(S.arrivalLines('Crystal Pier', '   ', '').story, '');
  assert.ok(!a.callout.includes('\u2014') && !a.story.includes('\u2014'));
});

test('match a note by stop name, address, or parking pin', () => {
  const stops = [{ name: 'Crystal Pier', lat: 32.80, lon: -117.25, park_lat: 32.801, park_lon: -117.251, note: 'Park by the umbrellas.' }];
  assert.equal(S.matchNote(stops, { lat: 0, lon: 0 }, 'Crystal Pier'), 'Park by the umbrellas.');
  assert.equal(S.matchNote(stops, { lat: 32.801, lon: -117.251 }, ''), 'Park by the umbrellas.');
  assert.equal(S.matchNote(stops, { lat: 32.80, lon: -117.25 }, 'Somewhere else'), 'Park by the umbrellas.');
  assert.equal(S.matchNote(stops, { lat: 40, lon: -70 }, 'Home'), '');
});

test('CarPlay speaks the callout on the arrival fix and the note on the next one', () => {
  const idle = { phase: 'idle' };
  const first = S.onArrive(idle, { arrived: true, callout: 'You\u2019ve arrived at Crystal Pier.', story: 'Park by the umbrellas.' });
  assert.equal(first.say, 'You\u2019ve arrived at Crystal Pier.');
  assert.equal(first.state.phase, 'story');
  const second = S.onArrive(first.state, { arrived: true, callout: 'You\u2019ve arrived at Crystal Pier.', story: 'Park by the umbrellas.' });
  assert.equal(second.say, 'Park by the umbrellas.');
  assert.equal(second.state.phase, 'done');
  const third = S.onArrive(second.state, { arrived: true, callout: 'x', story: 'Park by the umbrellas.' });
  assert.equal(third.say, null);
});

test('no note: one callout, then silence', () => {
  const first = S.onArrive({ phase: 'idle' }, { arrived: true, callout: 'Arrive at Home', story: '' });
  assert.equal(first.say, 'Arrive at Home');
  assert.equal(first.state.phase, 'done');
  assert.equal(S.onArrive(first.state, { arrived: true, callout: 'Arrive at Home', story: '' }).say, null);
});

test('not arrived resets the queue', () => {
  const mid = S.onArrive({ phase: 'idle' }, { arrived: true, callout: 'Here.', story: 'Note.' });
  const reset = S.onArrive(mid.state, { arrived: false, callout: 'Here.', story: 'Note.' });
  assert.equal(reset.state.phase, 'idle');
  assert.equal(reset.say, null);
});

function loadCarPlay(store) {
  const stories = fs.readFileSync(new URL('../public/stories.js', import.meta.url), 'utf8');
  const src = fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8');
  const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const win = { ready: true, GCM_IOS: false };
  const ctx = {
    window: win, self: win, localStorage: ls, location: { protocol: 'capacitor:' }, console,
    setTimeout, clearTimeout, Promise, JSON, Math, Date, isFinite, String, Number, document: { getElementById: () => null },
    READY: Promise.resolve(), REGIONS: [], REG: { id: 'sd', bbox: [-90, -180, 90, 180] }, MODE: 'lsv', RULE: {},
    GCMRule: { noRoute: () => 'none' }, GCMRange: { rangeFor: () => 30, load: () => ({ battery: 100 }) },
    GCMFollow: {
      isMuted: () => ls.getItem('gcm_voice_muted') === '1',
      engine: () => ({
        fix: () => ({ idx: 1, off: 0, along: 1, toNext: 0, remaining: 0, arrived: true, bearing: 1, course: 1, wrong: false }),
        offCheck: () => false, reset() {},
      }),
      promptPlan: () => ({ update: () => null }),
    },
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(stories, ctx);
  vm.runInContext(src, ctx);
  win.navStepsFor = () => ({
    pts: [[32.8, -117.25], [32.81, -117.26]],
    steps: [
      { kind: 'depart', mod: 'straight', name: 'Garnet', len: 100, text: 'Head north on Garnet', ll: [32.8, -117.25], turn: 0, outBrg: 10 },
      { kind: 'arrive', mod: 'arrive', name: 'Crystal Pier', len: 0, text: 'Arrive at Crystal Pier', ll: [32.81, -117.26], turn: 0, outBrg: 10 },
    ],
  });
  win.testRoute = async () => ({ mi: 1, rt: 2, min: 3, range: {}, risky: false });
  win._lastDetail = { legs: [], dist: 100 };
  return win.GCMCarPlay;
}

const ACCESS = {
  gcm_partner_access: JSON.stringify({
    slug: 'beachmode', code: 'TEST123', at: Date.now(),
    shop: { name: 'Beach Mode', vehicle: 'lsv' },
    experiences: [{ id: 'e1', title: 'Sunset', stops: [
      { name: 'Crystal Pier', lat: 32.81, lon: -117.26, note: 'Park by the blue umbrellas.' },
    ] }],
    affiliates: [],
  }),
};

test('CarPlay navFix: callout, then the note, and mute returns no speech', async () => {
  const cp = loadCarPlay({ ...ACCESS });
  const stops = await cp.stops('e1', 32.8, -117.25);
  assert.equal(stops.stops[0].note, 'Park by the blue umbrellas.');
  const plan = await cp.plan({ lat: 32.8, lon: -117.25 }, { lat: 32.81, lon: -117.26 }, 'lsv', false, null, 'Crystal Pier');
  assert.equal(plan.ok, true);
  const started = cp.navStart();
  assert.equal(started.ok, true);
  const fix = { lat: 32.81, lon: -117.26, course: 10, speed: 5, t: Date.now() };
  const a = cp.navFix(fix);
  assert.match(a.say, /arrived at Crystal Pier/);
  assert.equal(a.say.includes('umbrellas'), false);
  const b = cp.navFix(fix);
  assert.equal(b.say, 'Park by the blue umbrellas.');
  const c = cp.navFix(fix);
  assert.equal(c.say, null);

  const quiet = loadCarPlay({ ...ACCESS, gcm_voice_muted: '1' });
  await quiet.stops('e1', 32.8, -117.25);
  await quiet.plan({ lat: 32.8, lon: -117.25 }, { lat: 32.81, lon: -117.26 }, 'lsv', false, null, 'Crystal Pier');
  quiet.navStart();
  assert.equal(quiet.navFix(fix).say, null);
  assert.equal(quiet.navFix(fix).say, null);
});

test('spoken copy in stories.js has no em dash', () => {
  const src = fs.readFileSync(new URL('../public/stories.js', import.meta.url), 'utf8');
  assert.equal(src.includes('\u2014'), false);
});
