import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const O = createRequire(import.meta.url)('../public/offline.js');
const idx = { meta: { generated: '2026-10-30', segments: 9, ways: 3, tiles: ['1_2', '3_4'] } };

test('filesFor lists index, tiles, rules and regions', () => {
  const f = O.filesFor('hhi', idx);
  for (const u of ['/data/regions.json', '/data/rules.json', '/data/schema.json', '/data/hhi/index.json', '/data/hhi/tiles/1_2.json', '/data/hhi/tiles/3_4.json']) assert.ok(f.includes(u), u);
  assert.throws(() => O.filesFor('../x', idx));
});

test('stamp changes when data changes', () => {
  assert.notEqual(O.stampOf(idx), O.stampOf({ meta: { ...idx.meta, generated: '2026-10-31' } }));
});

function fakeCaches() {
  const all = new Map();
  const mk = () => { const m = new Map(); return { put: async (k, r) => m.set(typeof k === 'string' ? k : k.url, r.clone()), match: async k => { const r = m.get(typeof k === 'string' ? k : k.url); return r ? r.clone() : undefined; }, keys: async () => [...m.keys()].map(url => ({ url })) }; };
  return { open: async n => { if (!all.has(n)) all.set(n, mk()); return all.get(n); }, delete: async n => all.delete(n), has: async n => all.has(n) };
}
globalThis.localStorage = { s: {}, getItem(k) { return this.s[k] ?? null; }, setItem(k, v) { this.s[k] = v; } };

test('download, network-first fallback, refresh on change, remove', async () => {
  let live = idx; let fail = false;
  const fetch = async u => { if (fail) throw new Error('offline'); if (u.endsWith('index.json')) return new Response(JSON.stringify(live)); if (u.endsWith('schema.json')) return new Response('{"schema":1}'); return new Response('[]'); };
  const api = O.create({ fetch, caches: fakeCaches(), base: 'https://golfcartmap.com/map' });
  const m = await api.download('hhi');
  assert.equal(m.files, 8);
  assert.ok(api.isDownloaded('hhi'));
  const r = await api.fallback('/data/hhi/tiles/1_2.json');
  assert.equal(r.headers.get('X-GCM-Offline'), '1');
  assert.deepEqual(await api.refreshAll(), []);
  live = { meta: { ...idx.meta, generated: '2026-11-01' } };
  assert.deepEqual(await api.refreshAll(), ['hhi']);
  fail = true;
  assert.deepEqual(await api.refreshAll(), []);
  await api.remove('hhi');
  assert.equal(await api.fallback('/data/hhi/tiles/1_2.json'), null);
});

test('a failed required file leaves no partial city', async () => {
  const fetch = async u => (u.includes('3_4') ? new Response('', { status: 500 }) : new Response(u.endsWith('index.json') ? JSON.stringify(idx) : '[]'));
  const api = O.create({ fetch, caches: fakeCaches(), base: 'https://golfcartmap.com/map' });
  await assert.rejects(api.download('kiawah'));
  assert.ok(!api.isDownloaded('kiawah'));
});
