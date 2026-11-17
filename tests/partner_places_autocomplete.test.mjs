// Partner Google Places proxy: server-side key, session tokens, field mask, bbox bias, fallback, caps.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  handlePlacesRequest,
  memoryQuota,
  rectangleFromBbox,
  cleanPlaceId,
  quotaAllowed,
  PLACES_CAPS,
  PLACES_FIELD_MASK,
  PLACES_AUTOCOMPLETE_URL,
  PLACES_DETAILS_BASE,
} from '../lib/partner_places.js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel) => readFileSync(join(root, rel), 'utf8');
const KEY = 'test-places-key-NOT-A-REAL-SECRET';
const BBOX = [32.53, -117.46, 33.3, -116.95];
const PLACE_ID = 'ChIJTestCoveLaJollaCA';

const googleAutocomplete = {
  suggestions: [{
    placePrediction: {
      place: 'places/' + PLACE_ID,
      placeId: PLACE_ID,
      text: { text: 'La Jolla Cove, San Diego, CA, USA' },
      structuredFormat: {
        mainText: { text: 'La Jolla Cove' },
        secondaryText: { text: 'Coast Walk, San Diego, CA' },
      },
    },
  }],
};
const googleDetails = {
  displayName: { text: 'La Jolla Cove' },
  formattedAddress: '1100 Coast Blvd, La Jolla, CA 92037, USA',
  location: { latitude: 32.850123, longitude: -117.272345 },
};

function jsonRes(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

function recordFetch(handler) {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    const rec = { url: String(url), method: init.method || 'GET', headers: { ...(init.headers || {}) }, body: init.body };
    calls.push(rec);
    return handler(rec);
  };
  return { calls, fetchImpl };
}

function assertNoKeyLeak(obj, key = KEY) {
  const s = typeof obj === 'string' ? obj : JSON.stringify(obj);
  assert.ok(!s.includes(key), 'API key must not appear in the response or logged payload');
}

test('bbox becomes a locationBias rectangle; invalid boxes are dropped', () => {
  assert.deepEqual(rectangleFromBbox(BBOX), {
    low: { latitude: 32.53, longitude: -117.46 },
    high: { latitude: 33.3, longitude: -116.95 },
  });
  assert.equal(rectangleFromBbox([1, 2, 3]), null);
  assert.equal(rectangleFromBbox(null), null);
  const swapped = rectangleFromBbox([33.3, -116.95, 32.53, -117.46]);
  assert.equal(swapped.low.latitude, 32.53);
  assert.equal(swapped.high.longitude, -116.95);
});

test('place ids drop a places/ prefix and reject path junk', () => {
  assert.equal(cleanPlaceId('places/' + PLACE_ID), PLACE_ID);
  assert.equal(cleanPlaceId('../secrets'), '');
  assert.equal(cleanPlaceId('places/foo/bar'), '');
  assert.equal(cleanPlaceId(''), '');
});

test('autocomplete proxies Places API (New), sends a session token, and biases to the shop bbox', async () => {
  const { calls, fetchImpl } = recordFetch(async () => jsonRes(200, googleAutocomplete));
  const quota = memoryQuota();
  const out = await handlePlacesRequest({
    kind: 'autocomplete',
    body: { q: 'cove', sessionToken: 'sess-1', bbox: BBOX },
    env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's1',
    fetchImpl,
    nowMs: Date.UTC(2026, 10, 16, 18, 0, 0),
    quota,
  });
  assert.equal(out.status, 200);
  assert.equal(out.body.fallback, false);
  assert.deepEqual(out.body.suggestions, [{
    name: 'La Jolla Cove',
    sub: 'Coast Walk, San Diego, CA',
    place_id: PLACE_ID,
  }]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, PLACES_AUTOCOMPLETE_URL);
  assert.equal(calls[0].method, 'POST');
  assert.equal(calls[0].headers['X-Goog-Api-Key'], KEY);
  assert.ok(!String(calls[0].url).includes(KEY));
  const payload = JSON.parse(calls[0].body);
  assert.equal(payload.input, 'cove');
  assert.equal(payload.sessionToken, 'sess-1');
  assert.deepEqual(payload.locationBias.rectangle.low, { latitude: 32.53, longitude: -117.46 });
  assert.deepEqual(payload.locationBias.rectangle.high, { latitude: 33.3, longitude: -116.95 });
  assertNoKeyLeak(out.body);
});

