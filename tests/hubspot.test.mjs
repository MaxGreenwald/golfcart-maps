// node --test tests/hubspot.test.mjs
// The public loader inserts portal 52245531 once. A second call, a second
// evaluation, and a map-style path change must not add another tag.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const code = readFileSync(new URL('../public/hubspot.js', import.meta.url), 'utf8');
const LOADER = 'https://js.hs-scripts.com/52245531.js';

function boot(opts = {}) {
  const scripts = [];
  const listeners = {};
  const store = { ...(opts.ls || {}) };
  if (opts.existing) scripts.push({ id: 'hs-script-loader', src: LOADER });
  const location = {
    hostname: opts.hostname ?? 'golfcartmap.com',
    pathname: opts.pathname ?? '/',
    protocol: opts.protocol ?? 'https:',
    search: opts.search ?? '',
  };
  const document = {
    readyState: opts.readyState ?? 'complete',
    body: { appendChild(node) { scripts.push(node); return node; } },
    documentElement: { appendChild(node) { scripts.push(node); return node; } },
    getElementById(id) { return scripts.find((s) => s.id === id) || null; },
    createElement() { return {}; },
    addEventListener(type, fn) { (listeners[type] ||= []).push(fn); },
  };
  const navigator = {
    webdriver: opts.webdriver === true,
    doNotTrack: opts.doNotTrack,
    globalPrivacyControl: opts.gpc === true ? true : undefined,
  };
  const sandbox = {
    document,
    navigator,
    location,
    localStorage: { getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null) },
    Capacitor: opts.Capacitor,
    NO_TRACK: opts.NO_TRACK,
    GCM_INTERNAL: opts.GCM_INTERNAL,
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox, { filename: 'hubspot.js' });
  return {
    scripts,
    location,
    sandbox,
    fire(type) { (listeners[type] || []).forEach((fn) => fn()); },
  };
}

test('source is the https loader for portal 52245531 only', () => {
  assert.equal(code.split(LOADER).length - 1, 1);
  assert.equal(code.includes('247729169'), false);
  assert.equal(/(^|[^:])\/\/js\.hs-scripts\.com/.test(code), false);
  assert.equal((code.match(/https?:\/\/[^\s'"]+/g) || []).join('\n'), LOADER);
  assert.equal(/\b(hapikey|private[_-]?app|client_secret|pat-[a-z0-9]|bearer|api[_-]?key)\b/i.test(code), false);
});

test('a public page inserts one async loader', () => {
  const page = boot();
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].id, 'hs-script-loader');
  assert.equal(page.scripts[0].src, LOADER);
  assert.equal(page.scripts[0].async, true);
  assert.equal(page.scripts[0].defer, true);
  assert.equal(page.scripts[0].type, 'text/javascript');
});

test('www host loads; localhost and preview hosts do not', () => {
  assert.equal(boot({ hostname: 'www.golfcartmap.com' }).scripts.length, 1);
  for (const hostname of ['localhost', '127.0.0.1', 'abc.golfcart-maps.pages.dev', 'golfcartmap.com.evil.test']) {
    assert.equal(boot({ hostname }).scripts.length, 0, hostname);
  }
});

test('map town change and a second evaluation keep a single tag', () => {
  const page = boot({ pathname: '/map' });
  assert.equal(page.scripts.length, 1);
  page.location.pathname = '/map/pacific-beach';
  page.sandbox.GCMHubSpot.load();
  vm.runInNewContext(code, page.sandbox, { filename: 'hubspot.js' });
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].src, LOADER);
});

test('an existing loader is left alone', () => {
  const page = boot({ existing: true });
  assert.equal(page.scripts.length, 1);
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.scripts.length, 1);
});

test('DOMContentLoaded inserts the loader once', () => {
  const page = boot({ readyState: 'loading' });
  assert.equal(page.scripts.length, 0);
  page.fire('DOMContentLoaded');
  page.fire('DOMContentLoaded');
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.scripts.length, 1);
});

test('native app, partner admin, opt-out, and internal traffic do not insert', () => {
  const cases = [
    ['native', { Capacitor: { isNativePlatform: () => true } }],
    ['file', { protocol: 'file:' }],
    ['capacitor', { protocol: 'capacitor:' }],
    ['partner', { pathname: '/partner' }],
    ['partner shop', { pathname: '/partner/shops' }],
    ['GPC', { gpc: true }],
    ['DNT', { doNotTrack: '1' }],
    ['gcm-notrack', { ls: { 'gcm-notrack': '1' } }],
    ['NO_TRACK', { NO_TRACK: 1 }],
    ['webdriver', { webdriver: true }],
    ['GCM_INTERNAL', { GCM_INTERNAL: 'sim' }],
    ['gcm-internal', { ls: { 'gcm-internal': 'debug' } }],
  ];
  for (const [label, opts] of cases) assert.equal(boot(opts).scripts.length, 0, label);
});

test('renter pages and a DNT value other than 1 still load', () => {
  assert.equal(boot({ pathname: '/p/beach-mode' }).scripts.length, 1);
  assert.equal(boot({ pathname: '/privacy' }).scripts.length, 1);
  assert.equal(boot({ doNotTrack: '0' }).scripts.length, 1);
});
