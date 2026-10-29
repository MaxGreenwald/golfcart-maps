// gcm-analytics Worker: anonymous event store on a SQLite-backed Durable Object (works on the
// current Cloudflare token, no D1 needed). Routes:
//   POST /e                      one event (JSON, see lib/analytics.js). Always 204.
//   GET  /stats?days=30          JSON summary for the dashboard   (header x-stats-key or ?k=)
// /stats drops denylisted install ids and internal/test/simulator traffic (lib/analytics_exclude.js).
// That filter runs at read time, so it covers events already stored. It is live only after this
// Worker is deployed; until then production /stats is the unfiltered build.
//   GET  /daily.csv?days=30      one row per day                  (same key)
// Raw events older than 400 days are deleted.
import { DurableObject } from 'cloudflare:workers';
import { sanitize } from '../../../lib/analytics.js';
import { computeStats } from '../../../lib/analytics_stats.js';

const J = (o, s = 200) => new Response(JSON.stringify(o, null, 1), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const NC = () => new Response(null, { status: 204, headers: { 'cache-control': 'no-store', 'access-control-allow-origin': '*' } });
function eq(a, b) { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0 }

export class Events extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env); this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT);
      CREATE INDEX IF NOT EXISTS ev_day ON events(day); CREATE INDEX IF NOT EXISTS ev_event_day ON events(event, day); CREATE INDEX IF NOT EXISTS ev_iid ON events(iid);`);
  }
  add(r, now) {
    const d = new Date(now), day = d.toISOString().slice(0, 10);
    this.sql.exec('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)', now, day, r.event, r.town, r.platform, r.pwa, r.iid, r.sid, JSON.stringify(r.props));
    if (Math.random() < 0.01) this.sql.exec('DELETE FROM events WHERE ts < ?', now - 400 * 864e5);
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray() }
  stats(days, now) { return computeStats((s, ...a) => this.q(s, ...a), days, now); }
  async fetch(req) {
    const u = new URL(req.url), now = Date.now();
    if (u.pathname === '/add') { const r = await req.json(); this.add(r, now); return new Response(null, { status: 204 }) }
    const days = Math.min(400, Math.max(1, +u.searchParams.get('days') || 30));
    return J(this.stats(days, now));
  }
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST', 'access-control-allow-headers': 'content-type', 'access-control-max-age': '86400' } });
    const stub = env.EVENTS.get(env.EVENTS.idFromName('global'));
    if (u.pathname === '/e' && req.method === 'POST') {
      try {
        const t = await req.text(); if (t.length > 4000) return NC();
        const r = sanitize(JSON.parse(t)); if (r) await stub.fetch('https://do/add', { method: 'POST', body: JSON.stringify(r) });
      } catch (_) {}
      return NC();
    }
    if (u.pathname === '/stats' || u.pathname === '/daily.csv') {
      const k = req.headers.get('x-stats-key') || u.searchParams.get('k') || '';
      if (!env.STATS_KEY || !eq(k, env.STATS_KEY)) return J({ error: 'unauthorized' }, 401);
      const s = await (await stub.fetch('https://do/stats?days=' + (u.searchParams.get('days') || 30))).json();
      if (u.pathname === '/stats') return J(s);
      const cols = ['day', 'active_installs', 'sessions', 'new_installs', 'town_views', 'routes_searched', 'routes_found', 'routes_completed', 'road_reports'];
      return new Response([cols.join(','), ...s.daily.map(d => cols.map(c => d[c] ?? 0).join(','))].join('\n') + '\n', { headers: { 'content-type': 'text/csv', 'cache-control': 'no-store' } });
    }
    return new Response('gcm-analytics', { status: 404 });
  },
};
