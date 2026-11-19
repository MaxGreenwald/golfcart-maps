// gcm-partner Worker: rental-shop partner portal (super admin, shop admin, renter unlock).
// Storage: SQLite Durable Object. Auth: Google OAuth when secrets set, else DEV_AUTH_EMAIL mock.
import { DurableObject } from 'cloudflare:workers';
import { assertShopSlug, randomCode, randomToken, couponCode, normalizeSlug, shopAccess, codeExpiry, cleanPlace, SHOP_VEHICLES, shopVehicle, nearestStart, grantExpiry, handoffProblem, HANDOFF_TTL, cleanRental, rentalFromRow, cleanReturnBy, cleanRangeMi, cleanReturnSpot, cleanPhone, withPark, bytesFromB64, cleanStops, storeImage, MEDIA_MAX_COUNT } from '../../../lib/partner.js';
import { fetchShopStats } from '../../../lib/shop_stats.js';
import { handlePlacesRequest, quotaBuckets, quotaAllowed } from '../../../lib/partner_places.js';
import { sameTown, pushStops, brandFields, experiencePayload } from '../../../lib/partner_templates.js';
import { cleanBooking, bookingRow, rulesLines, welcomeEmail, welcomeSms, BOOKING_KEEP_DAYS, validZone } from '../../../lib/partner_bookings.js';
import { sendMail, mailState } from '../../../lib/partner_mail.js';
import { sendSms, smsProvider } from '../../../lib/partner_sms.js';
import { cleanReport, reportPhotoKey, reportEmail, reportRow, REPORT_KINDS, REPORT_KEEP_DAYS, REPORTS_PER_CODE_DAY } from '../../../lib/partner_reports.js';

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
    this.ensureReports();
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
      CREATE TABLE IF NOT EXISTS places(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL,
        lat REAL NOT NULL, lon REAL NOT NULL, note TEXT DEFAULT '', link TEXT DEFAULT '',
        created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS codes(
        code TEXT PRIMARY KEY, shop_id TEXT NOT NULL, experience_id TEXT,
        multi_use INTEGER NOT NULL DEFAULT 1, max_uses INTEGER NOT NULL DEFAULT 0,
        uses INTEGER NOT NULL DEFAULT 0, expires_at INTEGER, created_at INTEGER NOT NULL
      );
      CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS grants(grant TEXT PRIMARY KEY, shop_id TEXT NOT NULL, code TEXT NOT NULL, expires_at INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS handoffs(token TEXT PRIMARY KEY, shop_id TEXT NOT NULL, code TEXT NOT NULL, expires_at INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0);
      CREATE TABLE IF NOT EXISTS media(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, kind TEXT NOT NULL,
        r2_key TEXT NOT NULL, content_type TEXT NOT NULL, bytes INTEGER NOT NULL, created_at INTEGER NOT NULL
      );
    `);
    // Per-shop rental vehicle (road rules on /p/<slug>). Added Oct 29 2026.
    const cols = this.sql.exec('PRAGMA table_info(shops)').toArray().map(c => c.name);
    if (!cols.includes('vehicle')) this.sql.exec("ALTER TABLE shops ADD COLUMN vehicle TEXT DEFAULT ''");
    // Pickup, return, phone, cart rules. Omitted from the locked teaser. Added Nov 10 2026.
    if (!cols.includes('rental_json')) this.sql.exec("ALTER TABLE shops ADD COLUMN rental_json TEXT DEFAULT ''");
    // Shop phone for the renter Help button. A rental info card should keep this column name.
    if (!cols.includes('phone')) this.sql.exec("ALTER TABLE shops ADD COLUMN phone TEXT DEFAULT ''");
    // Per-experience nearest-stop start (on by default; existing rows read 1). Added Oct 31 2026.
    const exCols = this.sql.exec('PRAGMA table_info(experiences)').toArray().map(c => c.name);
    if (!exCols.includes('nearest_start')) this.sql.exec('ALTER TABLE experiences ADD COLUMN nearest_start INTEGER NOT NULL DEFAULT 1');
    // Return reminders. Names match the rental info card: return_by HH:MM, range_mi, return lat/lon.
    if (!cols.includes('return_by')) this.sql.exec("ALTER TABLE shops ADD COLUMN return_by TEXT DEFAULT ''");
    if (!cols.includes('range_mi')) this.sql.exec('ALTER TABLE shops ADD COLUMN range_mi REAL DEFAULT 0');
    if (!cols.includes('return_lat')) this.sql.exec('ALTER TABLE shops ADD COLUMN return_lat REAL');
    if (!cols.includes('return_lon')) this.sql.exec('ALTER TABLE shops ADD COLUMN return_lon REAL');
    if (!exCols.includes('template_id')) this.sql.exec('ALTER TABLE experiences ADD COLUMN template_id TEXT');
    const afCols = this.sql.exec('PRAGMA table_info(affiliates)').toArray().map(c => c.name);
    if (!afCols.includes('template_id')) this.sql.exec('ALTER TABLE affiliates ADD COLUMN template_id TEXT');
    const plCols = this.sql.exec('PRAGMA table_info(places)').toArray().map(c => c.name);
    if (!plCols.includes('template_id')) this.sql.exec('ALTER TABLE places ADD COLUMN template_id TEXT');
    if (!cols.includes('page_template_id')) this.sql.exec('ALTER TABLE shops ADD COLUMN page_template_id TEXT');
    // Rental-day bookings (renter contact + return time). Rows are deleted 30 days after return.
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS bookings(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, renter_name TEXT NOT NULL, email TEXT NOT NULL,
        phone TEXT DEFAULT '', return_at INTEGER NOT NULL, tz TEXT NOT NULL, code TEXT NOT NULL,
        welcome_status TEXT DEFAULT 'pending', welcome_at INTEGER, sms_status TEXT DEFAULT 'off',
        created_at INTEGER NOT NULL
      )
    `);
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS places_quota(
        shop_id TEXT NOT NULL, bucket TEXT NOT NULL, count INTEGER NOT NULL,
        PRIMARY KEY (shop_id, bucket)
      )
    `);
  }
  ensureReports() {
    // Renter problem reports (cart, what happened, optional note, contact, photo). Kept 90 days.
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS reports(
        id TEXT PRIMARY KEY, shop_id TEXT NOT NULL, code TEXT NOT NULL, cart TEXT DEFAULT '',
        kind TEXT NOT NULL, note TEXT DEFAULT '', contact_name TEXT DEFAULT '', contact_phone TEXT DEFAULT '',
        photo_key TEXT, photo_type TEXT, photo_status TEXT DEFAULT 'none', mail_status TEXT DEFAULT 'pending',
        status TEXT DEFAULT 'open', fixed_at INTEGER, created_at INTEGER NOT NULL
      )
    `);
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray(); }
  one(s, ...a) { return this.q(s, ...a)[0] || null; }

  takePlacesQuota(sid, kind, nowMs) {
    const allowedKind = kind === 'autocomplete' || kind === 'details' ? kind : '';
    if (!sid || !allowedKind) return { ok: false, retry: 'day' };
    const t = Number(nowMs) || Date.now();
    const { minute, day } = quotaBuckets(t, allowedKind);
    const countOf = (bucket) => {
      const r = this.one('SELECT count FROM places_quota WHERE shop_id=? AND bucket=?', sid, bucket);
      return r ? Number(r.count) || 0 : 0;
    };
    const allowed = quotaAllowed({ minute: countOf(minute), day: countOf(day) }, allowedKind);
    if (!allowed.ok) return { ok: false, retry: allowed.retry };
    const bump = (bucket) => {
      const cur = this.one('SELECT count FROM places_quota WHERE shop_id=? AND bucket=?', sid, bucket);
      if (cur) this.sql.exec('UPDATE places_quota SET count=count+1 WHERE shop_id=? AND bucket=?', sid, bucket);
      else this.sql.exec('INSERT INTO places_quota(shop_id, bucket, count) VALUES(?,?,1)', sid, bucket);
    };
    bump(minute);
    bump(day);
    const dayCut = new Date(t - 2 * 86400000).toISOString().slice(0, 10);
    this.sql.exec("DELETE FROM places_quota WHERE substr(bucket, instr(bucket, ':') + 1, 10) < ?", dayCut);
    return { ok: true };
  }

  shopRow(r, opts) {
    if (!r) return null;
    const row = {
      id: r.id, slug: r.slug, name: r.name, region_id: r.region_id,
      blurb: r.blurb || '', logo_url: r.logo_url || '', color: r.color || '',
      owner_email: r.owner_email || '', disabled: !!r.disabled, created_at: r.created_at,
      vehicle: shopVehicle(r.vehicle),
      return_by: r.return_by || '',
      range_mi: Number(r.range_mi) > 0 ? Number(r.range_mi) : 0,
      return_lat: Number.isFinite(r.return_lat) ? r.return_lat : null,
      return_lon: Number.isFinite(r.return_lon) ? r.return_lon : null,
      phone: r.phone || '',
      page_template_id: r.page_template_id || '',
    };
    if (opts && opts.rental) row.rental = rentalFromRow(r.rental_json);
    return row;
  }
  expRow(r) {
    if (!r) return null;
    let stops = [];
    try { stops = JSON.parse(r.stops_json || '[]'); } catch { stops = []; }
    return { id: r.id, shop_id: r.shop_id, title: r.title, description: r.description || '', stops, nearest_start: nearestStart(r.nearest_start), template_id: r.template_id || '', created_at: r.created_at, updated_at: r.updated_at };
  }
  placeRow(r) {
    if (!r) return null;
    return { id: r.id, shop_id: r.shop_id, name: r.name, category: r.category, lat: r.lat, lon: r.lon, note: r.note || '', link: r.link || '', template_id: r.template_id || '', created_at: r.created_at };
  }
  places(sid) { return this.q('SELECT * FROM places WHERE shop_id=? ORDER BY created_at', sid).map(r => this.placeRow(r)); }
  affRow(r) {
    if (!r) return null;
    return { id: r.id, shop_id: r.shop_id, name: r.name, lat: r.lat, lon: r.lon, offer: r.offer || '', coupon: r.coupon || '', template_id: r.template_id || '', created_at: r.created_at };
  }

  /** The unlock answer for a code row; withGrant adds a grant for a later app handoff. */
  unlockAnswer(sh, shop, c, withGrant) {
    const experiences = this.q(
      c.experience_id
        ? 'SELECT * FROM experiences WHERE id=? AND shop_id=?'
        : 'SELECT * FROM experiences WHERE shop_id=? ORDER BY created_at DESC',
      ...(c.experience_id ? [c.experience_id, sh.id] : [sh.id]),
    ).map(r => this.expRow(r));
    const affiliates = this.q('SELECT * FROM affiliates WHERE shop_id=? ORDER BY created_at DESC', sh.id).map(r => this.affRow(r));
    const out = {
      unlocked: true,
      shop: { ...shop, rental: rentalFromRow(sh.rental_json) },
      experiences, affiliates, places: this.places(sh.id), code: c.code,
    };
    if (withGrant) {
      out.grant = randomToken(24);
      this.sql.exec('INSERT INTO grants(grant,shop_id,code,expires_at) VALUES(?,?,?,?)', out.grant, sh.id, c.code, grantExpiry(now(), c.expires_at));
    }
    return out;
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
        if (body.vehicle != null && !SHOP_VEHICLES.includes(body.vehicle)) {
          return J({ error: 'vehicle must be one of ' + SHOP_VEHICLES.join(', ') }, 400);
        }
        const vehicle = body.vehicle != null ? body.vehicle : (sh.vehicle || '');
        let rental_json = sh.rental_json || '';
        if (body.rental != null) {
          const c = cleanRental(body.rental);
          if (c.error) return J({ error: c.error }, 400);
          rental_json = JSON.stringify(c.rental);
        }
        const retBy = cleanReturnBy(body.return_by !== undefined ? body.return_by : null);
        if (retBy.error) return J({ error: retBy.error }, 400);
        const range = cleanRangeMi(body.range_mi !== undefined ? body.range_mi : null);
        if (range.error) return J({ error: range.error }, 400);
        const spotSent = body.return_lat !== undefined || body.return_lon !== undefined;
        const spot = cleanReturnSpot(body.return_lat, body.return_lon, spotSent);
        if (spot.error) return J({ error: spot.error }, 400);
        const return_by = retBy.skip ? (sh.return_by || '') : retBy.value;
        const range_mi = range.skip ? (Number(sh.range_mi) || 0) : range.value;
        const return_lat = spot.skip ? sh.return_lat : spot.lat;
        const return_lon = spot.skip ? sh.return_lon : spot.lon;
        const ph = cleanPhone(body.phone !== undefined ? body.phone : null);
        if (ph.error) return J({ error: ph.error }, 400);
        const phone = ph.skip ? (sh.phone || '') : ph.value;
        this.sql.exec(
          'UPDATE shops SET name=?, region_id=?, blurb=?, logo_url=?, color=?, owner_email=?, disabled=?, vehicle=?, rental_json=?, return_by=?, range_mi=?, return_lat=?, return_lon=?, phone=? WHERE id=?',
          name, region_id, blurb, logo_url, color, owner_email, disabled, vehicle, rental_json, return_by, range_mi, return_lat, return_lon, phone, sid,
        );
        let pushed = 0;
        if (body.push_page && sh.page_template_id) {
          const fields = brandFields({ blurb, logo_url, color, vehicle });
          const allow = Array.isArray(body.push_shop_ids) ? body.push_shop_ids : null;
          for (const sib of this.q('SELECT id FROM shops WHERE page_template_id=? AND id<>?', sh.page_template_id, sid)) {
            if (allow && !allow.includes(sib.id)) continue;
            this.sql.exec('UPDATE shops SET blurb=?, logo_url=?, color=?, vehicle=? WHERE id=?', fields.blurb, fields.logo_url, fields.color, fields.vehicle, sib.id);
            pushed++;
          }
        }
        return J({ shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', sid), { rental: true }), pushed });
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
      if (path === '/shops-by-owner' && method === 'GET') {
        const email = (u.searchParams.get('email') || '').toLowerCase();
        const rows = email ? this.q('SELECT * FROM shops WHERE lower(owner_email)=? AND disabled=0 ORDER BY created_at', email) : [];
        return J({ shops: rows.map(r => this.shopRow(r)) });
      }
      if (path.startsWith('/shops/') && path.endsWith('/bundle') && method === 'GET') {
        const sid = path.split('/')[2];
        const sh = this.one('SELECT * FROM shops WHERE id=?', sid);
        if (!sh) return J({ error: 'not found' }, 404);
        return J({
          shop: this.shopRow(sh, { rental: true }),
          experiences: this.q('SELECT * FROM experiences WHERE shop_id=? ORDER BY created_at DESC', sid).map(r => this.expRow(r)),
          affiliates: this.q('SELECT * FROM affiliates WHERE shop_id=? ORDER BY created_at DESC', sid).map(r => this.affRow(r)),
          places: this.places(sid),
          codes: this.q('SELECT code,shop_id,experience_id,multi_use,max_uses,uses,expires_at,created_at FROM codes WHERE shop_id=? ORDER BY created_at DESC', sid),
        });
      }
      // Experiences
      if (path.match(/^\/shops\/[^/]+\/experiences$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        const title = String(body.title || '').trim();
        if (!title) return J({ error: 'Title required' }, 400);
        const stops = cleanStops(Array.isArray(body.stops) ? body.stops.map(withPark) : []);
        const eid = id();
        const t = now();
        this.sql.exec(
          'INSERT INTO experiences(id,shop_id,title,description,stops_json,nearest_start,template_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
          eid, sid, title, String(body.description || ''), JSON.stringify(stops), nearestStart(body.nearest_start) ? 1 : 0, body.template_id || null, t, t,
        );
        return J({ experience: this.expRow(this.one('SELECT * FROM experiences WHERE id=?', eid)) }, 201);
      }
      if (path.match(/^\/experiences\/[^/]+$/) && method === 'PATCH') {
        const eid = path.split('/')[2];
        const ex = this.one('SELECT * FROM experiences WHERE id=?', eid);
        if (!ex) return J({ error: 'not found' }, 404);
        const title = body.title != null ? String(body.title).trim() : ex.title;
        const description = body.description != null ? String(body.description) : ex.description;
        const stops = body.stops != null ? JSON.stringify(cleanStops(Array.isArray(body.stops) ? body.stops.map(withPark) : [])) : ex.stops_json;
        const ns = body.nearest_start != null ? (nearestStart(body.nearest_start) ? 1 : 0) : (nearestStart(ex.nearest_start) ? 1 : 0);
        this.sql.exec('UPDATE experiences SET title=?, description=?, stops_json=?, nearest_start=?, updated_at=? WHERE id=?', title, description, stops, ns, now(), eid);
        let pushed = 0;
        if (body.push && ex.template_id) {
          const saved = this.one('SELECT * FROM experiences WHERE id=?', eid);
          const srcShop = this.one('SELECT * FROM shops WHERE id=?', saved.shop_id);
          const allow = Array.isArray(body.push_shop_ids) ? body.push_shop_ids : null;
          let srcStops = [];
          try { srcStops = JSON.parse(saved.stops_json || '[]'); } catch { srcStops = []; }
          for (const sib of this.q('SELECT * FROM experiences WHERE template_id=? AND id<>?', ex.template_id, eid)) {
            if (allow && !allow.includes(sib.shop_id)) continue;
            const destShop = this.one('SELECT * FROM shops WHERE id=?', sib.shop_id);
            let destStops = [];
            try { destStops = JSON.parse(sib.stops_json || '[]'); } catch { destStops = []; }
            const next = pushStops(srcStops, destStops, sameTown(srcShop, destShop));
            this.sql.exec(
              'UPDATE experiences SET title=?, description=?, stops_json=?, nearest_start=?, updated_at=? WHERE id=?',
              saved.title, saved.description, JSON.stringify(next), saved.nearest_start, now(), sib.id,
            );
            pushed++;
          }
        }
        return J({ experience: this.expRow(this.one('SELECT * FROM experiences WHERE id=?', eid)), pushed });
      }
      if (path.match(/^\/(experiences|affiliates|places|bookings|reports)\/[^/]+\/owner$/) && method === 'GET') {
        const [, tbl, rid] = path.split('/');
        const table = { experiences: 'experiences', affiliates: 'affiliates', places: 'places', bookings: 'bookings', reports: 'reports' }[tbl];
        const r = this.one(`SELECT shop_id FROM ${table} WHERE id=?`, rid);
        return J({ shop_id: r ? r.shop_id : null });
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
      // Places of interest (no offer / coupon)
      if (path.match(/^\/shops\/[^/]+\/places$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        const c = cleanPlace(body);
        if (c.error) return J({ error: c.error }, 400);
        const p = c.place, pid = id();
        this.sql.exec('INSERT INTO places(id,shop_id,name,category,lat,lon,note,link,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
          pid, sid, p.name, p.category, p.lat, p.lon, p.note, p.link, now());
        return J({ place: this.placeRow(this.one('SELECT * FROM places WHERE id=?', pid)) }, 201);
      }
      if (path.match(/^\/places\/[^/]+$/) && method === 'PATCH') {
        const pid = path.split('/')[2];
        const cur = this.one('SELECT * FROM places WHERE id=?', pid);
        if (!cur) return J({ error: 'not found' }, 404);
        const c = cleanPlace(body, true);
        if (c.error) return J({ error: c.error }, 400);
        const p = { ...this.placeRow(cur), ...c.place };
        this.sql.exec('UPDATE places SET name=?, category=?, lat=?, lon=?, note=?, link=? WHERE id=?', p.name, p.category, p.lat, p.lon, p.note, p.link, pid);
        return J({ place: this.placeRow(this.one('SELECT * FROM places WHERE id=?', pid)) });
      }
      if (path.match(/^\/places\/[^/]+$/) && method === 'DELETE') {
        this.sql.exec('DELETE FROM places WHERE id=?', path.split('/')[2]);
        return J({ ok: true });
      }
      // Copy one experience, or the whole page, to another shop this partner owns.
      const copyEx = path.match(/^\/shops\/([^/]+)\/copy-experience$/);
      if (copyEx && method === 'POST') {
        const sid = copyEx[1];
        const srcShop = this.one('SELECT * FROM shops WHERE id=?', sid);
        const ex = this.one('SELECT * FROM experiences WHERE id=? AND shop_id=?', String(body.experience_id || ''), sid);
        const dest = this.one('SELECT * FROM shops WHERE id=? AND disabled=0', String(body.dest_shop_id || ''));
        if (!srcShop || !ex || !dest) return J({ error: 'not found' }, 404);
        if (dest.id === sid) return J({ error: 'Pick a different location' }, 400);
        const keep = sameTown(srcShop, dest);
        const sync = !!body.sync;
        const tid = sync ? (ex.template_id || randomToken(8)) : null;
        if (tid && !ex.template_id) this.sql.exec('UPDATE experiences SET template_id=? WHERE id=?', tid, ex.id);
        const payload = experiencePayload(this.expRow(this.one('SELECT * FROM experiences WHERE id=?', ex.id)), { keepPins: keep, templateId: tid });
        if (!payload.title) return J({ error: 'Title required' }, 400);
        const eid = id();
        const t = now();
        this.sql.exec(
          'INSERT INTO experiences(id,shop_id,title,description,stops_json,nearest_start,template_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
          eid, dest.id, payload.title, payload.description, JSON.stringify(payload.stops), payload.nearest_start ? 1 : 0, tid, t, t,
        );
        return J({ experience: this.expRow(this.one('SELECT * FROM experiences WHERE id=?', eid)), keep_pins: keep, synced: !!tid }, 201);
      }
      const copyPage = path.match(/^\/shops\/([^/]+)\/copy-page$/);
      if (copyPage && method === 'POST') {
        const sid = copyPage[1];
        const srcShop = this.one('SELECT * FROM shops WHERE id=?', sid);
        const dest = this.one('SELECT * FROM shops WHERE id=? AND disabled=0', String(body.dest_shop_id || ''));
        if (!srcShop || !dest) return J({ error: 'not found' }, 404);
        if (dest.id === sid) return J({ error: 'Pick a different location' }, 400);
        const keep = sameTown(srcShop, dest);
        const sync = !!body.sync;
        const pageId = sync ? (srcShop.page_template_id || randomToken(8)) : (dest.page_template_id || null);
        const brand = brandFields(this.shopRow(srcShop));
        if (sync && !srcShop.page_template_id) this.sql.exec('UPDATE shops SET page_template_id=? WHERE id=?', pageId, sid);
        this.sql.exec('UPDATE shops SET blurb=?, logo_url=?, color=?, vehicle=?, page_template_id=? WHERE id=?',
          brand.blurb, brand.logo_url, brand.color, brand.vehicle, sync ? pageId : dest.page_template_id, dest.id);
        const copied = { experiences: 0, affiliates: 0, places: 0 };
        for (const ex of this.q('SELECT * FROM experiences WHERE shop_id=? ORDER BY created_at', sid)) {
          const tid = sync ? (ex.template_id || randomToken(8)) : null;
          if (tid && !ex.template_id) this.sql.exec('UPDATE experiences SET template_id=? WHERE id=?', tid, ex.id);
          const payload = experiencePayload(this.expRow(this.one('SELECT * FROM experiences WHERE id=?', ex.id)), { keepPins: keep, templateId: tid });
          const eid = id();
          const t = now();
          this.sql.exec(
            'INSERT INTO experiences(id,shop_id,title,description,stops_json,nearest_start,template_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
            eid, dest.id, payload.title, payload.description, JSON.stringify(payload.stops), payload.nearest_start ? 1 : 0, tid, t, t,
          );
          copied.experiences++;
        }
        if (keep) {
          for (const af of this.q('SELECT * FROM affiliates WHERE shop_id=? ORDER BY created_at', sid)) {
            const tid = sync ? (af.template_id || randomToken(8)) : null;
            if (tid && !af.template_id) this.sql.exec('UPDATE affiliates SET template_id=? WHERE id=?', tid, af.id);
            const aid = id();
            this.sql.exec(
              'INSERT INTO affiliates(id,shop_id,name,lat,lon,offer,coupon,template_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
              aid, dest.id, af.name, af.lat, af.lon, af.offer || '', af.coupon || '', tid, now(),
            );
            copied.affiliates++;
          }
          for (const p of this.q('SELECT * FROM places WHERE shop_id=? ORDER BY created_at', sid)) {
            const tid = sync ? (p.template_id || randomToken(8)) : null;
            if (tid && !p.template_id) this.sql.exec('UPDATE places SET template_id=? WHERE id=?', tid, p.id);
            const pid = id();
            this.sql.exec(
              'INSERT INTO places(id,shop_id,name,category,lat,lon,note,link,template_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
              pid, dest.id, p.name, p.category, p.lat, p.lon, p.note || '', p.link || '', tid, now(),
            );
            copied.places++;
          }
        }
        return J({
          shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', dest.id)),
          keep_pins: keep, synced: sync, copied,
        }, 201);
      }
      if (path.match(/^\/shops\/[^/]+\/places-quota$/) && method === 'POST') {
        const sid = path.split('/')[2];
        return J(this.takePlacesQuota(sid, body && body.kind, body && body.now));
      }
      // Photos (bytes live in R2; this row is the lookup).
      if (path.match(/^\/shops\/[^/]+\/media-room$/) && method === 'GET') {
        const sid = path.split('/')[2];
        const n = this.one('SELECT COUNT(*) n FROM media WHERE shop_id=?', sid);
        const count = n ? n.n : 0;
        if (count >= MEDIA_MAX_COUNT) return J({ ok: false, error: 'This shop has ' + MEDIA_MAX_COUNT + ' photos. Remove one before adding another.' }, 400);
        return J({ ok: true, count });
      }
      if (path.match(/^\/shops\/[^/]+\/media$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        const n = this.one('SELECT COUNT(*) n FROM media WHERE shop_id=?', sid);
        if ((n ? n.n : 0) >= MEDIA_MAX_COUNT) return J({ error: 'This shop has ' + MEDIA_MAX_COUNT + ' photos. Remove one before adding another.' }, 400);
        this.sql.exec(
          'INSERT INTO media(id,shop_id,kind,r2_key,content_type,bytes,created_at) VALUES(?,?,?,?,?,?,?)',
          String(body.id || ''), sid, String(body.kind || ''), String(body.r2_key || ''), String(body.content_type || ''), +body.bytes || 0, now(),
        );
        return J({ ok: true }, 201);
      }
      if (path.match(/^\/media\/[^/]+$/) && method === 'GET') {
        const mid = path.split('/')[2];
        const row = this.one(
          'SELECT m.r2_key, m.content_type FROM media m JOIN shops s ON s.id = m.shop_id WHERE m.id=? AND s.disabled=0',
          mid,
        );
        if (!row) return J({ error: 'not found' }, 404);
        return J({ r2_key: row.r2_key, content_type: row.content_type });
      }
      // Codes
      if (path.match(/^\/shops\/[^/]+\/codes$/) && method === 'POST') {
        const sid = path.split('/')[2];
        if (!this.one('SELECT id FROM shops WHERE id=?', sid)) return J({ error: 'not found' }, 404);
        let code = String(body.code || '').trim().toUpperCase() || randomCode(4);
        if (this.one('SELECT code FROM codes WHERE code=?', code)) code = randomCode(5);
        const multi = body.multi_use === false ? 0 : 1;
        const max_uses = +body.max_uses || 0;
        const exp = codeExpiry(body, now());
        if (exp.error) return J({ error: exp.error }, 400);
        const expires_at = exp.expires_at;
        this.sql.exec(
          'INSERT INTO codes(code,shop_id,experience_id,multi_use,max_uses,uses,expires_at,created_at) VALUES(?,?,?,?,?,0,?,?)',
          code, sid, body.experience_id || null, multi, max_uses, expires_at, now(),
        );
        return J({ code: this.one('SELECT * FROM codes WHERE code=?', code) }, 201);
      }
      // Bookings: a renter's name, email, optional phone, and return time. The code is the shop's
      // pick, or a new multi-use code that lasts until a day after the return time.
      if (path.match(/^\/shops\/[^/]+\/bookings$/) && method === 'POST') {
        const sid = path.split('/')[2];
        const sh = this.one('SELECT * FROM shops WHERE id=?', sid);
        if (!sh) return J({ error: 'not found' }, 404);
        const c = cleanBooking(body, now());
        if (c.error) return J({ error: c.error }, 400);
        const bk = c.booking;
        let code = bk.code;
        if (code) {
          const row = this.one('SELECT * FROM codes WHERE code=? AND shop_id=?', code, sid);
          if (!row || (row.expires_at && row.expires_at < now())) return J({ error: 'That access code is not active' }, 400);
        } else {
          code = randomCode(4);
          while (this.one('SELECT code FROM codes WHERE code=?', code)) code = randomCode(5);
          this.sql.exec(
            'INSERT INTO codes(code,shop_id,experience_id,multi_use,max_uses,uses,expires_at,created_at) VALUES(?,?,NULL,1,0,0,?,?)',
            code, sid, bk.return_at + 86400, now(),
          );
        }
        const bid = id();
        this.sql.exec(
          'INSERT INTO bookings(id,shop_id,renter_name,email,phone,return_at,tz,code,welcome_status,sms_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
          bid, sid, bk.renter_name, bk.email, bk.phone, bk.return_at, bk.tz, code, 'pending', bk.phone ? 'pending' : 'none', now(),
        );
        this.sql.exec('DELETE FROM bookings WHERE return_at<?', now() - BOOKING_KEEP_DAYS * 86400);
        return J({ booking: bookingRow(this.one('SELECT * FROM bookings WHERE id=?', bid)), shop: this.shopRow(sh, { rental: true }) }, 201);
      }
      if (path.match(/^\/shops\/[^/]+\/bookings$/) && method === 'GET') {
        const sid = path.split('/')[2];
        const rows = this.q('SELECT * FROM bookings WHERE shop_id=? AND return_at>=? ORDER BY return_at', sid, now() - 2 * 86400);
        return J({ bookings: rows.map(bookingRow) });
      }
      if (path.match(/^\/bookings\/[^/]+$/) && method === 'GET') {
        const r = this.one('SELECT * FROM bookings WHERE id=?', path.split('/')[2]);
        if (!r) return J({ error: 'not found' }, 404);
        return J({ booking: bookingRow(r), shop: this.shopRow(this.one('SELECT * FROM shops WHERE id=?', r.shop_id), { rental: true }) });
      }
      if (path.match(/^\/bookings\/[^/]+\/status$/) && method === 'POST') {
        const bid = path.split('/')[2];
        const ok = ['sent', 'off', 'failed', 'pending', 'none'];
        const w = ok.includes(body.welcome) ? body.welcome : null;
        const t = ok.includes(body.sms) ? body.sms : null;
        if (w) this.sql.exec('UPDATE bookings SET welcome_status=?, welcome_at=? WHERE id=?', w, w === 'sent' ? now() : null, bid);
        if (t) this.sql.exec('UPDATE bookings SET sms_status=? WHERE id=?', t, bid);
        return J({ booking: bookingRow(this.one('SELECT * FROM bookings WHERE id=?', bid)) });
      }
      if (path.match(/^\/bookings\/[^/]+$/) && method === 'DELETE') {
        this.sql.exec('DELETE FROM bookings WHERE id=?', path.split('/')[2]);
        return J({ ok: true });
      }
      // Problem reports. The renter's code must be live for the shop; at most 5 a code a day.
      if (path.match(/^\/public\/[^/]+\/report-check$/) && method === 'POST') {
        const sh = this.one('SELECT * FROM shops WHERE slug=? AND disabled=0', normalizeSlug(path.split('/')[2]));
        if (!sh) return J({ error: 'not found' }, 404);
        const code = String((body && body.code) || '').replace(/\s+/g, '').toUpperCase();
        const c = code && this.one('SELECT * FROM codes WHERE code=? AND shop_id=?', code, sh.id);
        if (!c || (c.expires_at && c.expires_at < now())) return J({ error: 'Your access code is not active' }, 403);
        const n = this.one('SELECT COUNT(*) AS n FROM reports WHERE shop_id=? AND code=? AND created_at>?', sh.id, code, now() - 86400).n;
        if (n >= REPORTS_PER_CODE_DAY) return J({ error: 'This code has sent ' + REPORTS_PER_CODE_DAY + ' reports today. Call the shop.' }, 429);
        return J({ shop_id: sh.id, code, shop: this.shopRow(sh, { rental: true }) });
      }
      if (path.match(/^\/shops\/[^/]+\/reports$/) && method === 'POST') {
        const sid = path.split('/')[2];
        const r = body || {};
        const c = cleanReport(r);
        if (c.error) return J({ error: c.error }, 400);
        const rid = String(r.id || id());
        this.sql.exec(
          'INSERT INTO reports(id,shop_id,code,cart,kind,note,contact_name,contact_phone,photo_key,photo_type,photo_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
          rid, sid, String(r.code || ''), c.report.cart, c.report.kind, c.report.note, c.report.contact_name, c.report.contact_phone,
          r.photo_key || null, r.photo_type || null, ['saved', 'failed', 'off'].includes(r.photo_status) ? r.photo_status : 'none', now(),
        );
        this.sql.exec('DELETE FROM reports WHERE created_at<?', now() - REPORT_KEEP_DAYS * 86400);
        return J({ report: reportRow(this.one('SELECT * FROM reports WHERE id=?', rid)) }, 201);
      }
      if (path.match(/^\/shops\/[^/]+\/reports$/) && method === 'GET') {
        const rows = this.q('SELECT * FROM reports WHERE shop_id=? ORDER BY created_at DESC LIMIT 200', path.split('/')[2]);
        return J({ reports: rows.map(reportRow) });
      }
      if (path.match(/^\/reports\/[^/]+$/) && method === 'GET') {
        const r = this.one('SELECT * FROM reports WHERE id=?', path.split('/')[2]);
        if (!r) return J({ error: 'not found' }, 404);
        return J({ report: reportRow(r), photo_key: r.photo_key || '', photo_type: r.photo_type || '' });
      }
      if (path.match(/^\/reports\/[^/]+\/status$/) && method === 'POST') {
        const rid = path.split('/')[2];
        if (!this.one('SELECT id FROM reports WHERE id=?', rid)) return J({ error: 'not found' }, 404);
        if (body && ['sent', 'off', 'failed'].includes(body.mail)) this.sql.exec('UPDATE reports SET mail_status=? WHERE id=?', body.mail, rid);
        if (body && ['open', 'fixed'].includes(body.status)) {
          this.sql.exec('UPDATE reports SET status=?, fixed_at=? WHERE id=?', body.status, body.status === 'fixed' ? now() : null, rid);
        }
        return J({ report: reportRow(this.one('SELECT * FROM reports WHERE id=?', rid)) });
      }
      // App handoff: grant (from an unlock in the browser) -> single-use token, 10 minutes.
      const hm = path.match(/^\/public\/([^/]+)\/handoff$/);
      if (hm && method === 'POST') {
        const sh = this.one('SELECT * FROM shops WHERE slug=? AND disabled=0', normalizeSlug(hm[1]));
        const g = this.one('SELECT * FROM grants WHERE grant=?', String((body && body.grant) || ''));
        const why = handoffProblem(g, now(), { shopId: sh && sh.id });
        if (!sh || why) return J({ error: 'Handoff ' + (why || 'not found') }, 403);
        const token = randomToken(18), expires_at = now() + HANDOFF_TTL;
        this.sql.exec('INSERT INTO handoffs(token,shop_id,code,expires_at,used) VALUES(?,?,?,?,0)', token, sh.id, g.code, expires_at);
        this.sql.exec('DELETE FROM handoffs WHERE expires_at<?', now() - 86400);
        return J({ token, expires_at });
      }
      // Rental code typed in the app (Max t449u): no shop link, so find the shop from the code.
      // One code use, same checks and answer as /public/<slug>/unlock.
      if (path === '/public-code/unlock' && method === 'GET') {
        const code = String(u.searchParams.get('code') || '').replace(/\s+/g, '').toUpperCase();
        if (!code) return J({ error: 'code required' }, 400);
        const c = this.one('SELECT * FROM codes WHERE code=?', code);
        const sh = c && this.one('SELECT * FROM shops WHERE id=? AND disabled=0', c.shop_id);
        if (!c || !sh) return J({ error: 'Invalid access code' }, 403);
        const shop = this.shopRow(sh);
        if (c.expires_at && c.expires_at < now()) return J({ error: 'Code expired', shop }, 403);
        if (!c.multi_use && c.uses > 0) return J({ error: 'Code already used', shop }, 403);
        if (c.max_uses > 0 && c.uses >= c.max_uses) return J({ error: 'Code use limit reached', shop }, 403);
        this.sql.exec('UPDATE codes SET uses=uses+1 WHERE code=?', code);
        return J({ ...this.unlockAnswer(sh, shop, c, true), slug: sh.slug });
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
          return J(this.unlockAnswer(sh, shop, c, true));
        }
        if (parts[1] === 'redeem') {
          // App handoff: same answer as unlock, no code use counted; the token works once.
          const t = String(u.searchParams.get('token') || '');
          const h = this.one('SELECT * FROM handoffs WHERE token=?', t);
          const why = handoffProblem(h, now(), { shopId: sh.id, single: true });
          if (why) return J({ error: 'Handoff ' + why, shop }, 403);
          this.sql.exec('UPDATE handoffs SET used=1 WHERE token=?', t);
          const c = this.one('SELECT * FROM codes WHERE code=? AND shop_id=?', h.code, sh.id);
          if (!c || (c.expires_at && c.expires_at < now())) return J({ error: 'Code expired', shop }, 403);
          return J(this.unlockAnswer(sh, shop, c, true));
        }
        // Teaser (no paid content). Rental phone and rules stay off this response.
        const teaserShop = { ...shop };
        delete teaserShop.rental;
        return J({
          shop: teaserShop,
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

    async function ownedShops(sess) {
      if (!sess || supers(env).has(sess.email)) return [];
      const r = await (await doFetch('/shops-by-owner?email=' + encodeURIComponent(sess.email))).json();
      return r.shops || [];
    }

    // Owner endpoints. A super-admin may act on any shop by passing ?shop_id= (or body.shop_id);
    // an owner only on their own shop, and only on experiences/affiliates that belong to it.
    async function access(body, resource) {
      if (!sess) return { status: 401, error: 'unauthorized' };
      const owned = isSuper ? [] : await ownedShops(sess);
      const own = owned[0] || null;
      let resourceShopId;
      if (resource) {
        const r = await (await doFetch('/' + resource + '/owner')).json();
        resourceShopId = r.shop_id || null;
      }
      const a = shopAccess({
        isSuper, ownShopId: own && own.id, ownedShopIds: owned.map(s => s.id), resourceShopId,
        requestedShopId: u.searchParams.get('shop_id') || (body && body.shop_id) || '',
      });
      if (a.shopId && isSuper && req.method !== 'GET') {
        // Audit trail (Workers logs): which super-admin edited which shop.
        console.log(JSON.stringify({ audit: 'super_edit', email: sess.email, shop_id: a.shopId, method: req.method, path: u.pathname }));
      }
      return Object.assign(a, { owned });
    }
    function withPush(body, a) {
      const b = body && typeof body === 'object' ? { ...body } : {};
      delete b.push_shop_ids;
      delete b.shop_id;
      if (b.push || b.push_page) b.push_shop_ids = isSuper ? null : (a.owned || []).map(s => s.id);
      return b;
    }
    const deny = a => J({ error: a.error }, a.status);
    const readBody = async () => { try { return await req.json(); } catch { return {}; } };
    const send = (path, method, body) => doFetch(path, { method, headers: { 'content-type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });

    if ((u.pathname === '/places/autocomplete' || u.pathname === '/places/details') && req.method === 'POST') {
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      const kind = u.pathname.endsWith('/details') ? 'details' : 'autocomplete';
      const result = await handlePlacesRequest({
        kind,
        body,
        env,
        shopId: a.shopId,
        quota: async (shopId, qKind, nowMs) => {
          const res = await send('/shops/' + shopId + '/places-quota', 'POST', { kind: qKind, now: nowMs });
          try { return await res.json(); } catch { return { ok: false, retry: 'day' }; }
        },
      });
      return J(result.body, result.status);
    }

    if (u.pathname === '/shop/media' && req.method === 'POST') {
      if (!env.MEDIA) return J({ error: 'Photo storage is not configured' }, 503);
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      const decoded = bytesFromB64(body.data_base64);
      if (decoded.error) return J({ error: decoded.error }, 400);
      const roomRes = await doFetch('/shops/' + a.shopId + '/media-room');
      const room = await roomRes.json();
      if (!roomRes.ok) return J({ error: room.error || 'Too many photos' }, roomRes.status);
      const mid = randomToken(16);
      let stored;
      try {
        stored = await storeImage({
          bytes: decoded.bytes, shopId: a.shopId, kind: body.kind, id: mid,
          put: (key, bytes, type) => env.MEDIA.put(key, bytes, { httpMetadata: { contentType: type } }),
        });
      } catch (e) {
        return J({ error: 'Could not store that image' }, 502);
      }
      if (stored.status !== 201) return J({ error: stored.error }, stored.status);
      const ins = await send('/shops/' + a.shopId + '/media', 'POST', stored.row);
      if (!ins.ok) return ins;
      const origin = originOf(req, env);
      return J({ id: mid, url: origin + '/api/partner/media/' + mid, content_type: stored.row.content_type, bytes: stored.row.bytes }, 201);
    }
    if (u.pathname === '/shop' && req.method === 'GET') {
      const a = await access(null);
      if (!a.shopId) return deny(a);
      return doFetch('/shops/' + a.shopId + '/bundle');
    }
    if (u.pathname === '/shop/stats' && req.method === 'GET') {
      const a = await access(null);
      if (!a.shopId) return deny(a);
      const bundle = await (await doFetch('/shops/' + a.shopId + '/bundle')).json();
      const slug = bundle.shop && bundle.shop.slug;
      if (!slug) return J({ error: 'not found' }, 404);
      const days = u.searchParams.get('days') || '30';
      return J(await fetchShopStats(globalThis.fetch.bind(globalThis), {
        base: env.ANALYTICS_STATS_URL, key: env.ANALYTICS_STATS_KEY, shop: slug, days,
      }));
    }
    if (u.pathname === '/shop' && req.method === 'PATCH') {
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      // Shop admins may not disable or reassign owner
      if (!isSuper) {
        delete body.disabled;
        delete body.owner_email;
        delete body.slug;
      }
      return send('/shops/' + a.shopId, 'PATCH', withPush(body, a));
    }
    if (u.pathname === '/shop/locations' && req.method === 'GET') {
      const a = await access(null);
      if (!a.shopId) return deny(a);
      const bundle = await (await doFetch('/shops/' + a.shopId + '/bundle')).json();
      const email = (bundle.shop && bundle.shop.owner_email) || '';
      const listed = email
        ? (await (await doFetch('/shops-by-owner?email=' + encodeURIComponent(email))).json()).shops || []
        : [];
      const locations = listed.filter(s => s.id !== a.shopId).map(s => ({ id: s.id, name: s.name, slug: s.slug, region_id: s.region_id }));
      return J({ locations });
    }
    if ((u.pathname === '/shop/copy-experience' || u.pathname === '/shop/copy-page') && req.method === 'POST') {
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      const dest = String(body.dest_shop_id || '');
      if (!isSuper && !(a.owned || []).some(s => s.id === dest)) return J({ error: 'forbidden' }, 403);
      const kind = u.pathname === '/shop/copy-page' ? 'copy-page' : 'copy-experience';
      return send('/shops/' + a.shopId + '/' + kind, 'POST', { experience_id: body.experience_id, dest_shop_id: dest, sync: !!body.sync });
    }
    // ---- Rental-day welcome (bookings) ----
    async function siteData() {
      const o = originOf(req, env);
      const get = async p => { try { const r = await fetch(o + p); return r.ok ? await r.json() : null; } catch { return null; } };
      const [regionsJson, rulesJson] = await Promise.all([get('/data/regions.json'), get('/data/rules.json')]);
      return { regions: Array.isArray(regionsJson) ? regionsJson : [], rules: rulesJson };
    }
    async function welcomeFor(shop, booking) {
      const { regions, rules } = await siteData();
      const region = regions.find(r => r.id === shop.region_id) || null;
      const link = originOf(req, env) + '/p/' + encodeURIComponent(shop.slug) + '/go?code=' + encodeURIComponent(booking.code);
      const lines = rulesLines({ rules, region, vehicle: shop.vehicle, shopRules: shop.rental && shop.rental.rules });
      return { link, email: welcomeEmail({ shop, booking, link, rules: lines }), sms: welcomeSms({ shop, booking, link }) };
    }
    async function deliver(shop, booking) {
      const w = await welcomeFor(shop, booking);
      const mail = await sendMail(env, { to: booking.email, subject: w.email.subject, html: w.email.html, text: w.email.text, reply_to: shop.owner_email });
      const sms = booking.phone ? await sendSms(env, { to: booking.phone, text: w.sms }) : { status: 'none' };
      const res = await send('/bookings/' + booking.id + '/status', 'POST', { welcome: mail.status, sms: sms.status });
      const j = await res.json();
      return { booking: j.booking, mail, sms: { status: sms.status, reason: sms.reason }, link: w.link };
    }
    if (u.pathname === '/shop/bookings' && req.method === 'GET') {
      const a = await access(null);
      if (!a.shopId) return deny(a);
      const r = await (await doFetch('/shops/' + a.shopId + '/bookings')).json();
      const sms = smsProvider(env);
      return J({ ...r, mail: mailState(env), sms: { on: sms.enabled, reason: sms.reason || '' } });
    }
    if (u.pathname === '/shop/bookings/preview' && req.method === 'POST') {
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      const c = cleanBooking(body, now());
      if (c.error) return J({ error: c.error }, 400);
      const bundle = await (await doFetch('/shops/' + a.shopId + '/bundle')).json();
      const w = await welcomeFor(bundle.shop, { ...c.booking, code: c.booking.code || 'YOURCODE' });
      return J({ ...w.email, sms: w.sms, mail: mailState(env) });
    }
    if (u.pathname === '/shop/bookings' && req.method === 'POST') {
      const body = await readBody();
      const a = await access(body);
      if (!a.shopId) return deny(a);
      const made = await send('/shops/' + a.shopId + '/bookings', 'POST', body);
      const j = await made.json();
      if (!made.ok) return J(j, made.status);
      return J(await deliver(j.shop, j.booking), 201);
    }
    const bk = u.pathname.match(/^\/shop\/bookings\/([^/]+)(\/resend)?$/);
    if (bk && ((bk[2] && req.method === 'POST') || (!bk[2] && req.method === 'DELETE'))) {
      const a = await access(null, 'bookings/' + bk[1]);
      if (!a.shopId) return deny(a);
      if (!bk[2]) return send('/bookings/' + bk[1], 'DELETE');
      const j = await (await doFetch('/bookings/' + bk[1])).json();
      if (!j.booking) return J({ error: 'not found' }, 404);
      return J(await deliver(j.shop, j.booking));
    }
    for (const kind of ['experiences', 'affiliates', 'places', 'codes']) {
      if (u.pathname === '/shop/' + kind && req.method === 'POST') {
        const body = await readBody();
        const a = await access(body);
        if (!a.shopId) return deny(a);
        return send('/shops/' + a.shopId + '/' + kind, 'POST', body);
      }
    }
    const rm = u.pathname.match(/^\/shop\/(experiences|affiliates|places)\/([^/]+)$/);
    if (rm && (req.method === 'PATCH' || req.method === 'DELETE')) {
      const body = req.method === 'PATCH' ? await readBody() : undefined;
      const a = await access(body, rm[1] + '/' + rm[2]);
      if (!a.shopId) return deny(a);
      const payload = req.method === 'PATCH' && rm[1] === 'experiences' ? withPush(body, a) : body;
      return send('/' + rm[1] + '/' + rm[2], req.method, payload);
    }

    // ---- Problem reports ----
    if (u.pathname === '/shop/reports' && req.method === 'GET') {
      const a = await access(null);
      if (!a.shopId) return deny(a);
      const r = await (await doFetch('/shops/' + a.shopId + '/reports')).json();
      return J({ ...r, photos: !!env.MEDIA, mail: mailState(env) });
    }
    const rp = u.pathname.match(/^\/shop\/reports\/([^/]+)\/(fixed|photo)$/);
    if (rp) {
      const a = await access(null, 'reports/' + rp[1]);
      if (!a.shopId) return deny(a);
      if (rp[2] === 'fixed' && req.method === 'POST') {
        const body = await readBody();
        return send('/reports/' + rp[1] + '/status', 'POST', { status: body.fixed === false ? 'open' : 'fixed' });
      }
      if (rp[2] === 'photo' && req.method === 'GET') {
        if (!env.MEDIA) return J({ error: 'Photo storage is not configured' }, 503);
        const j = await (await doFetch('/reports/' + rp[1])).json();
        if (!j.photo_key) return J({ error: 'not found' }, 404);
        const obj = await env.MEDIA.get(j.photo_key);
        if (!obj) return J({ error: 'not found' }, 404);
        return new Response(obj.body, { headers: { 'content-type': j.photo_type || 'application/octet-stream', 'cache-control': 'private, max-age=3600', 'x-content-type-options': 'nosniff' } });
      }
    }
    const pr = u.pathname.match(/^\/public\/([^/]+)\/(report|report-info)$/);
    if (pr && pr[2] === 'report-info' && req.method === 'GET') {
      return J({ photos: !!env.MEDIA, kinds: REPORT_KINDS });
    }
    if (pr && pr[2] === 'report' && req.method === 'POST') {
      // A renter with a live code reports a problem. Works without photos (no R2 binding).
      const body = await readBody();
      const c = cleanReport(body);
      if (c.error) return J({ error: c.error }, 400);
      const chk = await send('/public/' + encodeURIComponent(pr[1]) + '/report-check', 'POST', { code: body.code });
      const ck = await chk.json();
      if (!chk.ok) return J({ error: ck.error }, chk.status);
      const rid = randomToken(12);
      let photo = { photo_status: 'none' };
      if (body.photo_base64) {
        if (!env.MEDIA) photo = { photo_status: 'off' };
        else {
          const dec = bytesFromB64(body.photo_base64);
          const k = dec.error ? dec : reportPhotoKey(ck.shop_id, rid, dec.bytes);
          if (k.error) return J({ error: k.error }, 400);
          try {
            await env.MEDIA.put(k.key, dec.bytes, { httpMetadata: { contentType: k.content_type } });
            photo = { photo_status: 'saved', photo_key: k.key, photo_type: k.content_type };
          } catch (e) { photo = { photo_status: 'failed' }; }
        }
      }
      const made = await send('/shops/' + ck.shop_id + '/reports', 'POST', { ...c.report, id: rid, code: ck.code, ...photo });
      const j = await made.json();
      if (!made.ok) return J(j, made.status);
      const shop = ck.shop;
      const tz = validZone(body.tz) || 'America/Los_Angeles';
      let when = '';
      try { when = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', minute: '2-digit', weekday: 'short', month: 'short', day: 'numeric', timeZoneName: 'short' }).format(new Date()); } catch {}
      const m = reportEmail({ shop, report: { ...c.report, code: ck.code }, adminLink: originOf(req, env) + '/partner', photo: photo.photo_status === 'saved' ? 'saved' : photo.photo_status === 'failed' ? 'failed' : 'none', when });
      const mail = shop.owner_email ? await sendMail(env, { to: shop.owner_email, subject: m.subject, html: m.html, text: m.text }) : { status: 'failed' };
      await send('/reports/' + rid + '/status', 'POST', { mail: mail.status });
      return J({ ok: true, report: { id: rid, cart: c.report.cart, kind: c.report.kind }, photo: photo.photo_status, shop_phone: (shop.rental && shop.rental.phone) || shop.phone || '' }, 201);
    }

    // Public (no auth)
    if (u.pathname === '/public-code/unlock') return doFetch(u.pathname + u.search, { method: 'GET' });
    if (req.method === 'GET' && /^\/media\/[a-f0-9]{16,64}$/.test(u.pathname)) {
      if (!env.MEDIA) return J({ error: 'Photo storage is not configured' }, 503);
      const metaRes = await doFetch(u.pathname);
      const meta = await metaRes.json();
      if (!metaRes.ok || !meta.r2_key) return J({ error: 'not found' }, 404);
      const obj = await env.MEDIA.get(meta.r2_key);
      if (!obj) return J({ error: 'not found' }, 404);
      return new Response(obj.body, {
        headers: {
          'content-type': meta.content_type || 'application/octet-stream',
          'cache-control': 'public, max-age=86400',
          'x-content-type-options': 'nosniff',
          'access-control-allow-origin': '*',
        },
      });
    }
    if (u.pathname.startsWith('/public/')) {
      if (req.method === 'POST' && /^\/public\/[^/]+\/handoff$/.test(u.pathname)) {
        return doFetch(u.pathname, { method: 'POST', headers: { 'content-type': 'application/json' }, body: await req.text() });
      }
      return doFetch(u.pathname + u.search, { method: 'GET' });
    }

    return J({ error: 'not found', path: u.pathname }, 404);
  },
};
