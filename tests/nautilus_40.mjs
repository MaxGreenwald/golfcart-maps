// Nautilus St, La Jolla is posted 40 (Max manual check, Oct 31 2026, t405u): red for golf carts and LSVs, and routes avoid it.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const GCMRouter = require('../public/router.js');
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => JSON.parse(fs.readFileSync(path.join(ROOT, 'public', p), 'utf8'));
const fetchImpl = url => {
  const p = path.join(ROOT, 'public', String(url).replace(/^\//, ''));
  if (!fs.existsSync(p)) return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  const body = JSON.parse(fs.readFileSync(p, 'utf8'));
  return Promise.resolve({ ok: true, status: 200, json: async () => body });
};
const idx = read('data/sd/index.json');
const naut = idx.meta.tiles.flatMap(t => read(`data/sd/tiles/${t}.json`)).filter(s => idx.names[s[0]] === 'Nautilus Street');
// Every Nautilus vertex; a route along it would pass most of them, a crossing only one or two.
const verts = naut.flatMap(s => s[7].map(p => [p[1], p[0]]));
const m = (p, q) => Math.hypot((p[0] - q[0]) * 110540, (p[1] - q[1]) * 93400);

for (const veh of ['golf_cart', 'lsv']) {
  test(`Nautilus St is red and avoided for ${veh}`, { timeout: 60000 }, async () => {
    const region = read('data/regions.json').find(r => r.id === 'sd');
    const api = await GCMRouter.openRegion(region, read('data/rules.json'), veh, fetchImpl);
    assert.equal(naut.length, 26);
    for (const s of naut) assert.equal(api.roadStyle(s).color, '#e5484d', JSON.stringify(s.slice(0, 7)));
    // West end (La Jolla Blvd) to east end (past La Jolla Mesa Dr): the route must not run along Nautilus.
    const legs = await api.legs([{ lat: 32.8312, lon: -117.2800 }, { lat: 32.8338, lon: -117.2495 }]);
    for (const leg of legs) {
      if (!leg.points) continue;
      const on = verts.filter(q => leg.points.some(p => m(p, q) < 8)).length;
      assert.ok(on <= 4, `${veh} route runs along Nautilus (${on} of ${verts.length} vertices)`);
    }
  });
}
