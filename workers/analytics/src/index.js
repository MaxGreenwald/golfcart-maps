// gcm-analytics Worker: anonymous event store on a SQLite-backed Durable Object (works on the
// current Cloudflare token, no D1 needed). Routes:
//   POST /e                      one event (JSON, see lib/analytics.js). Always 204.
//   GET  /stats?days=30          JSON summary for the dashboard   (header x-stats-key or ?k=)
//   GET  /daily.csv?days=30      one row per day                  (same key)
// Raw events older than 400 days are deleted.
import { DurableObject } from 'cloudflare:workers';
import { sanitize } from '../../../lib/analytics.js';

const J = (o, s = 200) => new Response(JSON.stringify(o, null, 1), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
const NC = () => new Response(null, { status: 204, headers: { 'cache-control': 'no-store', 'access-control-allow-origin': '*' } });
function eq(a, b) { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0 }

export class Events extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env); this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT);
      CREATE INDEX IF NOT EXISTS ev_day ON events(day); CREATE INDEX IF NOT EXISTS ev_event_day ON events(event, day);`);
  }
  add(r, now) {
    const d = new Date(now), day = d.toISOString().slice(0, 10);
    this.sql.exec('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)', now, day, r.event, r.town, r.platform, r.pwa, r.iid, r.sid, JSON.stringify(r.props));
    if (Math.random() < 0.01) this.sql.exec('DELETE FROM events WHERE ts < ?', now - 400 * 864e5);
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray() }
  stats(days, now) {
    const since = new Date(now - (days - 1) * 864e5).toISOString().slice(0, 10), wk = new Date(now - 6 * 864e5).toISOString().slice(0, 10);
    const daily = this.q(`SELECT day, COUNT(DISTINCT iid) active_installs, SUM(event='session') sessions, SUM(event='town_viewed') town_views,
        SUM(event='route_searched') routes_searched, SUM(event='route_searched' AND json_extract(props,'$.ok')=1) routes_found,
        SUM(event='route_completed') routes_completed, SUM(event='road_report_filed') road_reports,
        SUM(event='session' AND json_extract(props,'$.new_install')=1) new_installs
      FROM events WHERE day>=? GROUP BY day ORDER BY day DESC`, since);
    const one = (s, ...a) => this.q(s, ...a)[0] || {};
    return {
      days, generated: new Date(now).toISOString(), timezone: 'UTC days',
      weekly_active: one(`SELECT COUNT(DISTINCT iid) installs FROM events WHERE day>=?`, wk).installs || 0,
      weekly_active_route_users: one(`SELECT COUNT(DISTINCT iid) installs FROM events WHERE day>=? AND event='route_searched'`, wk).installs || 0,
      totals: one(`SELECT COUNT(DISTINCT iid) installs, SUM(event='session') sessions, COUNT(*) events FROM events WHERE day>=?`, since),
      daily,
      events: this.q(`SELECT event, COUNT(*) n, COUNT(DISTINCT iid) installs FROM events WHERE day>=? GROUP BY event ORDER BY n DESC`, since),
      towns: this.q(`SELECT town, COUNT(DISTINCT iid) installs, SUM(event='town_viewed') views, SUM(event='route_searched') routes_searched, SUM(event='route_completed') routes_completed, SUM(event='road_report_filed') road_reports
        FROM events WHERE day>=? AND town IS NOT NULL GROUP BY town ORDER BY installs DESC LIMIT 50`, since),
      platforms: this.q(`SELECT platform, pwa, COUNT(DISTINCT iid) installs, SUM(event='session') sessions FROM events WHERE day>=? GROUP BY platform, pwa ORDER BY installs DESC`, since),
      sources: this.q(`SELECT COALESCE(json_extract(props,'$.utm_source'),'(none)') utm_source, COALESCE(json_extract(props,'$.utm_medium'),'') utm_medium,
          COALESCE(json_extract(props,'$.utm_campaign'),'') utm_campaign, COUNT(*) sessions, COUNT(DISTINCT iid) installs
        FROM events WHERE day>=? AND event='session' GROUP BY 1,2,3 ORDER BY sessions DESC LIMIT 30`, since),
      referrers: this.q(`SELECT COALESCE(json_extract(props,'$.ref'),'(direct)') ref, COUNT(*) sessions FROM events WHERE day>=? AND event='session' GROUP BY 1 ORDER BY sessions DESC LIMIT 20`, since),
      first_touch: this.q(`SELECT COALESCE(json_extract(props,'$.ft_source'),'(none)') ft_source, COUNT(DISTINCT iid) installs FROM events WHERE day>=? AND event='session' GROUP BY 1 ORDER BY installs DESC LIMIT 20`, since),
    };
  }
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
