// Bundled by scripts/analytics_rows_read.mjs and run in local workerd (Miniflare). Not deployed.
// Two Durable Objects on the same synthetic events:
//   Before: the pre-change schema and read-time SQL (tests/fixtures/*_legacy.mjs)
//   After:  the real Events class from workers/analytics/src/index.js
// Both wrap ctx.storage.sql so every statement adds its cursor.rowsRead, the number Cloudflare bills.
import { Events } from '../workers/analytics/src/index.js';
import { computeStats as legacyStats } from '../tests/fixtures/analytics_stats_legacy.mjs';
import { computeShopStats as legacyShopStats } from '../tests/fixtures/shop_stats_legacy.mjs';
import { insertEvent } from '../lib/analytics_store.js';
import { DurableObject } from 'cloudflare:workers';

function meter(raw) {
  const m = { rows: 0, statements: 0 };
  m.sql = {
    exec(s, ...a) {
      const c = raw.exec(s, ...a); const arr = c.toArray();
      m.rows += c.rowsRead; m.statements++; if (m.log) m.log.push([s.replace(/\s+/g, ' ').replace(/^WITH excluded.*?\) (?=SELECT)/, '').slice(0, 70), c.rowsRead]);
      return { toArray: () => arr, one: () => arr[0] };
    },
  };
  return m;
}

const KINDS = ['session', 'town_viewed', 'town_viewed', 'route_searched', 'landing_view', 'map_open', 'cta_try_map_click', 'partner_unlock'];
const TOWNS = ['sd', 'myrtle', 'staug', 'coachella', 'villages'];
// n events spread evenly over `spanDays` days ending at `now`, ~4 events per install.
export function synth(n, now, spanDays, offsetDays = 0) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const ts = now - offsetDays * 864e5 - Math.floor(i * (spanDays * 864e5) / n);
    const ev = KINDS[i % KINDS.length];
    const props = ev === 'session' ? { new_install: i % 3 === 0, utm_source: i % 97 === 0 ? 'e2e' : (i % 5 ? 'flyer' : undefined), ref: 'google.com' }
      : ev === 'route_searched' ? { ok: i % 2 === 0, mi: 1.5 }
      : ev === 'partner_unlock' ? { shop: 'beachmode', code: 'ab' + (i % 4) }
      : i % 211 === 0 ? { internal: 'sim' } : {};
    out.push({ ts, r: { event: ev, town: TOWNS[i % TOWNS.length], platform: i % 4 ? 'web' : 'ios', pwa: 0, iid: `${offsetDays}-${String(i % Math.max(1, n >> 2)).padStart(8, '0')}-iid`, sid: 'sess-' + i, props } });
  }
  return out;
}

const PATHS = ['/stats?days=7', '/stats?days=30', '/shop-stats?shop=beachmode&days=30', '/top-iids?town=sd&days=7'];

export class After extends Events {
  constructor(ctx, env) { super(ctx, env); this.m = meter(ctx.storage.sql); this.sql = this.m.sql; }
  async fetch(req) {
    const u = new URL(req.url);
    if (u.pathname === '/seed') {
      const { n, now, span, offset } = await req.json();
      for (const { ts, r } of synth(n, now, span, offset)) insertEvent((s, ...a) => this.q(s, ...a), (s, ...a) => { this.sql.exec(s, ...a); }, r, ts);
      return new Response('ok');
    }
    if (u.pathname === '/measure') {
      const out = {};
      for (const p of PATHS) {
        this.statsCache.clear();
        this.m.rows = 0; this.m.statements = 0;
        this.m.log = [];
        const r = await super.fetch(new Request('https://do' + p));
        out[p] = { rows: this.m.rows, statements: this.m.statements, by_statement: this.m.log, body: await r.json() };
        this.m.log = null;
      }
      this.m.rows = 0; this.m.statements = 0;
      await super.fetch(new Request('https://do/stats?days=7'));
      await super.fetch(new Request('https://do/stats?days=7'));
      out.cached_repeat = { rows: this.m.rows, statements: this.m.statements };
      this.m.rows = 0; this.m.statements = 0;
      this.add({ event: 'session', town: 'sd', platform: 'web', pwa: 0, iid: 'ingest-probe-iid', sid: 'sess-probe', props: { utm_source: 'flyer' } }, Date.now());
      out.ingest_one = { rows: this.m.rows, statements: this.m.statements };
      this.m.rows = 0; this.m.statements = 0;
      this.sql.exec("DELETE FROM meta WHERE k='signal'");
      this.m.rows = 0; this.m.statements = 0;
      const { ensureSchema } = await import('../lib/analytics_store.js');
      ensureSchema((s, ...a) => { this.sql.exec(s, ...a); }, (s, ...a) => this.q(s, ...a));
      out.migration_once = { rows: this.m.rows, statements: this.m.statements };
      out.window_rows = Object.fromEntries([7, 30].map(d => [d, this.q('SELECT COUNT(*) n FROM events WHERE day>=?', new Date(Date.now() - (d - 1) * 864e5).toISOString().slice(0, 10))[0].n]));
      out.total_rows = this.q('SELECT COUNT(*) n FROM events')[0].n;
      return Response.json(out);
    }
    return super.fetch(req);
  }
}

export class Before extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env); this.m = meter(ctx.storage.sql); this.sql = this.m.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT);
      CREATE INDEX IF NOT EXISTS ev_day ON events(day); CREATE INDEX IF NOT EXISTS ev_event_day ON events(event, day); CREATE INDEX IF NOT EXISTS ev_iid ON events(iid);`);
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray(); }
  async fetch(req) {
    const u = new URL(req.url);
    if (u.pathname === '/seed') {
      const { n, now, span, offset } = await req.json();
      for (const { ts, r } of synth(n, now, span, offset)) {
        this.sql.exec('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)', ts, new Date(ts).toISOString().slice(0, 10), r.event, r.town, r.platform, r.pwa, r.iid, r.sid, JSON.stringify(r.props));
      }
      return new Response('ok');
    }
    if (u.pathname === '/measure') {
      const q = (s, ...a) => this.q(s, ...a), now = Date.now(), out = {};
      const run = (p, f) => { this.m.rows = 0; this.m.statements = 0; const body = JSON.parse(JSON.stringify(f())); out[p] = { rows: this.m.rows, statements: this.m.statements, body }; };
      run(PATHS[0], () => legacyStats(q, 7, now));
      run(PATHS[1], () => legacyStats(q, 30, now));
      run(PATHS[2], () => legacyShopStats(q, { shop: 'beachmode', days: 30, now }));
      // /top-iids SQL did not change; measured on After only.
      // Old ingest: one INSERT, plus a full-table DELETE on 1% of events (no index on ts).
      this.m.rows = 0; this.m.statements = 0;
      this.sql.exec('DELETE FROM events WHERE ts < ?', now - 400 * 864e5);
      out.purge_scan = { rows: this.m.rows, statements: 1 };
      return Response.json(out);
    }
    return new Response('?', { status: 404 });
  }
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    const ns = u.searchParams.get('v') === 'before' ? env.BEFORE : env.AFTER;
    return ns.get(ns.idFromName(u.searchParams.get('db') || 'g')).fetch(req);
  },
};
