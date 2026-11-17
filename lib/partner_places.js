// Google Places API (New) proxy helpers for the partner Worker.
// The API key stays on the server (env.GOOGLE_PLACES_API_KEY). The browser never sees it.
// Autocomplete and Place Details use a session token and a minimal Essentials field mask.

export const PLACES_AUTOCOMPLETE_URL = 'https://places.googleapis.com/v1/places:autocomplete';
export const PLACES_DETAILS_BASE = 'https://places.googleapis.com/v1/places/';
export const PLACES_FIELD_MASK = 'displayName,formattedAddress,location';
export const PLACES_CAPS = {
  autocomplete: { minute: 30, day: 300 },
  details: { minute: 10, day: 100 },
};
const TIMEOUT_MS = 2500;
const MAX_QUERY = 200;
const PLACE_ID_RE = /^[A-Za-z0-9_-]{1,256}$/;

export function rectangleFromBbox(bbox) {
  if (!Array.isArray(bbox) || bbox.length !== 4) return null;
  const nums = bbox.map(n => Number(n));
  if (nums.some(n => !Number.isFinite(n))) return null;
  let [south, west, north, east] = nums;
  if (south > north) [south, north] = [north, south];
  if (west > east) [west, east] = [east, west];
  south = Math.max(-90, Math.min(90, south));
  north = Math.max(-90, Math.min(90, north));
  west = Math.max(-180, Math.min(180, west));
  east = Math.max(-180, Math.min(180, east));
  if (south === north || west === east) return null;
  return {
    low: { latitude: south, longitude: west },
    high: { latitude: north, longitude: east },
  };
}

