// gcm-partner Worker: rental-shop partner portal (super admin, shop admin, renter unlock).
// Storage: SQLite Durable Object. Auth: Google OAuth when secrets set, else DEV_AUTH_EMAIL mock.
import { DurableObject } from 'cloudflare:workers';
import { assertShopSlug, randomCode, randomToken, couponCode, normalizeSlug } from '../../../lib/partner.js';

const J = (o, s = 200, extra = {}) => new Response(JSON.stringify(o), {
  status: s,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...extra },
});
const TEXT = (t, s = 200, h = {}) => new Response(t, { status: s, headers: { 'cache-control': 'no-store', ...h } });

function supers(env) {
  return new Set(String(env.SUPER_ADMINS || 'max@golfcartmap.com,maxgreenwald.assistant@gmail.com')
    .split(',').map(s => s.trim().toLowerCase()).filter(Boolean));
}
function googleReady(env) { return !!(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET); }
function originOf(req, env) {
  if (env.PUBLIC_ORIGIN) return env.PUBLIC_ORIGIN.replace(/\/$/, '');
  const u = new URL(req.url);
  // When proxied from Pages, Prefer X-Forwarded / Origin.
  const o = req.headers.get('x-partner-origin') || req.headers.get('origin');
  if (o) return o.replace(/\/$/, '');
  return u.origin;
}

