// Logo and stop photo uploads: type and size checks, R2 key, stop URL cleanup.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sniffImage, bytesFromB64, safeImageUrl, cleanStops, storeImage, MEDIA_MAX_BYTES } from '../lib/partner.js';

const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
const png = () => bytesFromB64(PNG_B64).bytes;
const read = (p) => readFileSync(new URL('../' + p, import.meta.url), 'utf8');

test('sniff accepts png jpeg webp and rejects gif, svg, and oversized files', () => {
  assert.equal(sniffImage(png()).content_type, 'image/png');
  assert.equal(sniffImage(Uint8Array.from([0xff, 0xd8, 0xff, 0x00])).ext, 'jpg');
  const webp = new Uint8Array(12);
  webp.set([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50]);
  assert.equal(sniffImage(webp).content_type, 'image/webp');
  assert.match(sniffImage(Uint8Array.from([0x47, 0x49, 0x46, 0x38])).error, /JPEG, PNG, or WebP/);
  assert.match(sniffImage(Uint8Array.from([0x3c, 0x73, 0x76, 0x67])).error, /JPEG, PNG, or WebP/);
  assert.match(sniffImage(new Uint8Array(MEDIA_MAX_BYTES + 1)).error, /1\.5 MB/);
  assert.equal(bytesFromB64('@@@').error, 'Image could not be read');
});

test('stop photo urls stay http(s) and scripts are dropped', () => {
  assert.equal(safeImageUrl('javascript:alert(1)'), '');
  assert.equal(safeImageUrl('https://user:pass@example.com/a.png'), '');
  const stops = cleanStops([
    { label: 'Cove', lat: 1, lon: 2, note: 'hi', photo: 'https://example.com/cove.jpg' },
    { label: 'Pier', lat: 3, lon: 4, photo: 'javascript:alert(1)' },
  ]);
  assert.equal(stops[0].photo, 'https://example.com/cove.jpg');
  assert.equal(stops[0].note, 'hi');
  assert.equal(stops[1].photo, undefined);
});

test('storeImage writes a shop key and refuses a bad kind', async () => {
  const puts = [];
  const ok = await storeImage({
    bytes: png(), shopId: 's1', kind: 'logo', id: 'abc',
    put: async (key, bytes, type) => { puts.push({ key, n: bytes.length, type }); },
  });
  assert.equal(ok.status, 201);
  assert.equal(ok.row.r2_key, 'shops/s1/abc.png');
  assert.equal(puts[0].type, 'image/png');
  const bad = await storeImage({ bytes: png(), shopId: 's1', kind: 'banner', id: 'x', put: async () => {} });
  assert.equal(bad.status, 400);
});

test('worker stores bytes in R2 and the pages proxy allows the app to read them', () => {
  const w = read('workers/partner/src/index.js');
  const toml = read('workers/partner/wrangler.toml');
  const proxy = read('functions/api/partner/[[path]].js');
  assert.match(w, /Photo storage is not configured/);
  assert.match(w, /env\.MEDIA\.put/);
  assert.match(w, /env\.MEDIA\.get/);
  assert.match(w, /cleanStops\(/);
  assert.match(w, /CREATE TABLE IF NOT EXISTS media/);
  assert.match(toml, /binding = "MEDIA"/);
  assert.match(toml, /gcm-partner-media-preview/);
  assert.match(proxy, /path\.startsWith\('\/media\/'\)/);
  assert.match(read('public/p.js'), /stopPopupHtml/);
  assert.match(read('public/partner/admin.js'), /uploadShopPhoto/);
});
