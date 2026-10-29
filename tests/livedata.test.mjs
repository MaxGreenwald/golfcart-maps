import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const L = require(path.join(root, 'public', 'livedata.js'));

const sd = { id: 'sd', short: 'San Diego', state: 'CA', center: [32.85, -117.25], zoom: 15, bbox: [32.5, -117.5, 33.3, -116.9] };
const liveTown = { id: 'livetown', short: 'Live Town', state: 'FL', center: [26.05, -81.95], zoom: 16, bbox: [26.0, -82.1, 26.1, -81.9] };
const liveIndex = { meta: { tiles: ['-820_260'], tileSize: 0.1, generated: '2026-10-29' }, names: ['Live Town Road'] };

function jsonRes(body, status = 200) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return new Response(text, { status, headers: { 'content-type': 'application/json' } });
}

function loaderWith(routes, store) {
  const calls = [];
  const mem = store || L.memoryStore();
  const loader = L.createLoader({
    store: mem,
    fetch: async (url) => {
      calls.push(String(url));
      const rel = new URL(url).pathname.replace(/^\//, '');
      const hit = routes[rel];
      if (hit instanceof Error) throw hit;
      if (typeof hit === 'function') return hit();
      if (hit == null) return jsonRes('{}', 404);
      if (hit && hit.status) return jsonRes(hit.body ?? '', hit.status);
      return jsonRes(hit);
    },
  });
  return { loader, calls, store: mem };
}

test('data paths are JSON under data/ and never another host or a script', () => {
  assert.equal(L.dataRel('data/regions.json'), 'data/regions.json');
  assert.equal(L.dataRel('/data/sd/tiles/-1172_325.json'), 'data/sd/tiles/-1172_325.json');
  assert.equal(L.dataRel('capacitor://localhost/data/sd/index.json'), 'data/sd/index.json');
  assert.equal(L.dataRel('ionic://localhost/data/rules.json'), 'data/rules.json');
  assert.equal(L.dataRel('https://golfcartmap.com/data/regions.json'), '');
  assert.equal(L.dataRel('https://evil.example/data/regions.json'), '');
  assert.equal(L.dataRel('https://photon.komoot.io/api/?q=1'), '');
  assert.equal(L.dataRel('data/app.js'), '');
  assert.equal(L.dataRel('data/../secrets.json'), '');
  assert.equal(L.dataRel('data/foo.json.js'), '');
});

test('app-mode loader prefers live regions, including a town absent from the bundle', async () => {
  const { loader, calls } = loaderWith({
    'data/schema.json': { schema: 1, note: 'test' },
    'data/regions.json': [sd, liveTown],
  });
  const res = await loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  const got = await res.json();
  assert.deepEqual(got.map(r => r.id), ['sd', 'livetown']);
  assert.equal(loader.mode, 'live');
  assert.ok(calls.some(u => u === 'https://golfcartmap.com/data/schema.json'));
  assert.ok(calls.some(u => u === 'https://golfcartmap.com/data/regions.json'));
  assert.ok(calls.every(u => u.startsWith('https://golfcartmap.com/data/') && u.endsWith('.json')));
});

test('live index for a town that is not bundled is used as region data', async () => {
  const { loader } = loaderWith({
    'data/schema.json': { schema: 1 },
    'data/livetown/index.json': liveIndex,
  });
  let bundled = false;
  const res = await loader.fetchData('data/livetown/index.json', async () => { bundled = true; return jsonRes('{}', 404); });
  const got = await res.json();
  assert.equal(got.names[0], 'Live Town Road');
  assert.equal(bundled, false);
  assert.equal(got.meta.tiles[0], '-820_260');
});

test('network failure falls back to bundled regions and does not invent the live town', async () => {
  const { loader } = loaderWith({
    'data/schema.json': new Error('offline'),
  });
  const res = await loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  const got = await res.json();
  assert.deepEqual(got.map(r => r.id), ['sd']);
  assert.equal(loader.mode, 'bundled');
});

test('schema mismatch falls back to bundled data and drops the cache', async () => {
  const store = L.memoryStore();
  await store.put('data/schema.json', JSON.stringify({ schema: 1 }));
  await store.put('data/regions.json', JSON.stringify([sd, liveTown]));
  const { loader } = loaderWith({
    'data/schema.json': { schema: 99, note: 'tiles are objects now' },
    'data/regions.json': [sd, liveTown],
  }, store);
  const res = await loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  const got = await res.json();
  assert.deepEqual(got.map(r => r.id), ['sd']);
  assert.equal(loader.mode, 'mismatch');
  assert.equal(await store.get('data/regions.json'), null);
  assert.equal(await store.get('data/schema.json'), null);
});

test('after a good fetch, a later offline open uses the cache', async () => {
  const store = L.memoryStore();
  const first = loaderWith({
    'data/schema.json': { schema: 1 },
    'data/regions.json': [sd, liveTown],
  }, store);
  const warm = await first.loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  assert.ok((await warm.json()).some(r => r.id === 'livetown'));
  const second = loaderWith({
    'data/schema.json': new Error('offline'),
    'data/regions.json': new Error('offline'),
  }, store);
  let bundled = false;
  const res = await second.loader.fetchData('data/regions.json', async () => { bundled = true; return jsonRes([sd]); });
  const got = await res.json();
  assert.equal(second.loader.mode, 'cache');
  assert.equal(bundled, false);
  assert.ok(got.some(r => r.id === 'livetown'));
});

test('a live body that is not JSON for this schema falls back to the bundle', async () => {
  const { loader } = loaderWith({
    'data/schema.json': { schema: 1 },
    'data/regions.json': 'alert(1)',
  });
  const res = await loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  const text = await res.text();
  assert.equal(text.includes('alert'), false);
  assert.deepEqual(JSON.parse(text).map(r => r.id), ['sd']);
});

test('invalid region list shape falls back to the bundle', async () => {
  const { loader } = loaderWith({
    'data/schema.json': { schema: 1 },
    'data/regions.json': [{ id: '../etc', state: 'FL', center: [1, 2], zoom: 3, bbox: [0, 0, 1, 1] }],
  });
  const res = await loader.fetchData('data/regions.json', async () => jsonRes([sd]));
  assert.deepEqual((await res.json()).map(r => r.id), ['sd']);
});

test('install patches fetch only in the native app', async () => {
  const calls = [];
  const win = {
    GCM_NATIVE: true,
    document: {},
    async fetch(url) {
      calls.push(String(url));
      if (String(url).endsWith('/data/schema.json')) return jsonRes({ schema: 1 });
      if (String(url).endsWith('/data/regions.json')) return jsonRes([sd, liveTown]);
      return jsonRes([sd]);
    },
  };
  L.install(win);
  const res = await win.fetch('data/regions.json');
  assert.ok((await res.json()).some(r => r.id === 'livetown'));
  assert.ok(calls.some(u => u.startsWith('https://golfcartmap.com/data/')));
  assert.ok(calls.every(u => !u.endsWith('.js')));
  const web = { GCM_NATIVE: false, document: {}, fetch: async () => jsonRes([sd]) };
  const orig = web.fetch;
  L.install(web);
  assert.equal(web.fetch, orig);
  assert.equal(web.GCMLiveData, undefined);
});

test('shipped JSON matches the schema the app accepts', () => {
  const pub = path.join(root, 'public');
  const read = rel => JSON.parse(fs.readFileSync(path.join(pub, rel), 'utf8'));
  const schema = read('data/schema.json');
  assert.equal(schema.schema, L.SCHEMA);
  assert.equal(L.schemaNumber(schema), L.SCHEMA);
  assert.equal(L.validate('data/regions.json', read('data/regions.json')), true);
  assert.equal(L.validate('data/rules.json', read('data/rules.json')), true);
  assert.equal(L.validate('data/putinbay/index.json', read('data/putinbay/index.json')), true);
  assert.equal(L.validate('data/putinbay/tiles/-829_416.json', read('data/putinbay/tiles/-829_416.json')), true);
  assert.equal(L.validate('data/putinbay/pois.json', read('data/putinbay/pois.json')), true);
  assert.equal(L.validate('data/sd/chargers.json', read('data/sd/chargers.json')), true);
  assert.equal(L.validate('data/sd/verified.json', read('data/sd/verified.json')), true);
  const html = fs.readFileSync(path.join(pub, 'index.html'), 'utf8');
  const sw = fs.readFileSync(path.join(pub, 'sw.js'), 'utf8');
  const headers = fs.readFileSync(path.join(pub, '_headers'), 'utf8');
  const src = fs.readFileSync(path.join(pub, 'livedata.js'), 'utf8');
  assert.ok(html.indexOf('src="native.js"') < html.indexOf('src="livedata.js"'));
  assert.ok(html.indexOf('src="livedata.js"') < html.indexOf('src="app.js"'));
  assert.match(sw, /'livedata\.js'/);
  assert.match(headers, /\/data\/\*[\s\S]*Access-Control-Allow-Origin: \*/);
  assert.equal(src.includes('eval('), false);
  assert.equal(src.includes('new Function'), false);
  assert.match(src, /https:\/\/golfcartmap\.com/);
});
