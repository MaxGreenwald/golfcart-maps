// Saved places (Max t414u): Home and Favorite beach, saved, edited and cleared on this device.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const P = createRequire(import.meta.url)('../public/places.js');
const mem = () => { const m = new Map(); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)) }; };

test('empty device: Home and Favorite beach slots exist but are not saved', () => {
  const s = P.make(mem());
  assert.deepEqual(s.list().map(p => [p.id, p.saved]), [['home', false], ['beach', false]]);
  assert.equal(s.saved().length, 0);
});

test('save Home and beach, survive a reload, edit, rename, clear', () => {
  const st = mem();
  let s = P.make(st);
  assert.equal(s.save('home', { name: '4600 Ocean Blvd', lat: 32.79, lon: -117.25 }), 'home');
  assert.equal(s.save('beach', { name: 'Tourmaline Surf Park', lat: 32.805, lon: -117.262 }), 'beach');
  s = P.make(st); // new page load, same device storage
  assert.equal(s.get('home').lat, 32.79);
  s.save('home', { name: 'New place', lat: 32.8, lon: -117.24 });
  assert.equal(s.get('home').name, 'New place');
  s.rename('beach', 'Tourmaline');
  assert.equal(s.get('beach').name, 'Tourmaline');
  assert.equal(s.label(s.get('beach')), 'Favorite beach');
  s.remove('home');
  assert.equal(s.get('home'), null);
  assert.deepEqual(s.saved().map(p => p.id), ['beach']);
});

test('custom favorites: a few allowed, named, capped', () => {
  const s = P.make(mem());
  for (let i = 0; i < P.MAX_CUSTOM; i++) assert.ok(s.save('new', { name: 'Spot ' + i, lat: 32.7, lon: -117.2 }));
  assert.equal(s.save('new', { name: 'too many', lat: 32.7, lon: -117.2 }), false);
  assert.equal(s.label(s.get('fav1')), 'Spot 0');
});

test('bad input and corrupt storage never break search', () => {
  const st = mem(); st.setItem(P.KEY, '{not json');
  const s = P.make(st);
  assert.equal(s.saved().length, 0);
  assert.equal(s.save('home', { lat: NaN, lon: 1 }), false);
  assert.equal(s.save('hacker', { lat: 1, lon: 1 }), false);
});