test('details uses the Essentials field mask, the same session token, and returns lat/lon', async () => {
  const { calls, fetchImpl } = recordFetch(async () => jsonRes(200, googleDetails));
  const out = await handlePlacesRequest({
    kind: 'details',
    body: { placeId: 'places/' + PLACE_ID, sessionToken: 'sess-1' },
    env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's1',
    fetchImpl,
    quota: memoryQuota(),
  });
  assert.equal(out.status, 200);
  assert.equal(out.body.name, 'La Jolla Cove');
  assert.equal(out.body.address, '1100 Coast Blvd, La Jolla, CA 92037, USA');
  assert.equal(out.body.lat, 32.850123);
  assert.equal(out.body.lon, -117.272345);
  assert.equal(calls.length, 1);
  assert.ok(calls[0].url.startsWith(PLACES_DETAILS_BASE + encodeURIComponent(PLACE_ID)));
  const u = new URL(calls[0].url);
  assert.equal(u.searchParams.get('sessionToken'), 'sess-1');
  assert.ok(!calls[0].url.includes(KEY));
  assert.equal(calls[0].headers['X-Goog-Api-Key'], KEY);
  assert.equal(calls[0].headers['X-Goog-FieldMask'], PLACES_FIELD_MASK);
  assert.equal(PLACES_FIELD_MASK, 'displayName,formattedAddress,location');
  assertNoKeyLeak(out.body);
});

test('missing key returns fallback so the admin can use Photon / Nominatim', async () => {
  const { calls, fetchImpl } = recordFetch(async () => { throw new Error('should not call Google'); });
  const out = await handlePlacesRequest({
    kind: 'autocomplete',
    body: { q: 'cove' },
    env: {},
    shopId: 's1',
    fetchImpl,
    quota: memoryQuota(),
  });
  assert.equal(out.status, 200);
  assert.equal(out.body.fallback, true);
  assert.equal(out.body.reason, 'not_configured');
  assert.deepEqual(out.body.suggestions, []);
  assert.equal(calls.length, 0);
});

test('Google errors and timeouts fall back without leaking the key', async () => {
  for (const handler of [
    async () => jsonRes(403, { error: { message: 'API key ' + KEY + ' denied' } }),
    async () => jsonRes(500, { error: { message: 'boom' } }),
    async () => { throw new Error('network ' + KEY); },
  ]) {
    const { fetchImpl } = recordFetch(handler);
    const out = await handlePlacesRequest({
      kind: 'autocomplete',
      body: { q: 'cove', sessionToken: 's' },
      env: { GOOGLE_PLACES_API_KEY: KEY },
      shopId: 's1',
      fetchImpl,
      quota: memoryQuota(),
    });
    assert.equal(out.status, 200);
    assert.equal(out.body.fallback, true);
    assert.equal(out.body.reason, 'upstream');
    assertNoKeyLeak(out.body);
  }
});

test('details with a Google miss also falls back', async () => {
  const { fetchImpl } = recordFetch(async () => jsonRes(200, { displayName: { text: 'No pin' } }));
  const out = await handlePlacesRequest({
    kind: 'details',
    body: { placeId: PLACE_ID },
    env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's1',
    fetchImpl,
    quota: memoryQuota(),
  });
  assert.equal(out.body.fallback, true);
});

