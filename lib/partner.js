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

// Rental vehicle per shop. Unset rows read as golf_cart: the stricter rule, and
// what /p/<slug> showed before this field existed (a road never turns green by default).
export const SHOP_VEHICLES = ['golf_cart', 'lsv'];
export function shopVehicle(v) { return SHOP_VEHICLES.includes(v) ? v : 'golf_cart'; }