export function cleanPlaceId(raw) {
  const s = String(raw || '').trim().replace(/^places\//, '');
  if (!PLACE_ID_RE.test(s)) return '';
  return s;
}

export function quotaBuckets(nowMs, kind) {
  const d = new Date(Number(nowMs) || Date.now());
  const iso = d.toISOString();
  return {
    minute: `${kind}:${iso.slice(0, 16)}`,
    day: `${kind}:${iso.slice(0, 10)}`,
  };
}

export function quotaAllowed(counts, kind) {
  const caps = PLACES_CAPS[kind];
  if (!caps) return { ok: false, retry: 'day' };
  if ((counts.minute || 0) >= caps.minute) return { ok: false, retry: 'minute' };
  if ((counts.day || 0) >= caps.day) return { ok: false, retry: 'day' };
  return { ok: true };
}

/** In-memory quota for tests. The Worker stores the same buckets in the Durable Object. */
export function memoryQuota(map = new Map()) {
  return async (shopId, kind, nowMs) => {
    const { minute, day } = quotaBuckets(nowMs, kind);
    const mk = shopId + '|' + minute;
    const dk = shopId + '|' + day;
    const cur = { minute: map.get(mk) || 0, day: map.get(dk) || 0 };
    const a = quotaAllowed(cur, kind);
    if (!a.ok) return { ok: false, retry: a.retry };
    map.set(mk, cur.minute + 1);
    map.set(dk, cur.day + 1);
    return { ok: true };
  };
}

function redacted(text, apiKey) {
  let s = String(text || '');
  if (apiKey && s.includes(apiKey)) s = s.split(apiKey).join('[redacted]');
  return s;
}

async function fetchTimed(fetchImpl, url, init, timeoutMs = TIMEOUT_MS) {
  const ac = new AbortController();
  const to = setTimeout(() => ac.abort(), timeoutMs);
  try {
    return await fetchImpl(url, { ...init, signal: ac.signal });
  } finally {
    clearTimeout(to);
  }
}

function suggestionFromPrediction(p) {
  if (!p) return null;
  const name = (p.structuredFormat && p.structuredFormat.mainText && p.structuredFormat.mainText.text)
    || (p.text && p.text.text)
    || '';
  const sub = (p.structuredFormat && p.structuredFormat.secondaryText && p.structuredFormat.secondaryText.text) || '';
  const place_id = cleanPlaceId(p.placeId || p.place || '');
  if (!String(name).trim() || !place_id) return null;
  return { name: String(name).trim(), sub: String(sub).trim(), place_id };
}

function detailsFromPlace(j) {
  const name = (j && j.displayName && j.displayName.text) || '';
  const address = (j && j.formattedAddress) || '';
  const lat = j && j.location && Number(j.location.latitude);
  const lon = j && j.location && Number(j.location.longitude);
  if (!String(name).trim() || !Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return { name: String(name).trim(), address: String(address).trim(), lat, lon };
}

async function readJson(res) {
  try { return await res.json(); } catch { return null; }
}

/**
 * Run one proxied Places call. Never puts the API key in the returned body.
 * Missing key or Google errors: { fallback: true } so the admin can use Photon / Nominatim.
 */
export async function handlePlacesRequest({
  kind,
  body,
  env,
  shopId,
  fetchImpl,
  nowMs,
  quota,
}) {
  const fallback = (reason, extra = {}) => ({
    status: 200,
    body: kind === 'details'
      ? { fallback: true, reason, ...extra }
      : { fallback: true, reason, suggestions: [], ...extra },
  });
  if (!shopId) return { status: 401, body: { error: 'unauthorized' } };
  if (kind !== 'autocomplete' && kind !== 'details') {
    return { status: 400, body: { error: 'Unknown places request' } };
  }

  const apiKey = env && env.GOOGLE_PLACES_API_KEY ? String(env.GOOGLE_PLACES_API_KEY) : '';
  if (!apiKey) return fallback('not_configured');

  const b = body && typeof body === 'object' ? body : {};
  const sessionToken = String(b.sessionToken || b.session_token || '').trim().slice(0, 256);

  if (kind === 'autocomplete') {
    const q = String(b.q || b.input || '').trim();
    if (q.length < 2) return { status: 400, body: { error: 'Type at least two characters' } };
    if (q.length > MAX_QUERY) return { status: 400, body: { error: 'Search is too long' } };
  } else {
    const placeId = cleanPlaceId(b.placeId || b.place_id || '');
    if (!placeId) return { status: 400, body: { error: 'Missing place' } };
  }

  if (typeof quota === 'function') {
    let qres;
    try { qres = await quota(shopId, kind, nowMs || Date.now()); }
    catch { return { status: 429, body: { error: 'Too many place searches. Try again later.', fallback: true, reason: 'rate_limit' } }; }
    if (!qres || !qres.ok) {
      return { status: 429, body: { error: 'Too many place searches. Try again later.', fallback: true, reason: 'rate_limit' } };
    }
  }

  const doFetch = fetchImpl || fetch;
  try {
    if (kind === 'autocomplete') {
      const q = String(b.q || b.input || '').trim();
      const payload = { input: q, languageCode: 'en' };
      if (sessionToken) payload.sessionToken = sessionToken;
      const rect = rectangleFromBbox(b.bbox);
      if (rect) payload.locationBias = { rectangle: rect };
      const res = await fetchTimed(doFetch, PLACES_AUTOCOMPLETE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': apiKey },
        body: JSON.stringify(payload),
      });
      if (!res || !res.ok) return fallback('upstream');
      const j = await readJson(res);
      const suggestions = ((j && j.suggestions) || [])
        .map(s => suggestionFromPrediction(s && s.placePrediction))
        .filter(Boolean);
      return { status: 200, body: { suggestions, fallback: false } };
    }

    const placeId = cleanPlaceId(b.placeId || b.place_id || '');
    const url = new URL(PLACES_DETAILS_BASE + encodeURIComponent(placeId));
    if (sessionToken) url.searchParams.set('sessionToken', sessionToken);
    const res = await fetchTimed(doFetch, url.toString(), {
      method: 'GET',
      headers: {
        'X-Goog-Api-Key': apiKey,
        'X-Goog-FieldMask': PLACES_FIELD_MASK,
      },
    });
    if (!res || !res.ok) return fallback('upstream');
    const j = await readJson(res);
    const details = detailsFromPlace(j);
    if (!details) return fallback('upstream');
    return { status: 200, body: details };
  } catch (e) {
    redacted(e && e.message, apiKey);
    return fallback('upstream');
  }
}