test('unauthenticated calls are refused and never reach Google', async () => {
  const { calls, fetchImpl } = recordFetch(async () => jsonRes(200, googleAutocomplete));
  const out = await handlePlacesRequest({
    kind: 'autocomplete',
    body: { q: 'cove' },
    env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: '',
    fetchImpl,
    quota: memoryQuota(),
  });
  assert.equal(out.status, 401);
  assert.equal(calls.length, 0);
});

test('short queries are rejected before a Google call', async () => {
  const { calls, fetchImpl } = recordFetch(async () => jsonRes(200, googleAutocomplete));
  const out = await handlePlacesRequest({
    kind: 'autocomplete',
    body: { q: 'c' },
    env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's1',
    fetchImpl,
    quota: memoryQuota(),
  });
  assert.equal(out.status, 400);
  assert.equal(calls.length, 0);
});

test('per-shop caps stop a burst and tell the client to fall back', async () => {
  assert.equal(quotaAllowed({ minute: 30, day: 1 }, 'autocomplete').ok, false);
  const quota = memoryQuota();
  const nowMs = Date.UTC(2026, 10, 16, 18, 5, 0);
  const { fetchImpl } = recordFetch(async () => jsonRes(200, googleAutocomplete));
  for (let i = 0; i < PLACES_CAPS.autocomplete.minute; i++) {
    const ok = await handlePlacesRequest({
      kind: 'autocomplete', body: { q: 'cove' + i }, env: { GOOGLE_PLACES_API_KEY: KEY },
      shopId: 's1', fetchImpl, nowMs, quota,
    });
    assert.equal(ok.status, 200);
    assert.equal(ok.body.fallback, false);
  }
  const blocked = await handlePlacesRequest({
    kind: 'autocomplete', body: { q: 'overflow' }, env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's1', fetchImpl, nowMs, quota,
  });
  assert.equal(blocked.status, 429);
  assert.equal(blocked.body.fallback, true);
  assert.equal(blocked.body.reason, 'rate_limit');
  const otherShop = await handlePlacesRequest({
    kind: 'autocomplete', body: { q: 'cove' }, env: { GOOGLE_PLACES_API_KEY: KEY },
    shopId: 's2', fetchImpl, nowMs, quota,
  });
  assert.equal(otherShop.status, 200);
  assert.equal(otherShop.body.fallback, false);
});

test('worker keeps the key server-side and documents the secret; admin falls back to Photon / Nominatim', () => {
  const w = read('workers/partner/src/index.js');
  const toml = read('workers/partner/wrangler.toml');
  const admin = read('public/partner/admin.js');
  const proxy = read('functions/api/partner/[[path]].js');
  const lib = read('lib/partner_places.js');
  assert.match(w, /handlePlacesRequest/);
  assert.match(lib, /GOOGLE_PLACES_API_KEY/);
  assert.match(w, /shopId: a\.shopId/);
  assert.match(w, /env,/);
  assert.match(w, /\/places\/autocomplete/);
  assert.match(w, /\/places\/details/);
  assert.match(w, /takePlacesQuota/);
  assert.match(toml, /wrangler secret put GOOGLE_PLACES_API_KEY/);
  assert.doesNotMatch(toml, /GOOGLE_PLACES_API_KEY\s*=/);
  assert.doesNotMatch(admin, /X-Goog-Api-Key/);
  assert.doesNotMatch(admin, /places\.googleapis\.com/);
  assert.match(admin, /\/places\/autocomplete/);
  assert.match(admin, /\/places\/details/);
  assert.match(admin, /photon\.komoot\.io/);
  assert.match(admin, /nominatim\.openstreetmap\.org/);
  assert.match(admin, /sessionToken/);
  assert.match(proxy, /partnerBase/);
  const accessAt = w.indexOf('async function access(');
  assert.ok(accessAt > 0);
  const autoAt = w.indexOf("/places/autocomplete");
  const detAt = w.indexOf("/places/details");
  assert.ok(autoAt > accessAt, 'autocomplete must use shop access');
  assert.ok(detAt > accessAt, 'details must use shop access');
});
