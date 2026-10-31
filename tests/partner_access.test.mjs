// Owner-endpoint authorization: super-admins may edit any shop; owners only their own.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { shopAccess } from '../lib/partner.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

test('super-admin may act on any shop it names', () => {
  assert.deepEqual(shopAccess({ isSuper: true, requestedShopId: 'B' }), { shopId: 'B' });
  assert.deepEqual(shopAccess({ isSuper: true, requestedShopId: 'B', resourceShopId: 'B' }), { shopId: 'B' });
  assert.deepEqual(shopAccess({ isSuper: true, resourceShopId: 'B' }), { shopId: 'B' });
  assert.equal(shopAccess({ isSuper: true }).status, 400);
  // Named shop B but the experience belongs to C: refuse rather than edit the wrong shop.
  assert.equal(shopAccess({ isSuper: true, requestedShopId: 'B', resourceShopId: 'C' }).status, 403);
});

test('owners stay on their own shop', () => {
  assert.deepEqual(shopAccess({ isSuper: false, ownShopId: 'A' }), { shopId: 'A' });
  assert.deepEqual(shopAccess({ isSuper: false, ownShopId: 'A', resourceShopId: 'A' }), { shopId: 'A' });
  assert.equal(shopAccess({ isSuper: false, ownShopId: 'A', requestedShopId: 'B' }).status, 403);
  assert.equal(shopAccess({ isSuper: false, ownShopId: 'A', resourceShopId: 'B' }).status, 403, "owner A can't edit B's experience");
  assert.equal(shopAccess({ isSuper: false, ownShopId: null }).status, 404);
  assert.equal(shopAccess({ isSuper: false, ownShopId: 'A', resourceShopId: null }).status, 404);
});

test('worker routes every owner endpoint through shopAccess', () => {
  const w = readFileSync(join(root, 'workers/partner/src/index.js'), 'utf8');
  const i = w.indexOf('async function access(');
  assert.ok(i > 0);
  const tail = w.slice(i);
  for (const re of [/'\/shop' && req\.method === 'GET'/, /'\/shop' && req\.method === 'PATCH'/, /\['experiences', 'affiliates', 'places', 'codes'\]/, /shop\\\/\(experiences\|affiliates\|places\)/]) {
    assert.match(tail, re);
  }
  assert.doesNotMatch(w, /if \(!shop && !isSuper\) return J\(\{ error: 'forbidden' \}/, 'old any-owner check is gone');
  assert.match(w, /audit: 'super_edit'/);
});

import { codeExpiry } from '../lib/partner.js';
test('access code duration: 1-30 days or never', () => {
  const t = 1_000_000;
  assert.deepEqual(codeExpiry({ expires_days: 1 }, t), { expires_at: t + 86400 });
  assert.deepEqual(codeExpiry({ expires_days: 30 }, t), { expires_at: t + 30 * 86400 });
  assert.deepEqual(codeExpiry({ expires_days: null }, t), { expires_at: null });
  assert.deepEqual(codeExpiry({ expires_days: 'never' }, t), { expires_at: null });
  assert.deepEqual(codeExpiry({}, t), { expires_at: t + 30 * 86400 }, 'old clients keep 30 days');
  for (const bad of [0, 31, 2.5, -1, 'x', '']) assert.ok(codeExpiry({ expires_days: bad }, t).error, String(bad));
});
test('public unlock treats a null expiry as valid', () => {
  const w = readFileSync(join(root, 'workers/partner/src/index.js'), 'utf8');
  assert.match(w, /if \(c\.expires_at && c\.expires_at < now\(\)\) return J\(\{ error: 'Code expired'/);
  assert.match(w, /const exp = codeExpiry\(body, now\(\)\);\s*if \(exp\.error\) return J\(\{ error: exp\.error \}, 400\)/);
});
