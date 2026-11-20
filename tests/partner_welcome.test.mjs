// Rental-day welcome: booking fields, the email (map link, local rules, return time), the
// mailer call, texts staying off, and owner-only access. Runs the real partner Worker.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cleanBooking, returnLabel, rulesLines, welcomeEmail, welcomeSms } from '../lib/partner_bookings.js';
import { mailState, sendMail } from '../lib/partner_mail.js';
import { smsProvider, sendSms } from '../lib/partner_sms.js';
import { makePartner } from './partner_worker_harness.mjs';

const rules = JSON.parse(readFileSync(new URL('../public/data/rules.json', import.meta.url)));
const regions = JSON.parse(readFileSync(new URL('../public/data/regions.json', import.meta.url)));
const NOW = 1795100000;
const MAIL_ON = { RENTER_EMAIL: 'on', MAILER_URL: 'https://mailer.test', MAILER_KEY: 'test-key' };

function mailer(outbox, ok = true) {
  return async (url, init) => {
    if (!url.startsWith('https://mailer.test/')) return null;
    outbox.push({ url, auth: init.headers.authorization, body: JSON.parse(init.body) });
    return new Response(JSON.stringify(ok ? { ok: true } : { ok: false }), { status: ok ? 200 : 502 });
  };
}

test('booking fields: name, email, optional US phone, return time within 30 days', () => {
  const ok = cleanBooking({ renter_name: '  Jamie   Rivera ', email: 'Jamie@Example.com', phone: '(858) 555-0100', return_at: NOW + 3600, tz: 'America/Chicago' }, NOW);
  assert.deepEqual(ok.booking, { renter_name: 'Jamie Rivera', email: 'jamie@example.com', phone: '8585550100', return_at: NOW + 3600, tz: 'America/Chicago', code: '' });
  assert.equal(cleanBooking({ renter_name: 'A', email: 'a@b.co', return_at: NOW + 60, tz: 'Mars/Base' }, NOW).booking.tz, 'America/Los_Angeles');
  assert.match(cleanBooking({ email: 'a@b.co', return_at: NOW }, NOW).error, /name/);
  assert.match(cleanBooking({ renter_name: 'A', email: 'nope', return_at: NOW }, NOW).error, /email/);
  assert.match(cleanBooking({ renter_name: 'A', email: 'a@b.co', phone: '123', return_at: NOW }, NOW).error, /phone/);
  assert.match(cleanBooking({ renter_name: 'A', email: 'a@b.co', return_at: NOW - 7200 }, NOW).error, /past/);
  assert.match(cleanBooking({ renter_name: 'A', email: 'a@b.co', return_at: NOW + 40 * 86400 }, NOW).error, /30 days/);
});

test('return time reads in the shop time zone', () => {
  // 2026-11-19 17:00 PST is 01:00 UTC on Nov 20.
  const at = Date.UTC(2026, 10, 20, 1, 0) / 1000;
  assert.equal(returnLabel(at, 'America/Los_Angeles'), '5:00 PM, Thu Nov 19');
  assert.equal(returnLabel(at, 'America/New_York'), '8:00 PM, Thu Nov 19');
});

test('local rules come from the road-rule module, with the shop rules and the signs line', () => {
  const gs = regions.find(r => r.id === 'gulfshores');
  const lines = rulesLines({ rules, region: gs, vehicle: 'golf_cart', shopRules: 'Seat belts on.' });
  assert.match(lines[0], /posted 25 mph or less/);
  assert.ok(lines.includes('From the shop: Seat belts on.'));
  assert.match(lines.at(-1), /Posted signs always take precedence/);
  const sd = regions.find(r => r.id === 'sd');
  assert.match(rulesLines({ rules, region: sd, vehicle: 'lsv' })[0], /^Street-legal LSVs may drive on roads posted 35 mph/);
  // No rules file: no made-up limit.
  assert.match(rulesLines({ rules: null, region: sd, vehicle: 'golf_cart' })[0], /green roads/);
});

