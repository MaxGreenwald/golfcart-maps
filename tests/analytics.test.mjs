// node --test tests/analytics.test.mjs  — event schema / PII guard (lib/analytics.js) and the /api/e proxy (functions/api/e.js)
import test from 'node:test';
import assert from 'node:assert/strict';
import { sanitize, EVENTS, PLATFORMS } from '../lib/analytics.js';
import { sinkFor, onRequestPost } from '../functions/api/e.js';

const base = { v: 1, t: 'sd', pl: 'web', pwa: false, i: '0b9c2a4e-1111-4222-8333-444455556666', s: '1c9c2a4e-1111-4222-8333-444455556666' };

test('internal channel survives sanitize and the /api/e forward, junk does not', () => {
  const once = sanitize({ ...base, e: 'session', internal: 'simulator', p: { utm_source: 'nextdoor' } });
  assert.equal(once.props.internal, 'sim');
  assert.equal(once.props.utm_source, 'nextdoor');
  const twice = sanitize({ e: once.event, t: once.town, pl: once.platform, pwa: false, i: once.iid, s: once.sid, p: once.props });
  assert.equal(twice.props.internal, 'sim');
  assert.equal(sanitize({ ...base, e: 'session', internal: 'Max Greenwald' }).props.internal, undefined);
  assert.equal(sanitize({ ...base, e: 'session', p: { internal: 'tf' } }).props.internal, 'tf');
});

test('unknown events are dropped', () => {
  assert.equal(sanitize({ ...base, e: 'pageview' }), null);
  assert.equal(sanitize({ ...base, e: '__proto__' }), null);
  assert.equal(sanitize(null), null);
  assert.equal(sanitize('session'), null);
});

test('only allowlisted props survive; PII never does', () => {
  const r = sanitize({ ...base, e: 'route_searched', p: { ok: true, risky: false, mi: 2.44, reason: 'other',
    email: 'max@example.com', lat: 32.96, lon: -117.27, name: 'Max', phone: '867-5309', from: 'Del Mar Plaza', q: 'my house' } });
  assert.deepEqual(r.props, { ok: true, risky: false, mi: 2.5, reason: 'other' });
  const s = JSON.stringify(r);
  for (const bad of ['@', '32.96', '-117.27', 'Max', '867', 'Plaza', 'house']) assert.ok(!s.includes(bad), `leaked ${bad}`);
});

test('every event has a fixed prop list and no free-text or location keys', () => {
  for (const [e, keys] of Object.entries(EVENTS)) for (const k of keys)
    assert.ok(!/lat|lon|email|name|phone|addr|ip|ua|text|query|q$/.test(k), `${e}.${k}`);
});

test('utm values are short lowercase tokens; anything else is dropped', () => {
  const r = sanitize({ ...base, e: 'session', p: { utm_source: 'Nextdoor', utm_medium: 'Paid Social', utm_campaign: '<script>alert(1)</script>',
    utm_content: 'x'.repeat(80), ref: 'www.Google.com', landing: '/delmar', new_install: true } });
  assert.equal(r.props.utm_source, 'nextdoor');
  assert.equal(r.props.utm_medium, 'paid_social');
  assert.ok(!('utm_campaign' in r.props));
  assert.equal(r.props.utm_content.length, 40);
  assert.equal(r.props.ref, 'google.com');
  assert.equal(r.props.landing, 'delmar');
  assert.equal(r.props.new_install, true);
});

test('referrer keeps the host only, never a path or query', () => {
  assert.ok(!('ref' in sanitize({ ...base, e: 'session', p: { ref: 'https://google.com/search?q=golf+carts' } }).props));
});

test('platforms, towns, ids', () => {
  assert.deepEqual(PLATFORMS, ['web', 'ios', 'android', 'carplay']);
  assert.equal(sanitize({ ...base, e: 'session', pl: 'carplay' }).platform, 'carplay');
  assert.equal(sanitize({ ...base, e: 'session', pl: 'windows' }).platform, 'web');
  assert.equal(sanitize({ ...base, e: 'session', t: 'San Diego, CA 92014' }).town, null);
  assert.equal(sanitize({ ...base, e: 'session', i: 'max@example.com' }).iid, null);
  assert.equal(sanitize({ ...base, e: 'session', s: 'x' }).sid, null);
});

test('enums and numbers are clamped', () => {
  assert.deepEqual(sanitize({ ...base, e: 'road_report_filed', p: { issue: 'wrong_speed' } }).props, { issue: 'wrong_speed' });
  assert.deepEqual(sanitize({ ...base, e: 'road_report_filed', p: { issue: 'the light at 5th is broken' } }).props, {});
  assert.deepEqual(sanitize({ ...base, e: 'route_completed', p: { mi: 9999 } }).props, {});
  assert.deepEqual(sanitize({ ...base, e: 'route_completed', p: { mi: -1 } }).props, {});
  assert.deepEqual(sanitize({ ...base, e: 'route_searched', p: { ok: 'yes' } }).props, {});
});

test('production host goes to the production worker, everything else to preview', () => {
  assert.match(sinkFor('golfcartmap.com', {}), /\/\/gcm-analytics\./);
  assert.match(sinkFor('www.golfcartmap.com', {}), /\/\/gcm-analytics\./);
  assert.match(sinkFor('analytics-v2.golfcart-maps.pages.dev', {}), /gcm-analytics-preview\./);
  assert.match(sinkFor('localhost', {}), /gcm-analytics-preview\./);
  assert.equal(sinkFor('golfcartmap.com', { ANALYTICS_URL: 'https://x/e' }), 'https://x/e');
});

test('/api/e forwards only the sanitized row and always answers 204', async () => {
  const calls = []; const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, o) => { calls.push([url, JSON.parse(o.body)]); return new Response(null, { status: 204 }) };
  try {
    const req = b => new Request('https://analytics-v2.golfcart-maps.pages.dev/api/e', { method: 'POST', body: typeof b === 'string' ? b : JSON.stringify(b) });
    let r = await onRequestPost({ request: req({ ...base, e: 'town_viewed', p: { how: 'picker', email: 'a@b.c' } }), env: {} });
    assert.equal(r.status, 204); assert.equal(calls.length, 1);
    assert.match(calls[0][0], /gcm-analytics-preview/);
    assert.deepEqual(calls[0][1].p, { how: 'picker' });
    for (const b of ['not json', JSON.stringify({ e: 'nope' }), 'x'.repeat(5000)]) { r = await onRequestPost({ request: req(b), env: {} }); assert.equal(r.status, 204) }
    assert.equal(calls.length, 1);
  } finally { globalThis.fetch = realFetch }
});

test('App Store badge event is accepted (and legacy testflight_click still counts)', () => {
  for (const e of ['app_store_click', 'testflight_click']) {
    const r = sanitize({ v: 1, e, pl: 'web', i: 'abcdefgh12', s: 'abcdefgh34', p: { position: 'app_section' } });
    assert.ok(r, e); assert.equal(r.props.position, 'app_section');
  }
});

test('every data-ev used by the site generators is on the allowlist', async () => {
  const fs = await import('node:fs');
  const files = ['scripts/seo_landing.py', 'scripts/seo_common.py', 'public/app.js', 'public/carplay.js'];
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    for (const m of fs.readFileSync(f, 'utf8').matchAll(/data-ev=["'\\]*([a-z_]+)/g)) assert.ok(EVENTS[m[1]], `${f}: ${m[1]} not in EVENTS`);
  }
});
