// Return-by and range nudges. Travel minutes come from the legal route; the words are decided here.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
import { cleanReturnBy, cleanRangeMi, cleanReturnSpot } from '../lib/partner.js';

const require = createRequire(import.meta.url);
const R = require('../public/reminders.js');

function at(h, m, s = 0) {
  const d = new Date(2026, 6, 4, h, m, s);
  return d;
}

test('return fields: HH:MM, miles, and a spot', () => {
  assert.equal(cleanReturnBy('17:05').value, '17:05');
  assert.equal(cleanReturnBy('7:05').value, '07:05');
  assert.equal(cleanReturnBy('').value, '');
  assert.equal(cleanReturnBy(undefined).skip, true);
  assert.match(cleanReturnBy('25:00').error, /HH:MM/);
  assert.equal(cleanRangeMi('25').value, 25);
  assert.equal(cleanRangeMi('').value, 0);
  assert.match(cleanRangeMi('300').error, /0 to 200/);
  assert.equal(cleanReturnSpot('', '', true).lat, null);
  assert.equal(cleanReturnSpot(32.8, -117.2, true).lon, -117.2);
  assert.match(cleanReturnSpot(99, 0, true).error, /latitude/);
  assert.equal(cleanReturnSpot(1, 2, false).skip, true);
});

test('head back in 15 minutes when the ride home leaves that much slack', () => {
  const n = R.timeNudge({ now: at(16, 30), returnBy: '17:00', travelMin: 15 });
  assert.equal(n.text, 'Head back in 15 minutes.');
  assert.equal(n.id, 'leave-window');
  const early = R.timeNudge({ now: at(16, 0), returnBy: '17:00', travelMin: 15 });
  assert.equal(early, null);
  const soon = R.timeNudge({ now: at(16, 50), returnBy: '17:00', travelMin: 15 });
  assert.equal(soon.text, 'Head back now to make your return time.');
  const late = R.timeNudge({ now: at(17, 10), returnBy: '17:00', travelMin: 5 });
  assert.equal(late.text, 'You are due back at the shop.');
  assert.equal(R.timeNudge({ now: at(16, 40), returnBy: '', travelMin: 0 }), null);
});

test('range warning uses 80 percent of the charge that is left', () => {
  assert.equal(R.rangeNudge({ homeMi: 0.1, rangeMi: 20, batteryPct: 100 }), null);
  const close = R.rangeNudge({ homeMi: 18, rangeMi: 20, batteryPct: 100 });
  assert.equal(close.id, 'range-close');
  assert.match(close.text, /close to this cart/);
  const half = R.rangeNudge({ homeMi: 12, rangeMi: 20, batteryPct: 50 });
  assert.equal(half.id, 'range-short');
  const fine = R.rangeNudge({ homeMi: 5, rangeMi: 20, batteryPct: 100 });
  assert.equal(fine, null);
  assert.equal(close.text.includes('\u2014'), false);
});

test('path miles and travel time', () => {
  const hav = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]) * 111320;
  const miles = R.pathMiles([[0, 0], [0, 0.01]], hav);
  assert.ok(miles > 0.6 && miles < 0.8, miles);
  assert.equal(R.travelMinutes(12, 'golf_cart'), 60);
  assert.equal(R.CART_MPH.lsv, 18);
});

function loadCarPlay(store) {
  const reminders = fs.readFileSync(new URL('../public/reminders.js', import.meta.url), 'utf8');
  const src = fs.readFileSync(new URL('../public/carplay.js', import.meta.url), 'utf8');
  const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
  const win = { ready: true, GCM_IOS: false };
  const ctx = {
    window: win, self: win, localStorage: ls, location: { protocol: 'capacitor:' }, console,
    setTimeout, clearTimeout, Promise, JSON, Math, Date, isFinite, String, Number,
    document: { getElementById: () => null },
    READY: Promise.resolve(), REGIONS: [], REG: { id: 'sd', bbox: [-90, -180, 90, 180] }, MODE: 'lsv', RULE: {}, RULES: {},
    GCMRule: { noRoute: () => 'none' }, GCMRange: { rangeFor: () => 30, load: () => ({ battery: 100 }) },
    GCMFollow: {
      isMuted: () => ls.getItem('gcm_voice_muted') === '1',
      engine: () => ({
        fix: () => ({ idx: 0, off: 0, along: 1, toNext: 400, remaining: 800, arrived: false, bearing: 1, course: 1, wrong: false }),
        offCheck: () => false, reset() {},
      }),
      promptPlan: () => ({ update: () => null }),
    },
  };
  ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(reminders, ctx);
  vm.runInContext(src, ctx);
  win.navStepsFor = () => ({
    pts: [[32.8, -117.25], [32.81, -117.26]],
    steps: [
      { kind: 'depart', mod: 'straight', name: 'Garnet', len: 100, text: 'Head north on Garnet', ll: [32.8, -117.25], turn: 0, outBrg: 10 },
      { kind: 'arrive', mod: 'arrive', name: 'Shop', len: 0, text: 'Arrive at Shop', ll: [32.81, -117.26], turn: 0, outBrg: 10 },
    ],
  });
  win.testRoute = async () => ({ mi: 1, rt: 2, min: 3, range: {}, risky: false });
  win._lastDetail = { legs: [], dist: 100 };
  return win.GCMCarPlay;
}

test('CarPlay navFix speaks a due nudge and stays quiet when muted', async () => {
  const soon = new Date(Date.now() + 10 * 60000);
  const hh = String(soon.getHours()).padStart(2, '0');
  const mm = String(soon.getMinutes()).padStart(2, '0');
  const access = JSON.stringify({
    slug: 'beachmode', code: 'TEST123', at: Date.now(),
    shop: { name: 'Beach Mode', vehicle: 'golf_cart', return_by: hh + ':' + mm, range_mi: 0 },
    experiences: [{ id: 'e1', title: 'Loop', stops: [{ name: 'Pier', lat: 32.81, lon: -117.26 }] }],
    affiliates: [],
  });
  const cp = loadCarPlay({ gcm_partner_access: access });
  const plan = await cp.plan({ lat: 32.8, lon: -117.25 }, { lat: 32.81, lon: -117.26 }, 'lsv', false, null, 'Pier');
  assert.equal(plan.ok, true);
  cp.navStart();
  const fix = { lat: 32.8, lon: -117.25, course: 10, speed: 4, t: Date.now() };
  const said = cp.navFix(fix);
  assert.match(said.say, /Head back in \d+ minute/);
  const again = cp.navFix({ ...fix, t: Date.now() });
  assert.equal(again.say, null);

  const quiet = loadCarPlay({ gcm_partner_access: access, gcm_voice_muted: '1' });
  await quiet.plan({ lat: 32.8, lon: -117.25 }, { lat: 32.81, lon: -117.26 }, 'lsv', false, null, 'Pier');
  quiet.navStart();
  assert.equal(quiet.navFix(fix).say, null);
});