test('welcome email: escaped, link, return time, rules, no em dash', () => {
  const booking = { renter_name: 'Jamie <b>Rivera</b>', email: 'j@x.co', return_at: Date.UTC(2026, 10, 20, 1, 0) / 1000, tz: 'America/Los_Angeles', code: 'ABCD' };
  const m = welcomeEmail({ shop: { name: 'A & B Carts', color: '#0b6e86', rental: { return_spot: 'Side lot', phone: '8585550100' } }, booking, link: 'https://golfcartmap.com/p/ab/go?code=ABCD', rules: ['Rule one.'] });
  assert.equal(m.subject, 'Your A & B Carts cart map and return time');
  assert.match(m.html, /A &amp; B Carts/);
  assert.match(m.html, /Hi Jamie,/);
  assert.doesNotMatch(m.html, /<b>Rivera/);
  assert.match(m.html, /href="https:\/\/golfcartmap\.com\/p\/ab\/go\?code=ABCD"/);
  assert.match(m.html, /Return by 5:00 PM, Thu Nov 19/);
  assert.match(m.text, /Return spot: Side lot/);
  assert.match(m.text, /Shop phone: \(858\) 555-0100/);
  assert.match(m.text, /- Rule one\./);
  for (const s of [m.html, m.text, m.subject]) assert.doesNotMatch(s, /\u2014/);
  assert.match(welcomeSms({ shop: { name: 'A' }, booking, link: 'https://x.test/l' }), /Return by 5:00 PM/);
});

test('mail stays off until RENTER_EMAIL=on with a mailer URL and key; texts are always off', async () => {
  assert.equal(mailState({}).on, false);
  assert.equal(mailState({ RENTER_EMAIL: 'on' }).on, false);
  assert.equal(mailState({ MAILER_URL: 'x', MAILER_KEY: 'y' }).on, false);
  assert.equal(mailState(MAIL_ON).on, true);
  let called = 0;
  const off = await sendMail({}, { to: 'a@b.co', subject: 's', html: 'h', text: 't' }, () => { called++; });
  assert.equal(off.status, 'off');
  assert.equal(called, 0);
  assert.equal(smsProvider({ SMS_PROVIDER: 'twilio' }).enabled, false);
  assert.equal((await sendSms({ SMS_PROVIDER: 'twilio' }, { to: '8585550100', text: 'x' })).status, 'off');
});

test('worker: booking sends one welcome through the mailer with a new code that unlocks the map', async () => {
  const outbox = [];
  const p = makePartner({ env: MAIL_ON, fetch: mailer(outbox), regions });
  const { owner } = await p.seedShop({ patch: { rental: { rules: 'No kids driving.', return_spot: 'Side lot' }, vehicle: 'golf_cart' } });
  const at = Math.floor(Date.now() / 1000) + 4 * 3600;
  const r = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Jamie Rivera', email: 'jamie@example.com', phone: '858-555-0100', return_at: at, tz: 'America/Los_Angeles' } });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  assert.equal(r.body.mail.status, 'sent');
  assert.equal(r.body.sms.status, 'off', 'no SMS provider, so no text');
  assert.equal(r.body.booking.welcome, 'sent');
  assert.equal(r.body.booking.sms, 'off');
  assert.equal(outbox.length, 1);
  const sent = outbox[0];
  assert.equal(sent.auth, 'Bearer test-key');
  assert.deepEqual(sent.body.to, ['jamie@example.com']);
  assert.deepEqual(sent.body.reply_to, ['owner@example.com']);
  assert.match(sent.body.text, /https:\/\/golfcartmap\.test\/p\/lajollacartco\/go\?code=[0-9A-Z]+/);
  assert.match(sent.body.text, /Golf carts may drive on roads posted 25 mph or less/);
  assert.match(sent.body.text, /From the shop: No kids driving\./);
  const code = r.body.booking.code;
  const u = await p.call('/public/lajollacartco/unlock?code=' + code);
  assert.equal(u.status, 200);
  const codes = (await p.call('/shop', { as: owner })).body.codes;
  const row = codes.find(c => c.code === code);
  assert.equal(row.expires_at, at + 86400, 'renter code ends a day after return');
  const list = await p.call('/shop/bookings', { as: owner });
  assert.equal(list.body.bookings.length, 1);
  assert.equal(list.body.mail.on, true);
  assert.equal(list.body.sms.on, false);
  const again = await p.call('/shop/bookings/' + r.body.booking.id + '/resend', { as: owner, json: {} });
  assert.equal(again.body.mail.status, 'sent');
  assert.equal(outbox.length, 2);
});

