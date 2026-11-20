// The in-process partner Worker harness runs the real Worker: sign in, a shop, a code, an unlock.
import test from 'node:test';
import assert from 'node:assert/strict';
import { makePartner } from './partner_worker_harness.mjs';

test('owner signs in, makes a code, and a renter unlocks with it', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop();
  const s = await p.call('/shop', { as: owner });
  assert.equal(s.status, 200);
  assert.equal(s.body.shop.slug, 'lajollacartco');
  const c = await p.call('/shop/codes', { as: owner, json: { code: 'ABCD' } });
  assert.equal(c.status, 201);
  const u = await p.call('/public/lajollacartco/unlock?code=ABCD');
  assert.equal(u.status, 200);
  assert.equal(u.body.unlocked, true);
  const anon = await p.call('/shop');
  assert.equal(anon.status, 401);
});
