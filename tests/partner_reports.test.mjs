// Renter problem reports: fields, the shop email, live-code check, daily cap, photos only with
// R2 (MEDIA), owner-only list and photo, and mark fixed. Runs the real partner Worker.
import test from 'node:test';
import assert from 'node:assert/strict';
import { cleanReport, cleanCart, reportEmail, reportRow, reportPhotoKey, REPORTS_PER_CODE_DAY } from '../lib/partner_reports.js';
import { makePartner } from './partner_worker_harness.mjs';

const MAIL_ON = { RENTER_EMAIL: 'on', MAILER_URL: 'https://mailer.test', MAILER_KEY: 'test-key' };
const PNG = Buffer.from('89504e470d0a1a0a0000000d4948445200000001000000010806000000', 'hex');

function mailer(outbox) {
  return async (url, init) => {
    if (!url.startsWith('https://mailer.test/')) return null;
    outbox.push(JSON.parse(init.body));
    return new Response('{"ok":true}', { status: 200 });
  };
}
function fakeR2() {
  const objs = new Map();
  return {
    objs,
    async put(k, bytes, o) { objs.set(k, { bytes, type: o && o.httpMetadata && o.httpMetadata.contentType }); },
    async get(k) { const o = objs.get(k); return o ? { body: o.bytes } : null; },
  };
}

test('report fields: cart number, a listed kind, note limits, optional US phone', () => {
  assert.deepEqual(cleanReport({ cart: ' 7 ', kind: 'flat', note: ' Rear left ', contact_phone: '858-555-0100' }).report,
    { cart: '7', kind: 'flat', note: 'Rear left', contact_name: '', contact_phone: '8585550100' });
  assert.equal(cleanCart(''), '');
  assert.equal(cleanCart('<b>'), null);
  assert.match(cleanReport({ kind: 'nope' }).error, /what happened/);
  assert.match(cleanReport({ kind: 'other' }).error, /Tell the shop/);
  assert.match(cleanReport({ kind: 'flat', note: 'x'.repeat(1001) }).error, /1000/);
  assert.match(cleanReport({ kind: 'flat', contact_phone: '12' }).error, /10-digit/);
  assert.equal(reportPhotoKey('s1', 'r1', new Uint8Array(PNG)).key, 'shops/s1/reports/r1.png');
  assert.match(reportPhotoKey('s1', 'r1', new Uint8Array([1, 2, 3])).error, /JPEG, PNG, or WebP/);
});

test('shop email: cart, what happened, note, phone link, photo line, escaped, no em dash', () => {
  const m = reportEmail({ shop: { name: 'Beach Mode' }, report: { cart: '7', kind: 'flat', note: '<b>rear</b>', contact_name: 'Sam', contact_phone: '8585550100', code: 'AB12' }, adminLink: 'https://golfcartmap.com/partner', photo: 'none', when: 'Thu, Nov 19, 4:05 PM PST' });
  assert.equal(m.subject, 'Cart 7: Flat tire reported by a renter');
  assert.match(m.text, /Note: <b>rear<\/b>/);
  assert.match(m.html, /&lt;b&gt;rear/);
  assert.match(m.html, /href="tel:\+18585550100"/);
  assert.match(m.text, /No photo\./);
  assert.match(m.text, /See all reports: https:\/\/golfcartmap\.com\/partner/);
  for (const s of [m.subject, m.text, m.html]) assert.doesNotMatch(s, /\u2014/);
  assert.equal(reportEmail({ shop: {}, report: { kind: 'battery', code: 'X' }, adminLink: 'x', photo: 'saved' }).subject, 'Cart: Battery low reported by a renter');
});

test('worker without R2: a renter report saves, emails the shop owner, and lists for the owner', async () => {
  const outbox = [];
  const p = makePartner({ env: MAIL_ON, fetch: mailer(outbox) });
  const { owner } = await p.seedShop();
  await p.call('/shop/codes', { as: owner, json: { code: 'CART7', multi_use: true } });
  const info = await p.call('/public/lajollacartco/report-info');
  assert.equal(info.body.photos, false);
  const r = await p.call('/public/lajollacartco/report', { json: { code: 'cart7', cart: '7', kind: 'flat', note: 'Rear left tire', contact_phone: '8585550100', photo_base64: PNG.toString('base64'), tz: 'America/Los_Angeles' } });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  assert.equal(r.body.photo, 'off', 'no R2: the photo is dropped, the report still saves');
  assert.equal(outbox.length, 1);
  assert.deepEqual(outbox[0].to, ['owner@example.com']);
  assert.equal(outbox[0].subject, 'Cart 7: Flat tire reported by a renter');
  assert.match(outbox[0].text, /Code CART7/);
  const list = await p.call('/shop/reports', { as: owner });
  assert.equal(list.status, 200);
  assert.equal(list.body.photos, false);
  const row = list.body.reports[0];
  assert.equal(row.cart, '7');
  assert.equal(row.kind_label, 'Flat tire');
  assert.equal(row.mail, 'sent');
  assert.equal(row.photo, false);
  assert.equal(row.photo_status, 'off');
  const fixed = await p.call('/shop/reports/' + row.id + '/fixed', { as: owner, json: { fixed: true } });
  assert.equal(fixed.body.report.status, 'fixed');
  assert.equal((await p.call('/shop/reports/' + row.id + '/photo', { as: owner })).status, 503);
});

