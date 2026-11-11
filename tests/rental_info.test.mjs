// Rental info card: field checks, unlock payload, Settings line, renter page.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { cleanRental, rentalFromRow, rentalFilled, RENTAL_KEYS } from '../lib/partner.js';

const require = createRequire(import.meta.url);
const R = require('../public/rental.js');
const root = new URL('../', import.meta.url);
const read = (p) => readFileSync(new URL(p, root), 'utf8');

test('cleanRental keeps the six fields and rejects a bad phone', () => {
  const ok = cleanRental({
    pickup: '  Blue umbrellas  ', return_spot: 'Side lot', return_by: '5:00 pm',
    phone: '(619) 555-0142', rules: 'Seat belts on.', if_cart_dies: 'Call the shop.',
  });
  assert.deepEqual(Object.keys(ok.rental), RENTAL_KEYS);
  assert.equal(ok.rental.pickup, 'Blue umbrellas');
  assert.equal(ok.rental.phone, '(619) 555-0142');
  assert.equal(cleanRental({ phone: 'call the desk' }).error, 'Shop phone should be a phone number');
  assert.equal(cleanRental({ phone: '' }).rental.phone, '');
  assert.match(cleanRental({ rules: 'x'.repeat(801) }).error, /Cart rules is too long/);
  assert.equal(rentalFilled(ok.rental), true);
  assert.equal(rentalFilled(cleanRental({}).rental), false);
  assert.deepEqual(rentalFromRow('{"phone":"not a phone"}'), Object.fromEntries(RENTAL_KEYS.map(k => [k, ''])));
  assert.equal(rentalFromRow('{"return_by":"sunset"}').return_by, 'sunset');
});

test('worker stores rental on the shop and only the unlock answers include it', () => {
  const w = read('workers/partner/src/index.js');
  assert.match(w, /ALTER TABLE shops ADD COLUMN rental_json/);
  assert.match(w, /cleanRental\(body\.rental\)/);
  assert.match(w, /rental_json=\?/);
  assert.match(w, /shop: this\.shopRow\(sh, \{ rental: true \}\)/);
  assert.match(w, /rental: rentalFromRow\(sh\.rental_json\)/);
  assert.match(w, /delete teaserShop\.rental/);
  const teaser = w.slice(w.indexOf('Teaser (no paid content)'));
  assert.match(teaser, /shop: teaserShop/);
  assert.doesNotMatch(teaser.slice(0, 400), /rental: rentalFromRow/);
});

test('the app record keeps shop.rental and Settings can say the return time', async () => {
  const rental = { pickup: 'Blue umbrellas', return_by: '5:00 pm', phone: '619-555-0142', rules: 'Seat belts.', if_cart_dies: 'Call us.', return_spot: '' };
  assert.equal(R.summary(rental), 'Return by 5:00 pm. Pickup: Blue umbrellas. 619-555-0142');
  assert.equal(R.summary({}), '');
  const mem = () => { const m = new Map(); return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) }; };
  const st = mem();
  const answer = {
    unlocked: true, slug: 'beachmode', code: 'AB12CD3', grant: 'g',
    shop: { name: 'Beach Mode', slug: 'beachmode', rental },
    experiences: [{ id: 'e1', title: 'Sunset', stops: [] }], affiliates: [], places: [],
  };
  const res = await R.enter('AB12CD3', { fetch: async () => ({ ok: true, json: async () => answer }), storage: st, win: {}, nowMs: 5 });
  assert.equal(res.ok, true);
  assert.equal(JSON.parse(st.getItem('gcm_partner_access')).shop.rental.phone, '619-555-0142');
  assert.match(read('public/rental.js'), /summary\(a\.shop\.rental\)/);
  const card = read('public/p.js').slice(read('public/p.js').indexOf('function rentalCard'));
  assert.match(card, /id="rentalCard"/);
  assert.match(card, /Your rental/);
  assert.doesNotMatch(card.slice(0, 1200), /\u2014/);
});
