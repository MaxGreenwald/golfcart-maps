// Who is left out of published Golf Cart Maps numbers (WAI, route users, and the other
// scorecard counts). Applied when /stats is read, so it covers events already stored.
// Three durable signals, any one of them drops the whole install id:
//   1. EXCLUDE_IIDS — anonymous gcm-iid values (Max's own browsers/phones, known test installs).
//   2. props.internal — sim / tf / e2e / ci / test / playwright / internal / debug / notrack.
//      The client sets this for simulator builds, internal TestFlight, webdriver, and test UTMs,
//      and does not send those events. If one still arrives, /stats ignores that install.
//   3. UTM / first-touch tokens that are e2e, test, ci, playwright, simulator, and the same family.
// A single tagged event excludes that install's other events too (a CI run that also sent a clean session).
//
// Add a device: on it, read localStorage key gcm-iid (same key in the iOS app) and append it below.
// These are random ids, not names or accounts.

export const EXCLUDE_IIDS = [
];

// Values stored on props.internal. Aliases (simulator, testflight, no_track) normalize to these.
export const INTERNAL_CHANNELS = ['sim', 'tf', 'e2e', 'ci', 'test', 'playwright', 'internal', 'debug', 'notrack'];
const INTERNAL_ALIAS = { simulator: 'sim', testflight: 'tf', no_track: 'notrack' };

// Whole utm/first-touch tokens. `test` is exact so a real word like "testimonial" still counts.
const UTM_EXACT = ['e2e', 'test', 'ci', 'playwright', 'simulator', 'internal', 'debug', 'notrack', 'no_track', 'testflight', 'tf', 'sim'];
// [prefix, require a delimiter after it]. Without a delimiter, "test" must not swallow "testing".
const UTM_PREFIXES = [
  ['e2e', true], ['ci', true], ['test', true],
  ['playwright', false], ['simulator', false], ['notrack', false], ['testflight', false],
];
const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ft_source', 'ft_medium', 'ft_campaign'];

export function cleanInternal(v) {
  if (typeof v !== 'string') return null;
  v = v.trim().toLowerCase();
  if (!v || v.indexOf('__') !== -1) return null;   // build placeholder __GCM_ANALYTICS_INTERNAL__
  v = INTERNAL_ALIAS[v] || v;
  return INTERNAL_CHANNELS.includes(v) ? v : null;
}

export function utmIsExcluded(v) {
  if (typeof v !== 'string') return false;
  const s = v.trim().toLowerCase();
  if (!s) return false;
  if (UTM_EXACT.includes(s)) return true;
  for (const [p, boundary] of UTM_PREFIXES) {
    if (!s.startsWith(p)) continue;
    if (!boundary) return true;
    if (s.length > p.length && '-_.'.includes(s[p.length])) return true;
  }
  return false;
}

/** Why this client must not be counted, or null. `search` is a URLSearchParams-like object or a plain map. */
export function internalChannel({ gcmInternal, stored, build, webdriver, search } = {}) {
  const marked = cleanInternal(gcmInternal) || cleanInternal(stored) || cleanInternal(build);
  if (marked) return marked;
  if (webdriver === true) return 'e2e';
  if (search && typeof search === 'object') {
    for (const k of UTM_KEYS) if (utmIsExcluded(search[k])) return 'e2e';
  }
  return null;
}

function sqlLit(s) {
  if (!/^[a-z0-9._-]+$/.test(s)) throw new Error('bad sql literal');
  return `'${s}'`;
}
function likePrefix(body) {
  return `'${body.replace(/[\\%_]/g, ch => '\\' + ch)}%'`;
}

/** SQL boolean (props JSON of one events row). Keep in lockstep with utmIsExcluded / cleanInternal. */
export function rowIsInternalSql(props = 'props') {
  const col = k => `lower(COALESCE(json_extract(${props},'$.${k}'),''))`;
  const parts = [`${col('internal')} IN (${INTERNAL_CHANNELS.map(sqlLit).join(',')})`];
  const exact = [...new Set([...UTM_EXACT, ...INTERNAL_CHANNELS])];
  const exactSql = exact.map(sqlLit).join(',');
  for (const k of UTM_KEYS) {
    const c = col(k);
    parts.push(`${c} IN (${exactSql})`);
    for (const [p, boundary] of UTM_PREFIXES) {
      if (boundary) for (const d of ['-', '_', '.']) parts.push(`${c} LIKE ${likePrefix(p + d)} ESCAPE '\\'`);
      else parts.push(`${c} LIKE ${likePrefix(p)} ESCAPE '\\'`);
    }
  }
  return `(${parts.join(' OR ')})`;
}

const ID = /^[A-Za-z0-9-]{8,40}$/;
export function denylistJson(extra) {
  const ids = [];
  for (const id of [...EXCLUDE_IIDS, ...(extra || [])]) if (typeof id === 'string' && ID.test(id) && !ids.includes(id)) ids.push(id);
  return JSON.stringify(ids);
}
