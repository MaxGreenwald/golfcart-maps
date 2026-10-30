// Per-shop rental vehicle: API values, worker wiring, admin save, renter page rules.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { SHOP_VEHICLES, shopVehicle } from '../lib/partner.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const worker = readFileSync(join(root, 'workers/partner/src/index.js'), 'utf8');

test('vehicle values', () => {
  assert.deepEqual(SHOP_VEHICLES, ['golf_cart', 'lsv']);
  assert.equal(shopVehicle('lsv'), 'lsv');
  assert.equal(shopVehicle('golf_cart'), 'golf_cart');
  // Unset or junk reads as the stricter golf cart rule.
  for (const v of [undefined, null, '', 'both', 'LSV']) assert.equal(shopVehicle(v), 'golf_cart');
});

test('worker stores, validates and exposes vehicle', () => {
  assert.match(worker, /ALTER TABLE shops ADD COLUMN vehicle/);
  assert.match(worker, /vehicle: shopVehicle\(r\.vehicle\)/, 'shopRow (public API + admin) carries vehicle');
  assert.match(worker, /!SHOP_VEHICLES\.includes\(body\.vehicle\)[\s\S]{0,120}400/, 'PATCH rejects unknown vehicle');
  assert.match(worker, /UPDATE shops SET[^']*vehicle=\?/);
});