test('worker: email off still saves the booking and says so; a failed mailer is recorded', async () => {
  const p = makePartner({ regions });
  const { owner } = await p.seedShop();
  const at = Math.floor(Date.now() / 1000) + 3600;
  const r = await p.call('/shop/bookings', { as: owner, json: { renter_name: 'Sam', email: 'sam@example.com', return_at: at, tz: 'America/Los_Angeles' } });
  assert.equal(r.status, 201);
  assert.equal(r.body.mail.status, 'off');
  assert.equal(r.body.booking.welcome, 'off');
  assert.equal(r.body.booking.sms, 'none');
  const outbox = [];
  const q = makePartner({ env: MAIL_ON, fetch: mailer(outbox, false), regions });
  const o2 = (await q.seedShop()).owner;
  const f = await q.call('/shop/bookings', { as: o2, json: { renter_name: 'Sam', email: 'sam@example.com', return_at: at, tz: 'America/Los_Angeles' } });
  assert.equal(f.body.mail.status, 'failed');
  assert.equal(f.body.booking.welcome, 'failed');
});

test('worker: preview builds the email without saving; owners only; a picked code must be live', async () => {
  const p = makePartner({ regions });
  const a = await p.seedShop({ slug: 'shopa', owner: 'a@example.com' });
  const b = await p.seedShop({ slug: 'shopb', owner: 'b@example.com' });
  const at = Math.floor(Date.now() / 1000) + 3600;
  const body = { renter_name: 'Sam', email: 'sam@example.com', return_at: at, tz: 'America/Los_Angeles' };
  const pv = await p.call('/shop/bookings/preview', { as: a.owner, json: body });
  assert.equal(pv.status, 200);
  assert.match(pv.body.subject, /cart map and return time/);
  assert.match(pv.body.html, /YOURCODE/);
  assert.equal((await p.call('/shop/bookings', { as: a.owner })).body.bookings.length, 0);
  const mine = await p.call('/shop/bookings', { as: a.owner, json: body });
  const del = await p.call('/shop/bookings/' + mine.body.booking.id, { as: b.owner, method: 'DELETE' });
  assert.equal(del.status, 403);
  const resend = await p.call('/shop/bookings/' + mine.body.booking.id + '/resend', { as: b.owner, json: {} });
  assert.equal(resend.status, 403);
  const other = await p.call('/shop/codes', { as: b.owner, json: { code: 'BCODE' } });
  assert.equal(other.status, 201);
  const stolen = await p.call('/shop/bookings', { as: a.owner, json: { ...body, code: 'BCODE' } });
  assert.equal(stolen.status, 400);
  assert.equal((await p.call('/shop/bookings', { json: body })).status, 401);
  const gone = await p.call('/shop/bookings/' + mine.body.booking.id, { as: a.owner, method: 'DELETE' });
  assert.equal(gone.status, 200);
});

test('worker: bookings are deleted 30 days after return', async () => {
  const p = makePartner({ regions });
  const { owner, shop } = await p.seedShop();
  p.db.prepare("INSERT INTO bookings(id,shop_id,renter_name,email,return_at,tz,code,created_at) VALUES('old',?,'Old','o@x.co',?,'UTC','X',0)").run(shop.id, Math.floor(Date.now() / 1000) - 31 * 86400);
  await p.call('/shop/bookings', { as: owner, json: { renter_name: 'New', email: 'n@x.co', return_at: Math.floor(Date.now() / 1000) + 3600, tz: 'UTC' } });
  assert.equal(p.db.prepare("SELECT COUNT(*) n FROM bookings WHERE id='old'").get().n, 0);
});
