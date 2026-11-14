// QR sticker and counter card: renter link, module matrix, print page escaping.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const kit = require('../public/qrkit.js');

const URL = 'https://golfcartmap.com/p/lajollacartco/go?code=TESTCODE';

test('renter link matches the admin copy link, code uppercased', () => {
  assert.equal(kit.renterUrl('https://golfcartmap.com/', 'lajollacartco', 'testcode'), URL);
  assert.equal(kit.renterUrl('https://golfcartmap.com', 'lajollacartco', 'TESTCODE'), URL);
});

test('matrix is square and has the three finder frames', () => {
  const rows = kit.modules(URL);
  assert.ok(rows.length >= 21);
  assert.ok(rows.every(r => r.length === rows.length));
  for (const origin of [[0, 0], [0, rows.length - 7], [rows.length - 7, 0]]) {
    const [r0, c0] = origin;
    assert.equal(rows[r0].slice(c0, c0 + 7), '1111111');
    assert.equal(rows[r0 + 6].slice(c0, c0 + 7), '1111111');
    assert.equal(rows[r0 + 1].slice(c0, c0 + 7), '1000001');
  }
  const longUrl = 'https://partner-portal-mvp.golfcart-maps.pages.dev/p/' + 'beachmode'.repeat(4) + '/go?code=DESKCODE12';
  const longRows = kit.modules(longUrl);
  assert.ok(longRows.length > rows.length);
  assert.equal(longRows[0].slice(0, 7), '1111111');
  const svg = kit.svg(rows);
  assert.match(svg, /<svg/);
  assert.match(svg, /fill="#000000"/);
  assert.doesNotMatch(svg, /<script/i);
});

test('print page has sticker, counter card, logo, color, and a safe QR target', () => {
  const html = kit.printHtml({
    name: 'A & B <Carts>',
    slug: 'lajollacartco',
    color: '#0b6',
    logoUrl: 'https://example.com/logo.png',
    code: 'testcode',
    origin: 'https://golfcartmap.com',
  });
  assert.match(html, /A &amp; B &lt;Carts&gt;/);
  assert.match(html, /class="piece sticker"/);
  assert.match(html, /class="piece card"/);
  assert.match(html, /Scan for your rides/);
  assert.match(html, /Ask the desk, then scan/);
  assert.match(html, />TESTCODE</);
  assert.equal(html.replace(/<wbr>/g, '').includes(URL), true);
  assert.match(html, /background:#00bb66/);
  assert.match(html, /src="https:\/\/example.com\/logo.png"/);
  assert.match(html, /Print or save as PDF/);
  assert.equal((html.match(/<svg/g) || []).length, 2);
  assert.doesNotMatch(html, /\u2014/);
});

test('bad color, script logos, and a missing code do not leak into the page', () => {
  const html = kit.printHtml({
    name: 'Beach Mode',
    slug: 'beachmode',
    color: 'red;background:url(javascript:alert(1))',
    logoUrl: 'javascript:alert(1)',
    code: 'AB12CD3',
    origin: 'https://golfcartmap.com',
  });
  assert.match(html, /background:#14b8c4/);
  assert.doesNotMatch(html, /javascript:/i);
  assert.doesNotMatch(html, /<img/);
  assert.throws(() => kit.printHtml({ name: 'X', slug: 'x', code: '  ', origin: 'https://golfcartmap.com' }), /access code/i);
});
