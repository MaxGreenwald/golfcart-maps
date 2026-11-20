// In-process gcm-partner Worker for node tests: the real Worker and Durable Object code
// on node:sqlite, with a fake clock-free alarm, a fetch stub, and a signed-in session helper.
// Node 22.5 or newer (node:sqlite). Nothing leaves the process.
import { register } from 'node:module';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const PUBLIC_DATA = fileURLToPath(new URL('../public/data/', import.meta.url));

const STUB = 'export class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }';
register('data:text/javascript,' + encodeURIComponent(`
export async function resolve(spec, ctx, next) {
  if (spec === 'cloudflare:workers') return { url: 'data:text/javascript,' + encodeURIComponent(${JSON.stringify(STUB)}), shortCircuit: true };
  return next(spec, ctx);
}`));

const { default: worker, PartnerStore } = await import('../workers/partner/src/index.js');

function sqlFor(db) {
  return {
    exec(query, ...binds) {
      for (const b of binds) if (b === undefined) throw new TypeError('undefined SQL binding in: ' + query.slice(0, 80));
      const many = binds.length === 0 && query.split(';').filter(s => s.trim()).length > 1;
      if (many) { db.exec(query); return { toArray: () => [], one: () => null }; }
      const st = db.prepare(query);
      const rows = /^\s*(select|pragma|with)\b/i.test(query) || /\breturning\b/i.test(query)
        ? st.all(...binds).map(r => ({ ...r }))
        : (st.run(...binds), []);
      return { toArray: () => rows, one: () => rows[0] || null };
    },
  };
}

/**
 * makePartner({ env, fetch }) -> { call(path, init), login(email), store, env, alarm(), outbox }
 * env vars default to the wrangler.toml [vars] minus Google (so /auth/dev works).
 * fetch replaces globalThis.fetch while a call runs (regions.json, mailer, analytics).
 */
export function makePartner(opts = {}) {
  const db = new DatabaseSync(':memory:');
  let alarmAt = null;
  const storage = {
    sql: sqlFor(db),
    async setAlarm(t) { alarmAt = Number(t); },
    async getAlarm() { return alarmAt; },
    async deleteAlarm() { alarmAt = null; },
  };
  const outbox = [];
  const env = {
    SUPER_ADMINS: 'max@golfcartmap.com,maxgreenwald.assistant@gmail.com',
    DEV_AUTH_EMAIL: 'maxgreenwald.assistant@gmail.com',
    PARTNER_SESSION_SECRET: 'test-secret',
    ...(opts.env || {}),
  };
  const store = new PartnerStore({ storage }, env);
  env.STORE = { idFromName: () => 'global', get: () => store };
  const regions = opts.regions || [{ id: 'sd', slug: 'sandiego' }];
  const fakeFetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input.url;
    if (/\/data\/regions\.json$/.test(url)) return new Response(JSON.stringify(regions), { headers: { 'content-type': 'application/json' } });
    // Site JSON (rules.json, schema.json) comes from this checkout's public/data.
    const site = /\/data\/([a-z0-9_-]+\.json)$/.exec(url);
    if (site && existsSync(PUBLIC_DATA + site[1])) return new Response(readFileSync(PUBLIC_DATA + site[1], 'utf8'), { headers: { 'content-type': 'application/json' } });
    if (opts.fetch) {
      const r = await opts.fetch(url, init || {}, outbox);
      if (r) return r;
    }
    return new Response(JSON.stringify({ error: 'offline in tests' }), { status: 599 });
  };
  // Overlapping calls (the dev server serves several at once) share one install of the fake.
  let depth = 0, real = null;
  async function withFetch(fn) {
    if (depth++ === 0) { real = globalThis.fetch; globalThis.fetch = fakeFetch; }
    try { return await fn(); } finally { if (--depth === 0) globalThis.fetch = real; }
  }
  const cookies = new Map();
  async function call(path, init = {}) {
    const headers = new Headers(init.headers || {});
    if (init.json !== undefined) headers.set('content-type', 'application/json');
    const who = init.as;
    if (who && cookies.has(who)) headers.set('cookie', cookies.get(who));
    headers.set('x-partner-origin', 'https://golfcartmap.test');
    const req = new Request('https://gcm-partner.test' + path, {
      method: init.method || (init.json !== undefined ? 'POST' : 'GET'),
      headers,
      body: init.json !== undefined ? JSON.stringify(init.json) : init.body,
    });
    const res = await withFetch(() => worker.fetch(req, env));
    const bytes = Buffer.from(await res.arrayBuffer());
    const text = bytes.toString('utf8');
    let body = null;
    try { body = JSON.parse(text); } catch { body = text; }
    return { status: res.status, body, headers: res.headers, bytes };
  }
  async function login(email) {
    const r = await call('/auth/dev', { json: { email, expect: email } });
    if (r.status !== 200) throw new Error('login failed: ' + JSON.stringify(r.body));
    const set = r.headers.get('set-cookie') || '';
    cookies.set(email, set.split(';')[0]);
    return email;
  }
  /** Super-admin creates a shop owned by ownerEmail; returns the shop row. */
  async function seedShop(fields = {}) {
    const boss = await login('max@golfcartmap.com');
    const made = await call('/admin/shops', { as: boss, json: { name: fields.name || 'La Jolla Cart Co', slug: fields.slug || 'lajollacartco', region_id: fields.region_id || 'sd' } });
    if (made.status !== 201) throw new Error('seed failed: ' + JSON.stringify(made.body));
    const owner = fields.owner || 'owner@example.com';
    await call('/admin/shops/' + made.body.shop.id, { as: boss, method: 'PATCH', json: { owner_email: owner, ...(fields.patch || {}) } });
    await login(owner);
    return { shop: made.body.shop, owner, boss };
  }
  async function alarm() {
    if (typeof store.alarm !== 'function') throw new Error('PartnerStore has no alarm()');
    return withFetch(() => store.alarm());
  }
  return { call, login, seedShop, store, env, alarm, outbox, alarmAt: () => alarmAt, db };
}
