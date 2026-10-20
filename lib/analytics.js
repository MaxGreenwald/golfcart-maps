// Golf Cart Map analytics: one shared, privacy-first event schema (used by the Pages Function
// /api/e, the gcm-analytics Worker and the tests). Anything not on these allowlists is dropped.
// Never stored: IP address, user agent, cookies, names, emails, phone numbers, free text,
// coordinates. Location is town level only (the region id the user is looking at).
export const EVENTS = {
  session:          ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref', 'landing', 'ft_source', 'ft_medium', 'ft_campaign', 'new_install'],
  town_viewed:      ['how'],
  route_searched:   ['ok', 'risky', 'mi', 'reason'],
  route_started:    [],
  route_completed:  ['mi'],
  road_report_filed:['issue'],
  range_set:        ['profile', 'full'],
  stop_added:       ['n'],
};
export const PLATFORMS = ['web', 'ios', 'android', 'carplay'];
const TOKEN = /^[a-z0-9][a-z0-9._-]{0,39}$/;          // utm values, region ids, enums
const HOST = /^[a-z0-9.-]{1,80}$/;                    // referrer host only, never a path
const ID = /^[A-Za-z0-9-]{8,40}$/;                    // random install / session ids
const ENUMS = {
  how: ['picker', 'auto', 'link', 'restore', 'carplay', 'default'],
  reason: ['no_legal_route', 'no_road_nearby', 'other'],
  profile: ['custom', 'd5_42'],
  issue: ['wrong_speed', 'allow', 'block', 'closed', 'other'],
};
function cleanToken(v) { if (typeof v !== 'string') return null; v = v.trim().toLowerCase().replace(/\s+/g, '_').slice(0, 40); return TOKEN.test(v) ? v : null }
function cleanProp(k, v) {
  if (k === 'ok' || k === 'risky' || k === 'new_install' || k === 'full') return typeof v === 'boolean' ? v : null;
  if (k === 'n') { const n = +v; return Number.isInteger(n) && n >= 0 && n <= 10 ? n : null }
  if (k === 'mi') { const n = +v; return Number.isFinite(n) && n >= 0 && n < 500 ? Math.round(n * 2) / 2 : null }   // 0.5 mi buckets
  if (k === 'ref') { if (typeof v !== 'string') return null; v = v.toLowerCase().replace(/^www\./, ''); return HOST.test(v) ? v : null }
  if (k === 'landing') { const t = cleanToken(typeof v === 'string' ? v.replace(/^\//, '') || 'home' : null); return t }
  if (ENUMS[k]) return ENUMS[k].includes(v) ? v : null;
  return cleanToken(v);
}
/** Returns a clean event row, or null if the event is not allowed. */
export function sanitize(b) {
  if (!b || typeof b !== 'object' || !Object.prototype.hasOwnProperty.call(EVENTS, b.e)) return null;
  const keys = EVENTS[b.e], p = {};
  const src = b.p && typeof b.p === 'object' && !Array.isArray(b.p) ? b.p : {};
  for (const k of keys) if (k in src) { const v = cleanProp(k, src[k]); if (v !== null && v !== undefined) p[k] = v }
  return {
    event: b.e,
    town: cleanToken(b.t),
    platform: PLATFORMS.includes(b.pl) ? b.pl : 'web',
    pwa: b.pwa === true ? 1 : 0,
    iid: typeof b.i === 'string' && ID.test(b.i) ? b.i : null,
    sid: typeof b.s === 'string' && ID.test(b.s) ? b.s : null,
    props: p,
  };
}