test('worker: bad or expired codes are refused, the daily cap holds, other shops cannot read reports', async () => {
  const p = makePartner({});
  const a = await p.seedShop({ slug: 'shopa', owner: 'a@example.com' });
  const b = await p.seedShop({ slug: 'shopb', owner: 'b@example.com' });
  await p.call('/shop/codes', { as: a.owner, json: { code: 'ACODE', multi_use: true } });
  await p.call('/shop/codes', { as: b.owner, json: { code: 'BCODE', multi_use: true } });
  assert.equal((await p.call('/public/shopa/report', { json: { code: 'NOPE1', kind: 'flat' } })).status, 403);
  assert.equal((await p.call('/public/shopa/report', { json: { code: 'BCODE', kind: 'flat' } })).status, 403, 'another shop code');
  assert.equal((await p.call('/public/shopa/report', { json: { code: 'ACODE', kind: 'nope' } })).status, 400);
  for (let i = 0; i < REPORTS_PER_CODE_DAY; i++) {
    const r = await p.call('/public/shopa/report', { json: { code: 'ACODE', kind: 'battery' } });
    assert.equal(r.status, 201);
    assert.equal(r.body.photo, 'none');
  }
  const capped = await p.call('/public/shopa/report', { json: { code: 'ACODE', kind: 'battery' } });
  assert.equal(capped.status, 429);
  assert.match(capped.body.error, /Call the shop/);
  const mine = (await p.call('/shop/reports', { as: a.owner })).body.reports;
  assert.equal(mine.length, REPORTS_PER_CODE_DAY);
  assert.equal(mine[0].mail, 'off', 'mail off: the list is the record');
  assert.equal((await p.call('/shop/reports', { as: b.owner })).body.reports.length, 0);
  assert.equal((await p.call('/shop/reports/' + mine[0].id + '/fixed', { as: b.owner, json: {} })).status, 403);
  assert.equal((await p.call('/shop/reports')).status, 401);
  p.db.prepare("UPDATE codes SET expires_at=1 WHERE code='ACODE'").run();
  p.db.prepare('DELETE FROM reports').run();
  assert.equal((await p.call('/public/shopa/report', { json: { code: 'ACODE', kind: 'flat' } })).status, 403, 'expired code');
});

test('worker with R2: the photo is stored under the shop and only the owner can open it', async () => {
  const MEDIA = fakeR2();
  const p = makePartner({ env: { MEDIA } });
  const a = await p.seedShop({ slug: 'shopa', owner: 'a@example.com' });
  const b = await p.seedShop({ slug: 'shopb', owner: 'b@example.com' });
  await p.call('/shop/codes', { as: a.owner, json: { code: 'ACODE', multi_use: true } });
  assert.equal((await p.call('/public/shopa/report-info')).body.photos, true);
  const bad = await p.call('/public/shopa/report', { json: { code: 'ACODE', kind: 'damage', photo_base64: Buffer.from('hello').toString('base64') } });
  assert.equal(bad.status, 400);
  const r = await p.call('/public/shopa/report', { json: { code: 'ACODE', cart: 'A-3', kind: 'damage', note: 'Cracked windshield', photo_base64: PNG.toString('base64') } });
  assert.equal(r.status, 201, JSON.stringify(r.body));
  assert.equal(r.body.photo, 'saved');
  const [key] = [...MEDIA.objs.keys()];
  assert.match(key, new RegExp('^shops/' + a.shop.id + '/reports/[0-9a-f]+\\.png$'));
  const row = (await p.call('/shop/reports', { as: a.owner })).body.reports[0];
  assert.equal(row.photo, true);
  const ph = await p.call('/shop/reports/' + row.id + '/photo', { as: a.owner, raw: true });
  assert.equal(ph.status, 200);
  assert.equal(ph.headers.get('content-type'), 'image/png');
  assert.deepEqual([...ph.bytes], [...PNG], 'the stored photo comes back byte for byte');
  assert.equal((await p.call('/shop/reports/' + row.id + '/photo', { as: b.owner })).status, 403);
  assert.equal((await p.call('/shop/reports/' + row.id + '/photo')).status, 401);
  assert.deepEqual(Object.keys(reportRow({ id: 'x', kind: 'flat', photo_key: 'k' })).includes('photo_key'), false, 'the R2 key never leaves the Worker');
});
