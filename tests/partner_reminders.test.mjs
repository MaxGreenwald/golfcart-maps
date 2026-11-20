// Return-time reminders: the shop's lead time, the booked renter's own return time in the
// in-app banner (phone and CarPlay share GCMRemind), and one "head back soon" email from the
// Durable Object alarm. Runs the real partner Worker.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { cleanRemindMin, remindAt, reminderAction, reminderEmail, backLink, DEFAULT_REMIND_MIN } from '../lib/partner_bookings.js';
import { makePartner } from './partner_worker_harness.mjs';

const require = createRequire(import.meta.url);
const R = require('../public/reminders.js');
const regions = JSON.parse(readFileSync(new URL('../public/data/regions.json', import.meta.url)));
const MAIL_ON = { RENTER_EMAIL: 'on', MAILER_URL: 'https://mailer.test', MAILER_KEY: 'test-key' };
const nowSec = () => Math.floor(Date.now() / 1000);

function mailer(outbox) {
  return async (url, init) => {
    if (!url.startsWith('https://mailer.test/')) return null;
    outbox.push(JSON.parse(init.body));
    return new Response('{"ok":true}', { status: 200 });
  };
}

test('shop lead time: listed choices only, default 15 minutes', () => {
  assert.deepEqual(cleanRemindMin(undefined), { skip: true });
  assert.deepEqual(cleanRemindMin('30'), { value: 30 });
  assert.match(cleanRemindMin(7).error, /10, 15, 20, 30, 45, 60/);
  assert.equal(DEFAULT_REMIND_MIN, 15);
  assert.equal(remindAt(10000, 30), 10000 - 1800);
  assert.equal(remindAt(10000, 99), 10000 - 900);
});

test('due, waiting, and too-late reminders', () => {
  const row = { remind_status: 'scheduled', remind_at: 1000, return_at: 1900 };
  assert.equal(reminderAction(row, 999), 'wait');
  assert.equal(reminderAction(row, 1000), 'send');
  assert.equal(reminderAction(row, 1900 + 3601), 'late');
  assert.equal(reminderAction({ ...row, remind_status: 'sent' }, 1000), 'none');
});

test('reminder email: due time, route-back link, shop phone, no em dash', () => {
  const at = Date.UTC(2026, 10, 20, 1, 0) / 1000;
  const link = backLink('https://golfcartmap.com/', 'ab', 'ABCD');
  assert.equal(link, 'https://golfcartmap.com/p/ab/go?code=ABCD&back=1');
  const shop = { name: 'A & B Carts', return_lat: 32.8, return_lon: -117.2, rental: { return_spot: 'Side lot', phone: '8585550100' } };
  const m = reminderEmail({ shop, booking: { renter_name: 'Jamie Rivera', return_at: at, tz: 'America/Los_Angeles' }, link, minutes: 30 });
  assert.equal(m.subject, 'Head back soon: your A & B Carts cart is due at 5:00 PM');
  assert.match(m.text, /due back in about 30 minutes, at 5:00 PM, Thu Nov 19/);
  assert.match(m.text, /route back to the shop on roads your cart can use/);
  assert.match(m.html, />Route me back</);
  assert.match(m.html, /href="https:\/\/golfcartmap\.com\/p\/ab\/go\?code=ABCD&amp;back=1"/);
  assert.match(m.text, /Running late\? Call the shop: \(858\) 555-0100/);
  for (const s of [m.html, m.text, m.subject]) assert.doesNotMatch(s, /\u2014/);
  const noPin = reminderEmail({ shop: { name: 'X', return_lat: null, return_lon: null }, booking: { renter_name: 'J', return_at: at, tz: 'UTC' }, link, minutes: 15 });
  assert.match(noPin.html, />Open your cart map</);
});

test('banner: a booked return time beats the shop clock, and the shop lead time sets when it shows', () => {
  const now = new Date(2026, 10, 19, 16, 0); // device clock, like the page
  const plan = R.returnPlan({ return_by: '23:00', remind_min: 30 }, { return_at: now.getTime() / 1000 + 25 * 60 });
  assert.equal(plan.leadMin, 30);
  assert.ok(R.hasReturnTime(plan));
  const n = R.timeNudge({ now, ...plan, travelMin: 0 });
  assert.equal(n.id, 'leave-window');
  assert.match(n.text, /Head back in 25 minutes/);
  const early = R.returnPlan({ remind_min: 15 }, { return_at: now.getTime() / 1000 + 25 * 60 });
  assert.equal(R.timeNudge({ now, ...early, travelMin: 0 }), null, '25 minutes out with a 15 minute lead: not yet');
  const late = R.returnPlan({}, { return_at: now.getTime() / 1000 - 60 });
  assert.equal(R.timeNudge({ now, ...late, travelMin: 0 }).id, 'overdue');
  const shopOnly = R.returnPlan({ return_by: '16:10' }, null);
  assert.equal(shopOnly.returnAt, null);
  assert.equal(shopOnly.leadMin, 15);
  assert.match(R.timeNudge({ now, ...shopOnly, travelMin: 0 }).text, /Head back in 10 minutes/);
  assert.equal(R.hasReturnTime(R.returnPlan({}, null)), false);
});

