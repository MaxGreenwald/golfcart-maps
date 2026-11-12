// node --test tests/hubspot.test.mjs
// The portal script is inserted on the first view of a public golfcartmap.com
// page. No site consent prompt. Native, partner, other hosts, and internal
// or NO_TRACK sessions stay unloaded.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const code = readFileSync(new URL('../public/hubspot.js', import.meta.url), 'utf8');
const LOADER = 'https://js.hs-scripts.com/52245531.js';

function boot(opts = {}) {
  const store = { ...(opts.ls || {}) };
  function make(tag) {
    const node = {
      tagName: String(tag || '').toUpperCase(),
      id: '',
      className: '',
      hidden: false,
      type: '',
      textContent: '',
      children: [],
      parentNode: null,
      style: {},
      listeners: {},
      get firstChild() { return this.children[0] || null; },
      appendChild(child) {
        this.children.push(child);
        child.parentNode = this;
        return child;
      },
      removeChild(child) {
        const i = this.children.indexOf(child);
        if (i >= 0) this.children.splice(i, 1);
        child.parentNode = null;
        return child;
      },
      setAttribute(k, v) {
        if (k === 'id') this.id = String(v);
      },
      addEventListener(type, fn) { this.listeners[type] = fn; },
      click() { if (this.listeners.click) this.listeners.click(); },
    };
    return node;
  }
  const head = make('head');
  const body = make('body');
  const root = make('html');
  root.appendChild(head);
  root.appendChild(body);
  if (opts.existing) {
    const prior = make('script');
    prior.id = 'hs-script-loader';
    prior.src = LOADER;
    body.appendChild(prior);
  }
  function walk(node, fn) {
    if (!node) return;
    fn(node);
    for (const child of node.children || []) walk(child, fn);
  }
  const cookies = [];
  const document = {
    readyState: opts.readyState ?? 'complete',
    head,
    body,
    documentElement: root,
    cookies,
    getElementById(id) {
      let found = null;
      walk(root, (n) => { if (n.id === id) found = n; });
      return found;
    },
    createElement: make,
    addEventListener(type, fn) { (document.listeners[type] ||= []).push(fn); },
    listeners: {},
  };
  const location = {
    hostname: opts.hostname ?? 'golfcartmap.com',
    pathname: opts.pathname ?? '/',
    protocol: opts.protocol ?? 'https:',
    search: opts.search ?? '',
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
    localStorage: {
      getItem: (k) => (Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
    },
    Capacitor: opts.Capacitor,
    NO_TRACK: opts.NO_TRACK,
    GCM_INTERNAL: opts.GCM_INTERNAL,
  };
  Object.defineProperty(document, 'cookie', {
    get() { return cookies.map((row) => row.split(';')[0]).join('; '); },
    set(value) { cookies.push(String(value)); },
  });
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox, { filename: 'hubspot.js' });
  function buttons() {
    const found = [];
    walk(root, (n) => { if (n.tagName === 'BUTTON') found.push(n); });
    return found;
  }
  function loaders() {
    const found = [];
    walk(root, (n) => { if (n.id === 'hs-script-loader') found.push(n); });
    return found;
  }
  function text() {
    const bits = [];
    walk(root, (n) => { if (n.textContent) bits.push(n.textContent); });
    return bits.join('\n');
  }
  return {
    store,
    location,
    sandbox,
    document,
    buttons,
    loaders,
    cookies,
    text,
    fire(type) { (document.listeners[type] || []).forEach((fn) => fn()); },
  };
}

function assertLoaded(page, label) {
  assert.equal(page.loaders().length, 1, label);
  assert.equal(page.loaders()[0].src, LOADER, label);
  assert.equal(page.loaders()[0].async, true, label);
  assert.equal(page.loaders()[0].defer, true, label);
  assert.equal(page.buttons().length, 0, label);
  assert.equal(page.document.getElementById('gcm-hs'), null, label);
  assert.equal(page.cookies.length, 0, label);
}

test('source is the https loader for portal 52245531 only', () => {
  assert.equal(code.split(LOADER).length - 1, 1);
  assert.equal(code.includes('247729169'), false);
  assert.equal(/(^|[^:])\/\/js\.hs-scripts\.com/.test(code), false);
  assert.equal((code.match(/https?:\/\/[^\s'"]+/g) || []).join('\n'), LOADER);
  assert.equal(/\b(hapikey|private[_-]?app|client_secret|pat-[a-z0-9]|bearer|api[_-]?key)\b/i.test(code), false);
  assert.equal(code.includes('widget.open'), false);
  assert.equal(code.includes('usemessages'), false);
  assert.equal(code.includes('Allow HubSpot'), false);
  assert.equal(code.includes('gcm-hs'), false);
  assert.equal(code.includes('gcm-hubspot'), false);
  assert.equal(code.includes('globalPrivacyControl'), false);
  assert.equal(/EU|GDPR|United Kingdom|geolocation|geoip/i.test(code), false);
});

test('first public page view inserts one loader and no consent prompt', () => {
  for (const pathname of ['/', '/map', '/privacy', '/sandiego', '/golf-cart-maps', '/p/beach-mode', '/for-rental-shops', '/404']) {
    const page = boot({ pathname });
    assertLoaded(page, pathname);
    assert.equal(page.text().includes('Allow'), false, pathname);
    assert.deepEqual(page.store, {}, pathname);
  }
});

test('a stored deny and privacy signals still load on first view', () => {
  const cases = [
    { ls: { 'gcm-hubspot': 'deny' } },
    { ls: { 'gcm-hubspot': 'allow' } },
    { gpc: true },
    { doNotTrack: '1' },
    { doNotTrack: '0' },
    { ls: { 'gcm-notrack': '1' } },
  ];
  for (const opts of cases) {
    const page = boot(opts);
    assertLoaded(page, JSON.stringify(opts));
  }
});

test('DOMContentLoaded loads once without a click', () => {
  const page = boot({ readyState: 'loading' });
  assert.equal(page.loaders().length, 0);
  assert.equal(page.buttons().length, 0);
  page.fire('DOMContentLoaded');
  page.fire('DOMContentLoaded');
  assertLoaded(page, 'after');
});

test('an existing loader is kept, and a partner path removes it', () => {
  const page = boot({ existing: true, pathname: '/' });
  assert.equal(page.loaders().length, 1);
  page.location.pathname = '/partner/shops';
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.loaders().length, 0);
  page.location.pathname = '/map';
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.loaders().length, 1);
});

test('native app, partner admin, other hosts, and internal sessions stay unloaded', () => {
  const cases = [
    ['native', { Capacitor: { isNativePlatform: () => true } }],
    ['file', { protocol: 'file:' }],
    ['capacitor', { protocol: 'capacitor:' }],
    ['ionic', { protocol: 'ionic:' }],
    ['partner', { pathname: '/partner' }],
    ['partner shop', { pathname: '/partner/shops' }],
    ['www', { hostname: 'www.golfcartmap.com' }],
    ['localhost', { hostname: 'localhost' }],
    ['preview', { hostname: 'abc.golfcart-maps.pages.dev' }],
    ['webdriver', { webdriver: true }],
    ['GCM_INTERNAL', { GCM_INTERNAL: 'sim' }],
    ['gcm-internal', { ls: { 'gcm-internal': 'debug' } }],
    ['NO_TRACK', { NO_TRACK: 1 }],
  ];
  for (const [label, opts] of cases) {
    const page = boot(opts);
    assert.equal(page.loaders().length, 0, label);
    assert.equal(page.buttons().length, 0, label);
    assert.equal(page.document.getElementById('gcm-hs'), null, label);
  }
});
