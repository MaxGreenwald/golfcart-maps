// gcm-reports Worker: review queue for in-app road/hazard reports (lib/reports.js), on a SQLite-backed Durable Object.
//   POST /r                 one report from /api/report (cleaned again here). 202.
//   GET  /active            reviewed, accepted, unexpired closures/hazards: [{id,issue,lat,lon,road,until}] (public, cached 5 min)
//   GET  /queue?status=     reviewer list           (header x-review-key)
//   POST /review            {id,status,avoid_days?,note?}  (header x-review-key)
// Reports never touch legality data; see lib/reports.js.
import { DurableObject } from 'cloudflare:workers';
import { sanitizeReport, queued, review, activeAvoids } from '../../../lib/reports.js';
import { NOTIFY_TO, MAX_PER_DAY, DIGEST_MAX, isTest, nextSendAt, buildEmail } from '../../../lib/report_notify.js';
const J = (o, s = 200, h = {}) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'access-control-allow-origin': '*', ...h } });
function eq(a, b) { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0 }
export class Queue extends DurableObject {
  constructor(ctx, env) { super(ctx, env); this.sql = ctx.storage.sql; this.sql.exec(`CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, ts INTEGER, status TEXT, row TEXT)`);
    this.sql.exec(`CREATE TABLE IF NOT EXISTS notify(id TEXT PRIMARY KEY, ts INTEGER)`); this.sql.exec(`CREATE TABLE IF NOT EXISTS sent(ts INTEGER)`) }
  lastSent() { return [...this.sql.exec('SELECT MAX(ts) m FROM sent')][0].m || 0 }
  // queue a notification; the alarm sends it no sooner than 5 min after the last email (rest batched into a digest)
  async noteNew(row) { if (!this.env.MAILER || !this.env.MAILER_KEY || isTest(row)) return; this.sql.exec('INSERT OR IGNORE INTO notify VALUES(?,?)', row.id, row.ts);
    if (!(await this.ctx.storage.getAlarm())) await this.ctx.storage.setAlarm(nextSendAt(this.lastSent(), Date.now())) }
  async alarm() {
    const now = Date.now(); this.sql.exec('DELETE FROM sent WHERE ts<?', now - 86400000);
    const ids = [...this.sql.exec('SELECT id FROM notify ORDER BY ts')].map(x => x.id); if (!ids.length) return;
    const wait = nextSendAt(this.lastSent(), now); if (wait > now) { await this.ctx.storage.setAlarm(wait); return }
    if ([...this.sql.exec('SELECT COUNT(*) c FROM sent')][0].c >= MAX_PER_DAY) { await this.ctx.storage.setAlarm(now + 3600000); return }
    const take = ids.slice(-DIGEST_MAX), rows = take.map(id => [...this.sql.exec('SELECT row FROM reports WHERE id=?', id)][0]).filter(Boolean).map(x => JSON.parse(x.row));
    const m = buildEmail(rows, { prod: this.env.ENV_NAME !== 'preview', more: ids.length - take.length });
    const r = await this.env.MAILER.fetch('https://gcm-mailer/send', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + this.env.MAILER_KEY },
      body: JSON.stringify({ to: NOTIFY_TO, subject: m.subject, html: m.html, text: m.text }) });
    if (!r.ok) { console.log('notify failed', r.status, (await r.text()).slice(0, 200)); await this.ctx.storage.setAlarm(now + 10 * 60000); return }
    this.sql.exec('INSERT INTO sent VALUES(?)', now); this.sql.exec('DELETE FROM notify');
  }
  rows(status) { return [...this.sql.exec(status ? 'SELECT row FROM reports WHERE status=? ORDER BY ts DESC LIMIT 500' : 'SELECT row FROM reports ORDER BY ts DESC LIMIT 500', ...(status ? [status] : []))].map(x => JSON.parse(x.row)) }
  async fetch(req) {
    const u = new URL(req.url), now = Date.now();
    if (u.pathname === '/add') { const r = sanitizeReport(await req.json()); if (!r) return J({ error: 'bad report' }, 400);
      const n = [...this.sql.exec('SELECT COUNT(*) c FROM reports WHERE ts>?', now - 86400000)][0].c; if (n > 2000) return J({ error: 'busy' }, 429);
      const row = queued(r, now, now.toString(36) + Math.random().toString(36).slice(2, 7)); this.sql.exec('INSERT INTO reports VALUES(?,?,?,?)', row.id, row.ts, row.status, JSON.stringify(row)); await this.noteNew(row); return J({ id: row.id, status: row.status }, 202) }
    if (u.pathname === '/active') return J(activeAvoids(this.rows('accepted'), now));
    if (u.pathname === '/queue') return J(this.rows(u.searchParams.get('status') || null));
    if (u.pathname === '/review') { const d = await req.json(); const x = [...this.sql.exec('SELECT row FROM reports WHERE id=?', String(d.id || ''))][0]; if (!x) return J({ error: 'not found' }, 404);
      let row; try { row = review(JSON.parse(x.row), d, now) } catch (e) { return J({ error: e.message }, 400) }
      this.sql.exec('UPDATE reports SET status=?, row=? WHERE id=?', row.status, JSON.stringify(row), row.id); return J(row) }
    return J({ error: 'nope' }, 404);
  }
}
export default {
  async fetch(req, env) {
    const u = new URL(req.url), stub = env.QUEUE.get(env.QUEUE.idFromName('global'));
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET,POST', 'access-control-allow-headers': 'content-type' } });
    if (u.pathname === '/r' && req.method === 'POST') { const t = await req.text(); if (t.length > 4000) return J({ error: 'too big' }, 413); return stub.fetch('https://do/add', { method: 'POST', body: t }) }
    if (u.pathname === '/active' && req.method === 'GET') { const r = await stub.fetch('https://do/active'); return new Response(r.body, { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=300', 'access-control-allow-origin': '*' } }) }
    if (u.pathname === '/queue' || u.pathname === '/review') {
      if (!env.REVIEW_KEY || !eq(req.headers.get('x-review-key') || '', env.REVIEW_KEY)) return J({ error: 'unauthorized' }, 401);
      return stub.fetch('https://do' + u.pathname + u.search, { method: req.method, body: req.method === 'POST' ? await req.text() : undefined });
    }
    return new Response('gcm-reports', { status: 404 });
  },
};
