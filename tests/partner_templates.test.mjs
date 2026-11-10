// node --test tests/partner_templates.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { copyStops, pushStops, sameTown, brandFields, experiencePayload } from '../lib/partner_templates.js';
import { shopAccess } from '../lib/partner.js';

const beach = [
  { label: 'Pier', note: 'seals', lat: 32.8, lon: -117.2 },
  { label: 'Tacos', note: '', lat: 32.81, lon: -117.21 },
];

test('pins travel only inside the same town', () => {
  assert.equal(sameTown({ region_id: 'sd' }, { region_id: 'sd' }), true);
  assert.equal(sameTown({ region_id: 'sd' }, { region_id: '30a' }), false);
  const kept = copyStops(beach, true);
  assert.equal(kept[0].lat, 32.8);
  const moved = copyStops(beach, false);
  assert.equal(moved[0].label, 'Pier');
  assert.equal(moved[0].note, 'seals');
  assert.equal('lat' in moved[0], false);
  assert.equal(moved.length, 2);
});

test('a later edit updates words everywhere and pins only in the same town', () => {
  const source = [{ label: 'New pier', note: 'morning', lat: 30.3, lon: -86.1 }, { label: 'Cafe', note: 'biscuits', lat: 30.32, lon: -86.12 }];
  const dest = [{ label: 'Old pier', note: 'old', lat: 26.1, lon: -81.8 }];
  const otherTown = pushStops(source, dest, false);
  assert.equal(otherTown[0].label, 'New pier');
  assert.equal(otherTown[0].note, 'morning');
  assert.equal(otherTown[0].lat, 26.1);
  assert.equal(otherTown[0].lon, -81.8);
  assert.equal('lat' in otherTown[1], false);
  const same = pushStops(source, dest, true);
  assert.equal(same[0].lat, 30.3);
  assert.equal(same[1].lat, 30.32);
});

test('page copy keeps the location name and town off the brand payload', () => {
  const brand = brandFields({ name: 'Beach Mode', slug: 'beach', region_id: 'sd', blurb: 'Hi', logo_url: 'https://x', color: '#abc', vehicle: 'lsv', owner_email: 'a@b.c' });
  assert.deepEqual(brand, { blurb: 'Hi', logo_url: 'https://x', color: '#abc', vehicle: 'lsv' });
  const ride = experiencePayload({ title: 'Sunset', description: 'west', stops: beach, nearest_start: false }, { keepPins: false, templateId: 'abc' });
  assert.equal(ride.template_id, 'abc');
  assert.equal(ride.nearest_start, false);
  assert.equal('lat' in ride.stops[0], false);
});

test('an owner can open every shop on their email, and nobody else', () => {
  assert.deepEqual(shopAccess({ isSuper: false, ownedShopIds: ['A', 'B'], requestedShopId: 'B' }), { shopId: 'B' });
  assert.equal(shopAccess({ isSuper: false, ownedShopIds: ['A', 'B'], requestedShopId: 'C' }).status, 403);
  assert.deepEqual(shopAccess({ isSuper: false, ownShopId: 'A' }), { shopId: 'A' });
});

test('copy routes ignore a client-supplied push target list', () => {
  const w = readFileSync(new URL('../workers/partner/src/index.js', import.meta.url), 'utf8');
  assert.match(w, /copy-experience/);
  assert.match(w, /copy-page/);
  assert.match(w, /shops-by-owner/);
  assert.match(w, /delete b\.push_shop_ids/);
  assert.match(w, /sameTown/);
  assert.match(w, /pushStops/);
});