async function hmacKey(secret) {
  return crypto.subtle.importKey('raw', new TextEncoder().encode(secret || 'dev-only-partner-secret'), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}
function b64u(buf) {
  const b = buf instanceof ArrayBuffer ? new Uint8Array(buf) : buf;
  let s = ''; for (const x of b) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function ub64(s) {
  const pad = '='.repeat((4 - (s.length % 4)) % 4);
  const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/') + pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
async function signSession(env, payload) {
  const body = b64u(new TextEncoder().encode(JSON.stringify(payload)));
  const sig = b64u(await crypto.subtle.sign('HMAC', await hmacKey(env.PARTNER_SESSION_SECRET), new TextEncoder().encode(body)));
  return body + '.' + sig;
}
async function readSession(env, cookieHeader) {
  const m = /(?:^|;\s*)gcm_partner=([^;]+)/.exec(cookieHeader || '');
  if (!m) return null;
  const [body, sig] = decodeURIComponent(m[1]).split('.');
  if (!body || !sig) return null;
  const ok = await crypto.subtle.verify('HMAC', await hmacKey(env.PARTNER_SESSION_SECRET), ub64(sig), new TextEncoder().encode(body));
  if (!ok) return null;
  try {
    const p = JSON.parse(new TextDecoder().decode(ub64(body)));
    if (!p.email || !p.exp || p.exp * 1000 < Date.now()) return null;
    return p;
  } catch { return null; }
}
function setCookie(token, maxAge = 60 * 60 * 24 * 14) {
  return `gcm_partner=${encodeURIComponent(token)}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}
function clearCookie() {
  return 'gcm_partner=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax';
}

function now() { return Math.floor(Date.now() / 1000); }
function id() { return randomToken(8); }

export class PartnerStore extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS shops(
        id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
        region_id TEXT NOT NULL DEFAULT 'sd', blurb TEXT DEFAULT '',
        logo_url TEXT DEFAULT '', color TEXT DEFAULT '',
        owner_email TEXT DEFAULT '', disabled INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS invites(
        token TEXT PRIMARY KEY, shop_id TEXT NOT NULL, email TEXT NOT NULL,
        created_at INTEGER NOT NULL, used_at INTEGER
      );
      CREATE TABLE IF NOT EXISTS experiences(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, title TEXT NOT NULL,
        description TEXT DEFAULT '', stops_json TEXT NOT NULL DEFAULT '[]',
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS affiliates(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, name TEXT NOT NULL,
        lat REAL NOT NULL, lon REAL NOT NULL, offer TEXT DEFAULT '',
        coupon TEXT DEFAULT '', created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS codes(
        code TEXT PRIMARY KEY, shop_id TEXT NOT NULL, experience_id TEXT,
        multi_use INTEGER NOT NULL DEFAULT 1, max_uses INTEGER NOT NULL DEFAULT 0,
        uses INTEGER NOT NULL DEFAULT 0, expires_at INTEGER, created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
    `);
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray(); }
  one(s, ...a) { return this.q(s, ...a)[0] || null; }

  shopRow(r) {
    if (!r) return null;
    return {
      id: r.id, slug: r.slug, name: r.name, region_id: r.region_id,
      blurb: r.blurb || '', logo_url: r.logo_url || '', color: r.color || '',
      owner_email: r.owner_email || '', disabled: !!r.disabled, created_at: r.created_at,
    };
  }
  expRow(r) {
    if (!r) return null;
    let stops = [];
    try { stops = JSON.parse(r.stops_json || '[]'); } catch { stops = []; }
    return { id: r.id, shop_id: r.shop_id, title: r.title, description: r.description || '', stops, created_at: r.created_at, updated_at: r.updated_at };
  }
  affRow(r) {
    if (!r) return null;
    return { id: r.id, shop_id: r.shop_id, name: r.name, lat: r.lat, lon: r.lon, offer: r.offer || '', coupon: r.coupon || '', created_at: r.created_at };
  }

  async fetch(req) {
    const u = new URL(req.url);
    const path = u.pathname;
    const method = req.method;
    let body = null;
    if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
      try { body = await req.json(); } catch { body = {}; }
    }
    try {
      if (path === '/shops' && method === 'GET') {
        const all = u.searchParams.get('all') === '1';
        const rows = this.q(all ? 'SELECT * FROM shops ORDER BY created_at DESC' : 'SELECT * FROM shops WHERE disabled=0 ORDER BY created_at DESC');
        return J({ shops: rows.map(r => this.shopRow(r)) });
      }
      if (path === '/shops' && method === 'POST') {
        const name = String(body.name || '').trim();
        const region_id = String(body.region_id || 'sd').trim() || 'sd';
        const regionSlugs = body.region_slugs || [];
        const check = assertShopSlug(body.slug || name, regionSlugs);
        if (!check.ok) return J({ error: check.error }, 400);
        if (!name) return J({ error: 'Display name required' }, 400);
        if (this.one('SELECT id FROM shops WHERE slug=?', check.slug)) return J({ error: 'Slug already taken' }, 409);
        const sid = id();
        this.sql.exec(
          'INSERT INTO shops(id,slug,name,region_id,created_at) VALUES(?,?,?,?,?)',
          sid, check.slug, name, region_id, now(),
        );
        return J({ shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', sid)) }, 201);
      }
      if (path.startsWith('/shops/') && method === 'PATCH') {
        const sid = path.slice('/shops/'.length);
        const sh = this.one('SELECT * FROM shops WHERE id=?', sid);
        if (!sh) return J({ error: 'not found' }, 404);
        const name = body.name != null ? String(body.name).trim() : sh.name;
        const region_id = body.region_id != null ? String(body.region_id).trim() : sh.region_id;
        const blurb = body.blurb != null ? String(body.blurb) : sh.blurb;
        const logo_url = body.logo_url != null ? String(body.logo_url) : sh.logo_url;
        const color = body.color != null ? String(body.color) : sh.color;
        const owner_email = body.owner_email != null ? String(body.owner_email).trim().toLowerCase() : sh.owner_email;
        const disabled = body.disabled != null ? (body.disabled ? 1 : 0) : sh.disabled;
        this.sql.exec(
          'UPDATE shops SET name=?, region_id=?, blurb=?, logo_url=?, color=?, owner_email=?, disabled=? WHERE id=?',
          name, region_id, blurb, logo_url, color, owner_email, disabled, sid,
        );
        return J({ shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', sid)) });
      }
      if (path.match(/^\/shops\/[^/]+\/invite$/) && method === 'POST') {
        const sid = path.split('/')[2];
        const sh = this.one('SELECT * FROM shops WHERE id=?', sid);
        if (!sh) return J({ error: 'not found' }, 404);
        const email = String(body.email || '').trim().toLowerCase();
        if (!email || !email.includes('@')) return J({ error: 'Valid email required' }, 400);
        const token = randomToken(16);
        this.sql.exec('INSERT INTO invites(token,shop_id,email,created_at) VALUES(?,?,?,?)', token, sid, email, now());
        // MVP: invite link only (no outbound email from this worker). Documented in research/.
        return J({ invite_token: token, email, shop_id: sid, path: `/partner?invite=${token}` }, 201);
      }
      if (path.startsWith('/invite/') && method === 'GET') {
        const token = path.slice('/invite/'.length);
        const inv = this.one('SELECT * FROM invites WHERE token=?', token);
        if (!inv || inv.used_at) return J({ error: 'Invite invalid or used' }, 404);
        const sh = this.shopRow(this.one('SELECT * FROM shops WHERE id=?', inv.shop_id));
        return J({ invite: { token, email: inv.email, shop: sh } });
      }
      if (path.startsWith('/invite/') && method === 'POST') {
        const token = path.slice('/invite/'.length);
        const inv = this.one('SELECT * FROM invites WHERE token=?', token);
        if (!inv || inv.used_at) return J({ error: 'Invite invalid or used' }, 404);
        const email = String(body.email || '').trim().toLowerCase();
        if (email !== inv.email) return J({ error: 'Sign in with the invited email' }, 403);
        this.sql.exec('UPDATE invites SET used_at=? WHERE token=?', now(), token);
        this.sql.exec('UPDATE shops SET owner_email=? WHERE id=? AND (owner_email IS NULL OR owner_email="")', email, inv.shop_id);
        return J({ shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', inv.shop_id)) });
      }
      if (path === '/shop-by-owner' && method === 'GET') {
        const email = (u.searchParams.get('email') || '').toLowerCase();
        const sh = this.one('SELECT * FROM shops WHERE lower(owner_email)=? AND disabled=0 ORDER BY created_at DESC LIMIT 1', email);
        return J({ shop: this.shopRow(sh) });
      }
      if (path.startsWith('/shops/') && path.endsWith('/bundle') && method === 'GET') {
        const sid = path.split('/')[2];
        const sh = this.one('SELECT * FROM shops WHERE id=?', sid);
        if (!sh) return J({ error: 'not found' }, 404);
        return J({
          shop: this.shopRow(sh),
          experiences: this.q('SELECT * FROM experiences WHERE shop_id=? ORDER BY created_at DESC', sid).map(r => this.expRow(r)),
          affiliates: this.q('SELECT * FROM affiliates WHERE shop_id=? ORDER BY created_at DESC', sid).map(r => this.affRow(r)),
          codes: this.q('SELECT code,shop_id,experience_id,multi_use,max_uses,uses,expires_at,created_at FROM codes WHERE shop_id=? ORDER BY created_at DESC', sid),
        });
      }
      // Experiences
      if (path.match(/^\/shops\/[^/]+\/experiences$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        const title = String(body.title || '').trim();
        if (!title) return J({ error: 'Title required' }, 400);
        const stops = Array.isArray(body.stops) ? body.stops : [];
        const eid = id();
        const t = now();
        this.sql.exec(
          'INSERT INTO experiences(id,shop_id,title,description,stops_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
          eid, sid, title, String(body.description || ''), JSON.stringify(stops), t, t,
        );
        return J({ experience: this.expRow(this.one('SELECT * FROM experiences WHERE id=?', eid)) }, 201);
      }
      if (path.match(/^\/experiences\/[^/]+$/) && method === 'PATCH') {
        const eid = path.split('/')[2];
        const ex = this.one('SELECT * FROM experiences WHERE id=?', eid);
        if (!ex) return J({ error: 'not found' }, 404);
        const title = body.title != null ? String(body.title).trim() : ex.title;
        const description = body.description != null ? String(body.description) : ex.description;
        const stops = body.stops != null ? JSON.stringify(body.stops) : ex.stops_json;
        this.sql.exec('UPDATE experiences SET title=?, description=?, stops_json=?, updated_at=? WHERE id=?', title, description, stops, now(), eid);
        return J({ experience: this.expRow(this.one('SELECT * FROM experiences WHERE id=?', eid)) });
      }
      if (path.match(/^\/experiences\/[^/]+$/) && method === 'DELETE') {
        const eid = path.split('/')[2];
        this.sql.exec('DELETE FROM experiences WHERE id=?', eid);
        return J({ ok: true });
      }
      // Affiliates
      if (path.match(/^\/shops\/[^/]+\/affiliates$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        const name = String(body.name || '').trim();
        const lat = +body.lat, lon = +body.lon;
        if (!name || !Number.isFinite(lat) || !Number.isFinite(lon)) return J({ error: 'Name and lat/lon required' }, 400);
        const coupon = body.generate_coupon ? couponCode('OFFER') : String(body.coupon || '');
        const aid = id();
        this.sql.exec(
          'INSERT INTO affiliates(id,shop_id,name,lat,lon,offer,coupon,created_at) VALUES(?,?,?,?,?,?,?,?)',
          aid, sid, name, lat, lon, String(body.offer || ''), coupon, now(),
        );
        return J({ affiliate: this.affRow(this.one('SELECT * FROM affiliates WHERE id=?', aid)) }, 201);
      }
      if (path.match(/^\/affiliates\/[^/]+$/) && method === 'PATCH') {
        const aid = path.split('/')[2];
        const af = this.one('SELECT * FROM affiliates WHERE id=?', aid);
        if (!af) return J({ error: 'not found' }, 404);
        let coupon = body.coupon != null ? String(body.coupon) : af.coupon;
        if (body.generate_coupon) coupon = couponCode('OFFER');
        this.sql.exec(
          'UPDATE affiliates SET name=?, lat=?, lon=?, offer=?, coupon=? WHERE id=?',
          body.name != null ? String(body.name).trim() : af.name,
          body.lat != null ? +body.lat : af.lat,
          body.lon != null ? +body.lon : af.lon,
          body.offer != null ? String(body.offer) : af.offer,
          coupon, aid,
        );
        return J({ affiliate: this.affRow(this.one('SELECT * FROM affiliates WHERE id=?', aid)) });
      }
      if (path.match(/^\/affiliates\/[^/]+$/) && method === 'DELETE') {
        this.sql.exec('DELETE FROM affiliates WHERE id=?', path.split('/')[2]);
        return J({ ok: true });
      }
      // Codes
      if (path.match(/^\/shops\/[^/]+\/codes$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        let code = String(body.code || '').trim().toUpperCase() || randomCode(4);
        if (this.one('SELECT code FROM codes WHERE code=?', code)) code = randomCode(5);
        const multi = body.multi_use === false ? 0 : 1;
        const max_uses = +body.max_uses || 0;
        const expires_at = body.expires_days ? now() + (+body.expires_days) * 86400 : (body.expires_at || null);
        this.sql.exec(
          'INSERT INTO codes(code,shop_id,experience_id,multi_use,max_uses,uses,expires_at,created_at) VALUES(?,?,?,?,?,0,?,?)',
          code, sid, body.experience_id || null, multi, max_uses, expires_at, now(),
        );
        return J({ code: this.one('SELECT * FROM codes WHERE code=?', code) }, 201);
      }
      // Public brand + unlock
      if (path.startsWith('/public/') && method === 'GET') {
        const parts = path.slice('/public/'.length).split('/');
        const slug = normalizeSlug(parts[0]);
        const sh = this.one('SELECT * FROM shops WHERE slug=? AND disabled=0', slug);
        if (!sh) return J({ error: 'not found' }, 404);
        const shop = this.shopRow(sh);
        if (parts[1] === 'unlock') {
          const code = String(u.searchParams.get('code') || '').trim().toUpperCase();
          if (!code) return J({ error: 'code required', shop }, 400);
          const c = this.one('SELECT * FROM codes WHERE code=? AND shop_id=?', code, sh.id);
          if (!c) return J({ error: 'Invalid access code', shop }, 403);
          if (c.expires_at && c.expires_at < now()) return J({ error: 'Code expired', shop }, 403);
          if (!c.multi_use && c.uses > 0) return J({ error: 'Code already used', shop }, 403);
          if (c.max_uses > 0 && c.uses >= c.max_uses) return J({ error: 'Code use limit reached', shop }, 403);
          this.sql.exec('UPDATE codes SET uses=uses+1 WHERE code=?', code);
          const experiences = this.q(
            c.experience_id
              ? 'SELECT * FROM experiences WHERE id=? AND shop_id=?'
              : 'SELECT * FROM experiences WHERE shop_id=? ORDER BY created_at DESC',
            ...(c.experience_id ? [c.experience_id, sh.id] : [sh.id]),
          ).map(r => this.expRow(r));
          const affiliates = this.q('SELECT * FROM affiliates WHERE shop_id=? ORDER BY created_at DESC', sh.id).map(r => this.affRow(r));
          return J({ unlocked: true, shop, experiences, affiliates, code });
        }
        // Teaser (no paid content)
        return J({
          shop,
          unlocked: false,
          experience_count: this.one('SELECT COUNT(*) n FROM experiences WHERE shop_id=?', sh.id).n,
          affiliate_count: this.one('SELECT COUNT(*) n FROM affiliates WHERE shop_id=?', sh.id).n,
        });
      }
      return J({ error: 'not found', path }, 404);
    } catch (e) {
      return J({ error: e.message || String(e) }, 500);
    }
  }
}

async function stub(env) {
  return env.STORE.get(env.STORE.idFromName('global'));
}

async function requireUser(req, env) {
  return readSession(env, req.headers.get('cookie'));
}

async function regionSlugsFromOrigin(origin) {
  try {
    const r = await fetch(origin + '/data/regions.json');
    if (!r.ok) return [];
    const rs = await r.json();
    return rs.map(x => x.slug);
  } catch { return []; }
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'access-control-allow-origin': req.headers.get('origin') || '*',
          'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS',
          'access-control-allow-headers': 'content-type',
          'access-control-allow-credentials': 'true',
          'access-control-max-age': '86400',
        },
      });
    }

    // Health
    if (u.pathname === '/' || u.pathname === '/health') {
      return J({ ok: true, service: 'gcm-partner', google: googleReady(env), dev_auth: !googleReady(env) && !!env.DEV_AUTH_EMAIL });
    }

    const store = await stub(env);
    const doFetch = (path, init) => store.fetch(new Request('https://do' + path, init));

    // ---- Auth ----
    if (u.pathname === '/auth/me' && req.method === 'GET') {
      const sess = await requireUser(req, env);
      if (!sess) return J({ user: null, google: googleReady(env), dev_auth: !googleReady(env) && !!env.DEV_AUTH_EMAIL });
      const isSuper = supers(env).has(sess.email);
      let shop = null;
      if (!isSuper) {
        const r = await (await doFetch('/shop-by-owner?email=' + encodeURIComponent(sess.email))).json();
        shop = r.shop;
      }
      return J({ user: { email: sess.email, name: sess.name || '', super: isSuper }, shop, google: googleReady(env), dev_auth: !googleReady(env) && !!env.DEV_AUTH_EMAIL });
    }

    if (u.pathname === '/auth/logout' && req.method === 'POST') {
      return J({ ok: true }, 200, { 'set-cookie': clearCookie() });
    }

    if (u.pathname === '/auth/dev' && req.method === 'POST') {
      if (googleReady(env)) return J({ error: 'Dev auth disabled when Google OAuth is configured' }, 400);
      if (!env.DEV_AUTH_EMAIL) return J({ error: 'DEV_AUTH_EMAIL not set' }, 400);
      let body = {};
      try { body = await req.json(); } catch { body = {}; }
      const email = String(body.email || env.DEV_AUTH_EMAIL).trim().toLowerCase();
      const allowed = new Set([...supers(env), String(env.DEV_AUTH_EMAIL).toLowerCase()]);
      if (body.invite) {
        const inv = await (await doFetch('/invite/' + body.invite)).json();
        if (inv.invite) allowed.add(String(inv.invite.email).toLowerCase());
      }
      if (body.expect) allowed.add(String(body.expect).toLowerCase());
      const owned = await (await doFetch('/shop-by-owner?email=' + encodeURIComponent(email))).json();
      if (owned.shop) allowed.add(email);
      if (!allowed.has(email)) {
        return J({ error: 'Email not on allowlist for mock login', hint: 'Use a super-admin email, an invite expect=, or DEV_AUTH_EMAIL' }, 403);
      }
      const token = await signSession(env, { email, name: body.name || email.split('@')[0], exp: now() + 14 * 86400 });
      return J({ ok: true, email }, 200, { 'set-cookie': setCookie(token) });
    }

    if (u.pathname === '/auth/google' && req.method === 'GET') {
      if (!googleReady(env)) return J({ error: 'Google OAuth not configured', use: '/auth/dev' }, 501);
      const o = originOf(req, env);
      const redirect = o + '/api/partner/auth/callback';
      const st = randomToken(12);
      const url = new URL('https://accounts.google.com/o/oauth2/v2/auth');
      url.searchParams.set('client_id', env.GOOGLE_CLIENT_ID);
      url.searchParams.set('redirect_uri', redirect);
      url.searchParams.set('response_type', 'code');
      url.searchParams.set('scope', 'openid email profile');
      url.searchParams.set('access_type', 'online');
      url.searchParams.set('prompt', 'select_account');
      url.searchParams.set('state', st);
      return new Response(null, {
        status: 302,
        headers: {
          location: url.toString(),
          'set-cookie': `gcm_oauth_st=${st}; Max-Age=600; Path=/; HttpOnly; Secure; SameSite=Lax`,
          'cache-control': 'no-store',
        },
      });
    }

    if (u.pathname === '/auth/callback' && req.method === 'GET') {
      if (!googleReady(env)) return TEXT('Google OAuth not configured', 501);
      const o = originOf(req, env);
      const code = u.searchParams.get('code');
      const st = u.searchParams.get('state');
      const cst = (/(?:^|;\s*)gcm_oauth_st=([^;]+)/.exec(req.headers.get('cookie') || '') || [])[1];
      if (!code || !st || st !== cst) return TEXT('Bad OAuth state', 400);
      const redirect = o + '/api/partner/auth/callback';
      const tokRes = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          code,
          client_id: env.GOOGLE_CLIENT_ID,
          client_secret: env.GOOGLE_CLIENT_SECRET,
          redirect_uri: redirect,
          grant_type: 'authorization_code',
        }),
      });
      const tok = await tokRes.json();
      if (!tok.access_token) return TEXT('Token exchange failed', 400);
      const ui = await (await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
        headers: { authorization: 'Bearer ' + tok.access_token },
      })).json();
      const email = String(ui.email || '').toLowerCase();
      if (!email) return TEXT('No email from Google', 400);
      const token = await signSession(env, { email, name: ui.name || '', exp: now() + 14 * 86400 });
      return new Response(null, {
        status: 302,
        headers: {
          location: o + '/partner',
          'set-cookie': setCookie(token) + ', gcm_oauth_st=; Max-Age=0; Path=/',
          'cache-control': 'no-store',
        },
      });
    }

    // ---- Authed API ----
    const sess = await requireUser(req, env);
    const isSuper = sess && supers(env).has(sess.email);

    if (u.pathname === '/admin/shops' && req.method === 'GET') {
      if (!isSuper) return J({ error: 'forbidden' }, 403);
      return doFetch('/shops?all=1');
    }
    if (u.pathname === '/admin/shops' && req.method === 'POST') {
      if (!isSuper) return J({ error: 'forbidden' }, 403);
      const o = originOf(req, env);
      const region_slugs = await regionSlugsFromOrigin(o);
      const body = await req.json();
      return doFetch('/shops', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ...body, region_slugs }) });
    }
    if (u.pathname.match(/^\/admin\/shops\/[^/]+$/) && req.method === 'PATCH') {
      if (!isSuper) return J({ error: 'forbidden' }, 403);
      const sid = u.pathname.split('/').pop();
      return doFetch('/shops/' + sid, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: await req.text() });
    }
    if (u.pathname.match(/^\/admin\/shops\/[^/]+\/invite$/) && req.method === 'POST') {
      if (!isSuper) return J({ error: 'forbidden' }, 403);
      const sid = u.pathname.split('/')[3];
      return doFetch('/shops/' + sid + '/invite', { method: 'POST', headers: { 'content-type': 'application/json' }, body: await req.text() });
    }

    if (u.pathname === '/invite/peek' && req.method === 'GET') {
      const token = u.searchParams.get('token') || '';
      return doFetch('/invite/' + token);
    }
    if (u.pathname === '/invite/accept' && req.method === 'POST') {
      if (!sess) return J({ error: 'sign in first' }, 401);
      const body = await req.json();
      return doFetch('/invite/' + body.token, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email: sess.email }) });
    }

    async function shopFor(sess) {
      if (!sess) return null;
      if (supers(env).has(sess.email)) {
        // Super may pass ?shop_id=
        return null;
      }
      const r = await (await doFetch('/shop-by-owner?email=' + encodeURIComponent(sess.email))).json();
      return r.shop;
    }

    if (u.pathname === '/shop' && req.method === 'GET') {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      let shop = await shopFor(sess);
      if (!shop && isSuper && u.searchParams.get('shop_id')) {
        const b = await (await doFetch('/shops/' + u.searchParams.get('shop_id') + '/bundle')).json();
        return J(b);
      }
      if (!shop) return J({ error: 'no shop' }, 404);
      return doFetch('/shops/' + shop.id + '/bundle');
    }
    if (u.pathname === '/shop' && req.method === 'PATCH') {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      let shop = await shopFor(sess);
      const body = await req.json();
      if (!shop && isSuper && body.shop_id) shop = { id: body.shop_id };
      if (!shop) return J({ error: 'no shop' }, 404);
      // Shop admins may not disable or reassign owner
      if (!isSuper) {
        delete body.disabled;
        delete body.owner_email;
        delete body.slug;
      }
      return doFetch('/shops/' + shop.id, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    }

    async function ensureShopAccess(shopId) {
      if (!sess) return { error: J({ error: 'unauthorized' }, 401) };
      if (isSuper) return { shopId };
      const shop = await shopFor(sess);
      if (!shop || shop.id !== shopId) return { error: J({ error: 'forbidden' }, 403) };
      return { shopId };
    }

    if (u.pathname.match(/^\/shop\/experiences$/) && req.method === 'POST') {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      const body = await req.json();
      let shop = await shopFor(sess);
      if (!shop && isSuper && body.shop_id) shop = { id: body.shop_id };
      if (!shop) return J({ error: 'no shop' }, 404);
      return doFetch('/shops/' + shop.id + '/experiences', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    }
    if (u.pathname.match(/^\/shop\/experiences\/[^/]+$/) && (req.method === 'PATCH' || req.method === 'DELETE')) {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      const eid = u.pathname.split('/').pop();
      // Ownership check via bundle would be nicer; MVP trusts shop owner session + super.
      const shop = await shopFor(sess);
      if (!shop && !isSuper) return J({ error: 'forbidden' }, 403);
      return doFetch('/experiences/' + eid, { method: req.method, headers: { 'content-type': 'application/json' }, body: req.method === 'PATCH' ? await req.text() : undefined });
    }

    if (u.pathname === '/shop/affiliates' && req.method === 'POST') {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      const body = await req.json();
      let shop = await shopFor(sess);
      if (!shop && isSuper && body.shop_id) shop = { id: body.shop_id };
      if (!shop) return J({ error: 'no shop' }, 404);
      return doFetch('/shops/' + shop.id + '/affiliates', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    }
    if (u.pathname.match(/^\/shop\/affiliates\/[^/]+$/) && (req.method === 'PATCH' || req.method === 'DELETE')) {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      const shop = await shopFor(sess);
      if (!shop && !isSuper) return J({ error: 'forbidden' }, 403);
      const aid = u.pathname.split('/').pop();
      return doFetch('/affiliates/' + aid, { method: req.method, headers: { 'content-type': 'application/json' }, body: req.method === 'PATCH' ? await req.text() : undefined });
    }

    if (u.pathname === '/shop/codes' && req.method === 'POST') {
      if (!sess) return J({ error: 'unauthorized' }, 401);
      const body = await req.json();
      let shop = await shopFor(sess);
      if (!shop && isSuper && body.shop_id) shop = { id: body.shop_id };
      if (!shop) return J({ error: 'no shop' }, 404);
      return doFetch('/shops/' + shop.id + '/codes', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    }

    // Public (no auth)
    if (u.pathname.startsWith('/public/')) {
      return doFetch(u.pathname + u.search, { method: 'GET' });
    }

    return J({ error: 'not found', path: u.pathname }, 404);
  },
};
