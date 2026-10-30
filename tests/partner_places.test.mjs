import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cleanPlace, PLACE_CATEGORIES } from '../lib/partner.js';

const ok = { name: 'Pier', category: 'views', lat: 32.85, lon: -117.27, note: 'Built 1925' };

test('a place needs no discount code or offer', () => {
  const r = cleanPlace(ok);
  assert.equal(r.error, undefined);
  assert.deepEqual(r.place, { name: 'Pier', category: 'views', lat: 32.85, lon: -117.27, note: 'Built 1925', link: '' });
  assert.ok(!('coupon' in r.place) && !('offer' in r.place));
});

test('category is an enum', () => {
  assert.deepEqual(PLACE_CATEGORIES, ['restaurant', 'views', 'trivia', 'fun_fact', 'other']);
  for (const c of PLACE_CATEGORIES) assert.equal(cleanPlace({ ...ok, category: c }).error, undefined, c);
  for (const c of ['bar', '', undefined, 'Views']) assert.match(cleanPlace({ ...ok, category: c }).error, /category/, String(c));
});

test('name and a real pin are required', () => {
  assert.match(cleanPlace({ ...ok, name: '  ' }).error, /Name/);
  for (const v of [undefined, '', 'x', 200]) assert.match(cleanPlace({ ...ok, lat: v }).error, /lat/, String(v));
  assert.match(cleanPlace({ ...ok, lon: 999 }).error, /lat\/lon/);
});

test('link is optional but must be https', () => {
  assert.equal(cleanPlace({ ...ok, link: 'https://example.com/a' }).place.link, 'https://example.com/a');
  assert.match(cleanPlace({ ...ok, link: 'javascript:alert(1)' }).error, /https/);
  assert.match(cleanPlace({ ...ok, link: 'http://x.com' }).error, /https/);
});

test('PATCH validates only sent fields', () => {
  assert.deepEqual(cleanPlace({ note: 'new' }, true).place, { note: 'new' });
  assert.match(cleanPlace({ category: 'nope' }, true).error, /category/);
});

test('Worker routes places through the shared shop access check', () => {
  const src = readFileSync(new URL('../workers/partner/src/index.js', import.meta.url), 'utf8');
  assert.match(src, /\['experiences', 'affiliates', 'places', 'codes'\]/);
  assert.match(src, /\(experiences\|affiliates\|places\)\\\/\(\[\^\/\]\+\)\$/);
  assert.match(src, /places: this\.places\(sh\.id\)/, 'unlock returns places');
});
