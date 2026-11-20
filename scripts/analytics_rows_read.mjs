#!/usr/bin/env node
// Durable Object rows read by gcm-analytics, before vs after the stored internal/test flag.
// Runs both versions in local workerd (Miniflare) on the same synthetic events and prints
// cursor.rowsRead per request, the number Cloudflare bills. Nothing touches Cloudflare.
//
//   npm install --prefix /tmp/mf miniflare@3 esbuild@0.17   (once)
//   NODE_PATH=/tmp/mf/node_modules node scripts/analytics_rows_read.mjs [--events 15000] [--check]
//
// --check exits 1 unless: /stats output is identical before and after, a 7-day /stats reads
// at most 1/10 of what it used to, and adding old history (outside every window) does not
// change what /stats reads.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const req = createRequire(path.join(process.env.NODE_PATH || process.cwd(), 'x.js'));
const load = name => import(req.resolve(name));
const { Miniflare } = await load('miniflare');
const { build } = await load('esbuild');

const args = process.argv.slice(2);
const N = +(args[args.indexOf('--events') + 1] || 0) || 15000;
const CHECK = args.includes('--check');
const here = path.dirname(fileURLToPath(import.meta.url));
const out = await build({ entryPoints: [path.join(here, 'analytics_rows_bench_do.js')], bundle: true, format: 'esm', write: false, external: ['cloudflare:workers'], logLevel: 'silent' });
const now = Date.now();
const result = {};
// A fresh local runtime per scenario keeps the old SQL's memory use from one run out of the next.
for (const [label, extraOld] of [['recent', 0], ['plus_old_history', N]]) {
  result[label] = {};
  for (const v of ['before', 'after']) {
    const mf = new Miniflare({
      modules: true, script: out.outputFiles[0].text, compatibilityDate: '2025-07-01',
      durableObjects: { AFTER: { className: 'After', useSQLite: true }, BEFORE: { className: 'Before', useSQLite: true } },
    });
    const call = async (p, body) => {
      const r = await mf.dispatchFetch(`http://x${p}?v=${v}&db=${label}`, body ? { method: 'POST', body: JSON.stringify(body) } : {});
      if (!r.ok) throw new Error(`${v} ${p} HTTP ${r.status}: ${await r.text()}`);
      return p === '/measure' ? r.json() : r.text();
    };
    try {
      await call('/seed', { n: N, now, span: 35, offset: 0 });
      if (extraOld) await call('/seed', { n: extraOld, now, span: 300, offset: 40 });
      result[label][v] = await call('/measure');
    } finally { await mf.dispose(); }
  }
}

const strip = b => { const c = JSON.parse(JSON.stringify(b)); delete c.generated; return c; };
const r = result.recent, o = result.plus_old_history;
console.log(`events in table: ${r.after.total_rows - 1} (35 days); 7-day window ${r.after.window_rows[7]}, 30-day window ${r.after.window_rows[30]}`);
console.log('request                                 | before rows read | after rows read | statements before -> after');
for (const p of ['/stats?days=7', '/stats?days=30', '/shop-stats?shop=beachmode&days=30']) {
  console.log(`${p.padEnd(40)}| ${String(r.before[p].rows).padStart(16)} | ${String(r.after[p].rows).padStart(15)} | ${r.before[p].statements} -> ${r.after[p].statements}`);
}
console.log(`${'/top-iids?town=sd&days=7 (unchanged SQL)'.padEnd(40)}| ${'same'.padStart(16)} | ${String(r.after['/top-iids?town=sd&days=7'].rows).padStart(15)} |`);
console.log(`${'/stats?days=7 twice within 5 min'.padEnd(40)}| ${String(2 * r.before['/stats?days=7'].rows).padStart(16)} | ${String(r.after.cached_repeat.rows).padStart(15)} |`);
console.log(`${'store one event (POST /e)'.padEnd(40)}| ${'0 (+1% full scan)'.padStart(16)} | ${String(r.after.ingest_one.rows).padStart(15)} | old purge scan: ${r.before.purge_scan.rows} rows`);
console.log(`${'one-time flag backfill on deploy'.padEnd(40)}| ${'-'.padStart(16)} | ${String(r.after.migration_once.rows).padStart(15)} |`);
console.log(`with ${o.after.total_rows - 1 - (r.after.total_rows - 1)} more events older than 40 days: /stats?days=7 before ${o.before['/stats?days=7'].rows}, after ${o.after['/stats?days=7'].rows}`);

const fails = [];
for (const set of [r, o]) for (const p of ['/stats?days=7', '/stats?days=30', '/shop-stats?shop=beachmode&days=30']) {
  if (JSON.stringify(strip(set.before[p].body)) !== JSON.stringify(strip(set.after[p].body))) fails.push(`${p} output differs before vs after`);
}
if (r.after['/stats?days=7'].rows * 10 > r.before['/stats?days=7'].rows) fails.push('/stats?days=7 did not drop 10x');
if (o.after['/stats?days=7'].rows > r.after['/stats?days=7'].rows * 1.05 + 100) fails.push('/stats?days=7 still grows with history outside the window');
if (r.after.cached_repeat.rows > r.after['/stats?days=7'].rows) fails.push('/stats repeat within 5 min was not cached');
console.log(fails.length ? 'FAIL\n- ' + fails.join('\n- ') : 'OK: outputs identical before/after; reads bounded by the window');
if (CHECK && fails.length) process.exit(1);
