// Off-limits zones on the real partner Worker: the shop saves, edits and deletes them; renters get
// them with the unlock answer; another shop can't touch them; bad shapes are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import { makePartner } from './partner_worker_harness.mjs';

const AREA = { kind: 'area', name: 'Boardwalk lot', note: 'Walkers only.', points: [[32.79, -117.256], [32.79, -117.254], [32.792, -117.254], [32.792, -117.256]] };
const LINE = { kind: 'line', name: 'Ocean Front Walk', points: [[32.795, -117.2565], [32.80, -117.2575]] };

test('shop saves zones, renters get them with the unlock, other shops cannot touch them', async () => {
  const p = makePartner();
  const { owner, boss } = await p.seedShop();
  const a = await p.call('/shop/offlimits', { as: owner, json: AREA });
  assert.equal(a.status, 201, JSON.stringify(a.body));
  assert.equal(a.body.zone.kind, 'area');
  assert.equal(a.body.zone.points.length, 4);
  const l = await p.call('/shop/offlimits', { as: owner, json: LINE });
  assert.equal(l.status, 201);

  const shop = await p.call('/shop', { as: owner });
  assert.deepEqual(shop.body.offlimits.map(z => z.name), ['Boardwalk lot', 'Ocean Front Walk']);

  await p.call('/shop/codes', { as: owner, json: { code: 'ZONE1' } });
  const u = await p.call('/public/lajollacartco/unlock?code=ZONE1');
  assert.equal(u.status, 200);
  assert.deepEqual(u.body.offlimits.map(z => [z.kind, z.name, z.note]), [['area', 'Boardwalk lot', 'Walkers only.'], ['line', 'Ocean Front Walk', '']]);
  const teaser = await p.call('/public/lajollacartco');
  assert.equal(teaser.body.offlimits, undefined, 'the locked page does not list them');

  const ed = await p.call('/shop/offlimits/' + l.body.zone.id, { as: owner, method: 'PATCH', json: { note: 'Bikes and walkers.' } });
  assert.equal(ed.status, 200);
  assert.equal(ed.body.zone.note, 'Bikes and walkers.');
  assert.equal(ed.body.zone.kind, 'line', 'the kind never changes');

  // A second shop with its own owner.
  const made = await p.call('/admin/shops', { as: boss, json: { name: 'Other', slug: 'othershop', region_id: 'sd' } });
  await p.call('/admin/shops/' + made.body.shop.id, { as: boss, method: 'PATCH', json: { owner_email: 'other@example.com' } });
  await p.login('other@example.com');
  const steal = await p.call('/shop/offlimits/' + a.body.zone.id, { as: 'other@example.com', method: 'DELETE' });
  assert.equal(steal.status, 403);
  const del = await p.call('/shop/offlimits/' + a.body.zone.id, { as: owner, method: 'DELETE' });
  assert.equal(del.status, 200);
  assert.deepEqual((await p.call('/shop', { as: owner })).body.offlimits.map(z => z.name), ['Ocean Front Walk']);
  assert.equal((await p.call('/shop/offlimits', { json: AREA })).status, 401);
});

test('bad shapes and the per-shop cap are refused with a plain reason', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop();
  const bad = await p.call('/shop/offlimits', { as: owner, json: { kind: 'area', name: 'x', points: [[32.79, -117.25], [32.8, -117.25]] } });
  assert.equal(bad.status, 400);
  assert.match(bad.body.error, /at least 3 points/);
  const noName = await p.call('/shop/offlimits', { as: owner, json: { ...LINE, name: '' } });
  assert.match(noName.body.error, /Name/);
  for (let i = 0; i < 30; i++) assert.equal((await p.call('/shop/offlimits', { as: owner, json: { ...LINE, name: 'Zone ' + i } })).status, 201);
  const over = await p.call('/shop/offlimits', { as: owner, json: LINE });
  assert.equal(over.status, 400);
  assert.match(over.body.error, /Up to 30/);
});