test('worker: a booking schedules one reminder; the renter unlock carries the return time, not the contact', async () => {
  const outbox = [];
  const p = makePartner({ env: MAIL_ON, fetch: mailer(outbox), regions });
  const { owner } = await p.seedShop({ patch: { remind_min: 30, return_lat: 32.85, return_lon: -117.27, rental: { return_spot: 'Side lot' } } });
  const at = nowSec() + 3 * 3600;
  const r = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Jamie Rivera', email: 'jamie@example.com', return_at: at, tz: 'America/Los_Angeles' } });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  assert.equal(r.body.booking.remind, 'scheduled');
  assert.equal(r.body.booking.remind_at, at - 1800);
  assert.equal(p.alarmAt(), (at - 1800) * 1000);
  assert.equal(outbox.length, 1, 'welcome only');
  const u = await p.call('/public/lajollacartco/unlock?code=' + r.body.booking.code);
  assert.deepEqual(u.body.booking, { return_at: at, tz: 'America/Los_Angeles', remind_min: 30 });
  assert.equal(u.body.shop.remind_min, 30);
  assert.doesNotMatch(JSON.stringify(u.body), /jamie@example\.com|Rivera/);
  // Not due yet: the alarm sends nothing.
  await p.alarm();
  assert.equal(outbox.length, 1);
  // Shop changes the lead time: the scheduled reminder moves with it.
  const patched = await p.call('/shop', { as: owner, method: 'PATCH', json: { remind_min: 60 } });
  assert.equal(patched.status, 200, JSON.stringify(patched.body));
  assert.equal(p.alarmAt(), (at - 3600) * 1000);
  // Make it due, then fire the alarm twice: one email.
  p.db.prepare('UPDATE bookings SET remind_at=?').run(nowSec() - 5);
  await p.alarm();
  await p.alarm();
  assert.equal(outbox.length, 2);
  const m = outbox[1];
  assert.deepEqual(m.to, ['jamie@example.com']);
  assert.deepEqual(m.reply_to, ['owner@example.com']);
  assert.match(m.subject, /^Head back soon: your .+ cart is due at /);
  assert.match(m.text, /https:\/\/golfcartmap\.test\/p\/lajollacartco\/go\?code=[0-9A-Z]+&back=1/);
  assert.match(m.text, /about 60 minutes/);
  const list = (await p.call('/shop/bookings', { as: owner })).body.bookings;
  assert.equal(list[0].remind, 'sent');
  assert.ok(list[0].reminded_at > 0);
  assert.equal(p.alarmAt(), null, 'nothing left to send');
});

test('worker: mail off records the reminder as off; past-return reminders are skipped; removing a booking clears the alarm', async () => {
  const p = makePartner({ regions });
  const { owner } = await p.seedShop();
  const at = nowSec() + 3600;
  const r = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Sam', email: 'sam@example.com', return_at: at, tz: 'UTC' } });
  assert.equal(r.body.booking.remind_at, at - 15 * 60, 'default 15 minutes');
  p.db.prepare('UPDATE bookings SET remind_at=?').run(nowSec() - 5);
  await p.alarm();
  assert.equal((await p.call('/shop/bookings', { as: owner })).body.bookings[0].remind, 'off');

  const r2 = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Late', email: 'l@example.com', return_at: at, tz: 'UTC' } });
  p.db.prepare('UPDATE bookings SET remind_at=?, return_at=? WHERE id=?').run(nowSec() - 7300, nowSec() - 7200, r2.body.booking.id);
  await p.alarm();
  assert.equal(p.db.prepare('SELECT remind_status s FROM bookings WHERE id=?').get(r2.body.booking.id).s, 'late');

  const r3 = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Gone', email: 'g@example.com', return_at: at + 600, tz: 'UTC' } });
  assert.ok(p.alarmAt() > 0);
  await p.call('/shop/bookings/' + r3.body.booking.id, { as: owner, method: 'DELETE' });
  assert.equal(p.alarmAt(), null);
  assert.match((await p.call('/shop', { as: owner, method: 'PATCH', json: { remind_min: 7 } })).body.error, /Reminder must be/);
});
