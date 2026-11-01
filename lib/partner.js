// Partner portal helpers (slug rules, access codes). Used by the Worker and by Node tests.
// Brand pages live at /p/<slug> so they never collide with city SEO pages at /<cityslug>.

export const SYSTEM_SLUGS = new Set([
  'map', 'p', 'partner', 'admin', 'api', 'privacy', 'compare', 'llms', 'robots',
  'lsv', 'golf-cart-maps',
  'sitemap', 'sw', 'vendor', 'data', 'assets', 'static', 'login', 'logout',
  'auth', 'go', 'x', 'app', 'ios', 'android', 'download', 'checkout', 'pay',
]);

export const SLUG_RE = /^[a-z][a-z0-9-]{1,47}$/;

export function normalizeSlug(s) {
  return String(s || '').trim().toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 48);
}

/** regionSlugs: Set or array of city slugs from regions.json */
export function assertShopSlug(raw, regionSlugs) {
  const slug = normalizeSlug(raw);
  if (!SLUG_RE.test(slug)) return { ok: false, error: 'Slug must be 2–48 chars: start with a letter, then letters, digits, or hyphens.' };
  if (SYSTEM_SLUGS.has(slug)) return { ok: false, error: `Slug "${slug}" is reserved.` };
  const regions = regionSlugs instanceof Set ? regionSlugs : new Set(regionSlugs || []);
  if (regions.has(slug)) return { ok: false, error: `Slug "${slug}" is a city page. Pick another.` };
  return { ok: true, slug };
}

export function randomCode(bytes = 4) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  // Crockford-ish base32 without I/L/O/U — easy to read aloud at the rental desk.
  const abc = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  let n = 0n;
  for (const b of a) n = (n << 8n) | BigInt(b);
  let out = '';
  for (let i = 0; i < Math.ceil(bytes * 8 / 5); i++) {
    out = abc[Number(n & 31n)] + out;
    n >>= 5n;
  }
  return out;
}

export function randomToken(bytes = 18) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return [...a].map(b => b.toString(16).padStart(2, '0')).join('');
}

export function couponCode(prefix = 'GCM') {
  return `${prefix}-${randomCode(3)}`;
}

/**
 * Who may act on a shop's owner endpoints (/shop/*). Pure, so tests cover every branch.
 * isSuper: super-admin session. ownShopId: shop the session owns (owners). requestedShopId: ?shop_id= / body.shop_id.
 * resourceShopId: shop that owns the experience/affiliate being edited (undefined for shop-level routes).
 * Returns { shopId } or { status, error }.
 */
export function shopAccess({ isSuper, ownShopId, requestedShopId, resourceShopId }) {
  if (resourceShopId === null) return { status: 404, error: 'not found' };
  if (isSuper) {
    const sid = requestedShopId || resourceShopId;
    if (!sid) return { status: 400, error: 'shop_id required for super-admin' };
    if (resourceShopId && resourceShopId !== sid) return { status: 403, error: 'forbidden' };
    return { shopId: sid };
  }
  if (!ownShopId) return { status: 404, error: 'no shop' };
  if (requestedShopId && requestedShopId !== ownShopId) return { status: 403, error: 'forbidden' };
  if (resourceShopId && resourceShopId !== ownShopId) return { status: 403, error: 'forbidden' };
  return { shopId: ownShopId };
}

/**
 * Access-code expiry from a POST body. expires_days: 1..30 (whole days) or null / 'never' = never expires.
 * Missing expires_days keeps the old default (30 days) unless expires_at was sent.
 * Returns { expires_at } (unix seconds or null) or { error }.
 */
export const CODE_MAX_DAYS = 30;
export function codeExpiry(body, nowSec) {
  const d = body ? body.expires_days : undefined;
  if (d === undefined) return { expires_at: body && body.expires_at ? +body.expires_at : nowSec + CODE_MAX_DAYS * 86400 };
  if (d === null || d === 'never') return { expires_at: null };
  const n = Number(d);
  if (!Number.isInteger(n) || n < 1 || n > CODE_MAX_DAYS) return { error: `expires_days must be 1-${CODE_MAX_DAYS} or null (never expires)` };
  return { expires_at: nowSec + n * 86400 };
}

/** Places of interest a shop pins for renters. Not affiliates: no offer, no coupon. */
export const PLACE_CATEGORIES = ['restaurant', 'views', 'trivia', 'fun_fact', 'other'];
export const PLACE_LABEL = { restaurant: 'Restaurant', views: 'Views', trivia: 'Trivia', fun_fact: 'Fun fact', other: 'Other' };
export const PLACE_ICON = { restaurant: '🍽️', views: '🌅', trivia: '❓', fun_fact: '💡', other: '📍' };

/**
 * Validate a place body. partial=true (PATCH) only checks the fields sent.
 * Returns { place: {name, category, lat, lon, note, link} (only sent fields when partial) } or { error }.
 */
export function cleanPlace(body, partial = false) {
  const b = body || {};
  const out = {};
  if (!partial || b.name != null) {
    const name = String(b.name ?? '').trim();
    if (!name) return { error: 'Name required' };
    out.name = name.slice(0, 120);
  }
  if (!partial || b.category != null) {
    if (!PLACE_CATEGORIES.includes(b.category)) return { error: 'category must be one of ' + PLACE_CATEGORIES.join(', ') };
    out.category = b.category;
  }
  for (const k of ['lat', 'lon']) {
    if (!partial || b[k] != null) {
      const v = Number(b[k]);
      if (b[k] === '' || b[k] == null || !Number.isFinite(v) || Math.abs(v) > (k === 'lat' ? 90 : 180)) return { error: 'Pick a place (lat/lon required)' };
      out[k] = v;
    }
  }
  if (!partial || b.note != null) out.note = String(b.note ?? '').slice(0, 1000);
  if (!partial || b.link != null) {
    const link = String(b.link ?? '').trim();
    if (link && !/^https:\/\/[^\s<>"']+$/i.test(link)) return { error: 'Link must start with https://' };
    out.link = link;
  }
  return { place: out };
}

// Rental vehicle per shop. Unset rows read as golf_cart: the stricter rule, and
// what /p/<slug> showed before this field existed (a road never turns green by default).
export const SHOP_VEHICLES = ['golf_cart', 'lsv'];
export function shopVehicle(v) { return SHOP_VEHICLES.includes(v) ? v : 'golf_cart'; }

// Per-experience "Start riders at their nearest stop". Missing or junk reads as on (Max, Oct 31 2026, t441u).
export function nearestStart(v) { return !(v === false || v === 0 || v === '0' || v === 'false'); }
