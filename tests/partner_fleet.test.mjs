// Fleet stickers: cart numbers in, one code per cart out, the sheet, and the PNG page drawing.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { parseCarts, fleetPlan, cleanCartLabel, cartOrder, FLEET_MAX } from '../lib/partner_fleet.js';
import { makePartner } from './partner_worker_harness.mjs';

const kit = createRequire(import.meta.url)('../public/qrkit.js');

test('cart numbers: ranges, lists, zero padding, no repeats', () => {
  assert.deepEqual(parseCarts('1-4').carts, ['1', '2', '3', '4']);
  assert.deepEqual(parseCarts('A1-A3, B7').carts, ['A1', 'A2', 'A3', 'B7']);
  assert.deepEqual(parseCarts('01-03').carts, ['01', '02', '03']);
  assert.deepEqual(parseCarts('Blue 3, 7\n7, blue 3').carts, ['Blue 3', '7']);
  assert.deepEqual(parseCarts('A1-3').carts, ['A1', 'A2', 'A3']);
  assert.match(parseCarts('').error, /cart numbers/);
  assert.match(parseCarts('9-2').error, /low to high/);
  assert.match(parseCarts('1-500').error, new RegExp(String(FLEET_MAX)));
  assert.match(parseCarts('<script>').error, /not a cart number/);
  assert.equal(cleanCartLabel('  Cart   12 '), 'Cart 12');
  assert.equal(cleanCartLabel('a'.repeat(30)).length, 12);
  assert.deepEqual(['10', '2', 'A10', 'A2'].sort(cartOrder), ['2', '10', 'A2', 'A10']);
});

test('a cart with a live code keeps it; expired or missing carts get new ones', () => {
  const plan = fleetPlan(['1', '2', '3'], [
    { code: 'KEEP', cart_label: '1', expires_at: null },
    { code: 'OLD', cart_label: '2', expires_at: 10 },
    { code: 'DESK', cart_label: '', expires_at: null },
  ], 100);
  assert.deepEqual(plan.reuse, [{ cart: '1', code: 'KEEP' }]);
  assert.deepEqual(plan.make, ['2', '3']);
});

test('worker: owner makes cart codes, printing again reuses them, unlock names the cart', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop();
  const first = await p.call('/shop/fleet', { as: owner, json: { carts: '1-3, A7' } });
  assert.equal(first.status, 201, JSON.stringify(first.body));
  assert.equal(first.body.created, 4);
  assert.deepEqual(first.body.fleet.map(f => f.cart), ['1', '2', '3', 'A7']);
  for (const f of first.body.fleet) {
    assert.match(f.code, /^[0-9A-Z]{7,8}$/);
    assert.equal(f.expires_at, null, 'fleet codes default to no expiry');
  }
  const again = await p.call('/shop/fleet', { as: owner, json: { carts: '2-4' } });
  assert.equal(again.body.created, 1);
  assert.equal(again.body.reused, 2);
  const two = first.body.fleet.find(f => f.cart === '2').code;
  assert.equal(again.body.fleet.find(f => f.cart === '2').code, two);
  const bundle = await p.call('/shop', { as: owner });
  assert.equal(bundle.body.codes.filter(c => c.cart_label).length, 5);
  const u = await p.call('/public/lajollacartco/unlock?code=' + two);
  assert.equal(u.status, 200);
  assert.equal(u.body.cart, '2');
  const dated = await p.call('/shop/fleet', { as: owner, json: { carts: '9', expires_days: 30 } });
  assert.ok(dated.body.fleet[0].expires_at > Date.now() / 1000 + 29 * 86400);
  const bad = await p.call('/shop/fleet', { as: owner, json: { carts: '5-1' } });
  assert.equal(bad.status, 400);
  const anon = await p.call('/shop/fleet', { json: { carts: '1' } });
  assert.equal(anon.status, 401);
  const desk = await p.call('/shop/codes', { as: owner, json: { code: 'DESK1' } });
  assert.equal(desk.body.code.cart_label, '');
});

test('worker: another shop owner cannot print this fleet', async () => {
  const p = makePartner();
  const a = await p.seedShop({ slug: 'shopa', owner: 'a@example.com' });
  const b = await p.seedShop({ slug: 'shopb', owner: 'b@example.com' });
  const r = await p.call('/shop/fleet?shop_id=' + a.shop.id, { as: b.owner, json: { carts: '1' } });
  assert.equal(r.status, 403);
});

test('sheet: six stickers per page, each QR opens that cart code', () => {
  const fleet = Array.from({ length: 8 }, (_, i) => ({ cart: String(i + 1), code: 'CODE' + (i + 1) }));
  const html = kit.fleetHtml({ name: 'A & B <Carts>', slug: 'lajollacartco', color: '#0b6', logoUrl: 'javascript:alert(1)', origin: 'https://golfcartmap.com', fleet });
  assert.equal((html.match(/class="page"/g) || []).length, 2);
  assert.equal((html.match(/class="piece sticker"/g) || []).length, 8);
  assert.match(html, /A &amp; B &lt;Carts&gt;/);
  assert.match(html, /Cart 8/);
  assert.ok(html.replace(/<wbr>/g, '').includes('https://golfcartmap.com/p/lajollacartco/go?code=CODE3'));
  assert.match(html, /Save page 2 as PNG/);
  assert.doesNotMatch(html, /javascript:alert/);
  assert.doesNotMatch(html.split('<script>')[1], /<Carts>/, 'names inside the script data are escaped');
  assert.doesNotMatch(html, /\u2014/);
  assert.throws(() => kit.fleetHtml({ fleet: [] }), /Make cart codes first/);
  assert.equal(kit.bandInk('#ffffff'), '#073044');
  assert.equal(kit.bandInk('#0b3c50'), '#ffffff');
});

test('PNG page: draws every sticker band and the QR modules', () => {
  const calls = [];
  const ctx = new Proxy({}, {
    get(t, k) {
      if (k in t) return t[k];
      if (k === 'measureText') return s => ({ width: String(s).length * 10 });
      return (...a) => calls.push([k, ...a]);
    },
    set(t, k, v) { t[k] = v; return true; },
  });
  const url = kit.renterUrl('https://golfcartmap.com', 'lj', 'CODE1');
  const items = [1, 2, 3].map(n => ({ cart: String(n), code: 'CODE' + n, url, rows: kit.modules(url) }));
  kit.drawPage(ctx, items, { name: 'La Jolla Cart Co', color: '#14b8c4', ink: '#073044' }, kit.PNG_PAGE, kit.drawSticker);
  const texts = calls.filter(c => c[0] === 'fillText').map(c => c[1]);
  assert.ok(texts.includes('Cart 3'));
  assert.ok(texts.includes('CODE2'));
  const dark = items[0].rows.join('').split('').filter(x => x === '1').length;
  assert.ok(calls.filter(c => c[0] === 'fillRect').length >= dark * 3, 'every QR module is drawn');
});
