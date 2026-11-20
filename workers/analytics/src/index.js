// gcm-analytics Worker: anonymous event store on a SQLite-backed Durable Object (works on the
// current Cloudflare token, no D1 needed). Routes:
//   POST /e                      one event (JSON, see lib/analytics.js). Always 204.
//   GET  /stats?days=30          JSON summary for the dashboard   (header x-stats-key or ?k=)
//   GET  /shop-stats?shop=&days=  one partner shop's activity     (same key; not public)
// /stats and /shop-stats drop denylisted install ids and internal/test/simulator traffic (lib/analytics_exclude.js).
// Each event is checked once when stored (internal_rows, excluded_iids); a change to that file
// re-flags stored events on the next wake after deploy, so the filter still covers events already stored.
//   GET  /daily.csv?days=30      one row per day                  (same key)
//   GET  /top-iids?town=&days=7   per-iid top-N for one town        (same key; not public)
// Raw events older than 400 days are deleted (once per UTC day, via the day index).
// Rows read are billed: the internal/test check runs once per event at ingest (lib/analytics_store.js),
// and a /stats answer is reused for STATS_TTL_MS so retries and back-to-back scripts do not rescan.
import { DurableObject } from 'cloudflare:workers';
import { sanitize } from '../../../lib/analytics.js';
import { computeStats, topIidsByTown } from '../../../lib/analytics_stats.js';
import { computeShopStats } from '../../../lib/shop_stats.js';
import { ensureSchema, insertEvent, purgeOld } from '../../../lib/analytics_store.js';

export const STATS_TTL_MS = 5 * 60 * 1000;

const J = (o, s = 200) => new Response(JSON.stringify(o, null, 1), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const NC = () => new Response(null, { status: 204, headers: { 'cache-control': 'no-store', 'access-control-allow-origin': '*' } });
function eq(a, b) { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0 }

export class Events extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env); this.sql = ctx.storage.sql; this.statsCache = new Map(); this.purgedDay = '';
    ensureSchema((s, ...a) => { this.sql.exec(s, ...a); }, (s, ...a) => this.q(s, ...a));
  }
  add(r, now) {
    const { day } = insertEvent((s, ...a) => this.q(s, ...a), (s, ...a) => { this.sql.exec(s, ...a); }, r, now);
    if (this.purgedDay !== day) {
      const last = (this.q(`SELECT v FROM meta WHERE k='purged_day'`)[0] || {}).v;
      if (last !== day) {
        purgeOld((s, ...a) => this.q(s, ...a), (s, ...a) => { this.sql.exec(s, ...a); }, now);
        this.sql.exec(`INSERT INTO meta(k, v) VALUES('purged_day', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v`, day);
      }
      this.purgedDay = day;
    }
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray() }
  stats(days, now) {
    const hit = this.statsCache.get(days);
    if (hit && now - hit.at < STATS_TTL_MS) return hit.body;
    const body = computeStats((s, ...a) => this.q(s, ...a), days, now);
    this.statsCache.set(days, { at: now, body });
    return body;
  }
  shopStats(shop, days, now) { return computeShopStats((s, ...a) => this.q(s, ...a), { shop, days, now }); }
  topIids(days, now, town, limit) { return topIidsByTown((s, ...a) => this.q(s, ...a), days, now, { town, limit }); }
  async fetch(req) {
    const u = new URL(req.url), now = Date.now();
    if (u.pathname === '/add') { const r = await req.json(); this.add(r, now); return new Response(null, { status: 204 }) }
    const days = Math.min(400, Math.max(1, +u.searchParams.get('days') || 30));
    if (u.pathname === '/top-iids') {
      try { return J(this.topIids(days, now, u.searchParams.get('town') || '', +(u.searchParams.get('limit') || 5))); }
      catch (e) { return J({ error: String(e && e.message || e) }, 400); }
    }
    if (u.pathname === '/shop-stats') {
      try { return J(this.shopStats(u.searchParams.get('shop') || '', days, now)); }
      catch (e) { return J({ error: String(e && e.message || e) }, 400); }
    }
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
        const r = sanitize(JSON.parse(t));
        if (r) {
          const res = await stub.fetch('https://do/add', { method: 'POST', body: JSON.stringify(r) });
          if (!res.ok) console.error('gcm-analytics /e: store returned', res.status);
        }
      } catch (e) {
        // Bad JSON from a client is normal; a storage failure (for example a Durable Object limit) is not.
        if (!(e instanceof SyntaxError)) console.error('gcm-analytics /e: event not stored:', String(e && e.message || e));
      }
      return NC();
    }
    if (u.pathname === '/stats' || u.pathname === '/daily.csv' || u.pathname === '/top-iids' || u.pathname === '/shop-stats') {
      const k = req.headers.get('x-stats-key') || u.searchParams.get('k') || '';
      if (!env.STATS_KEY || !eq(k, env.STATS_KEY)) return J({ error: 'unauthorized' }, 401);
      if (u.pathname === '/top-iids') {
        const qs = new URLSearchParams({ days: u.searchParams.get('days') || '7' });
        if (u.searchParams.get('town')) qs.set('town', u.searchParams.get('town'));
        if (u.searchParams.get('limit')) qs.set('limit', u.searchParams.get('limit'));
        const r = await stub.fetch('https://do/top-iids?' + qs);
        const body = await r.json();
        return J(body, r.status === 400 || body.error ? 400 : 200);
      }
      if (u.pathname === '/shop-stats') {
        const qs = new URLSearchParams({ days: u.searchParams.get('days') || '30', shop: u.searchParams.get('shop') || '' });
        const r = await stub.fetch('https://do/shop-stats?' + qs);
        const body = await r.json();
        return J(body, r.status === 400 || body.error ? 400 : 200);
      }
      const s = await (await stub.fetch('https://do/stats?days=' + (u.searchParams.get('days') || 30))).json();
      if (u.pathname === '/stats') return J(s);
      const cols = ['day', 'active_installs', 'sessions', 'new_installs', 'town_views', 'routes_searched', 'routes_found', 'routes_completed', 'road_reports'];
      return new Response([cols.join(','), ...s.daily.map(d => cols.map(c => d[c] ?? 0).join(','))].join('\n') + '\n', { headers: { 'content-type': 'text/csv', 'cache-control': 'no-store' } });
    }
    return new Response('gcm-analytics', { status: 404 });
  },
};
