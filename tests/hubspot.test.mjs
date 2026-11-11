// node --test tests/hubspot.test.mjs
// No HubSpot tag until an explicit allow. Refusal sticks. A privacy signal
// blocks a stored allow. After allow, a map path change keeps one tag.
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
  if (opts.slot) {
    const slot = make('div');
    slot.id = 'gcm-hs-slot';
    body.appendChild(slot);
  }
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
    HubSpotConversations: opts.conversations,
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
  function byText(label) {
    return buttons().find((b) => b.textContent === label) || null;
  }
  function loaders() {
    const found = [];
    walk(root, (n) => { if (n.id === 'hs-script-loader') found.push(n); });
    return found;
  }
  return {
    store,
    location,
    sandbox,
    document,
    buttons,
    byText,
    loaders,
    cookies,
    fire(type) { (document.listeners[type] || []).forEach((fn) => fn()); },
  };
}

test('source is the https loader for portal 52245531 only', () => {
  assert.equal(code.split(LOADER).length - 1, 1);
  assert.equal(code.includes('247729169'), false);
  assert.equal(/(^|[^:])\/\/js\.hs-scripts\.com/.test(code), false);
  assert.equal((code.match(/https?:\/\/[^\s'"]+/g) || []).join('\n'), LOADER);
  assert.equal(/\b(hapikey|private[_-]?app|client_secret|pat-[a-z0-9]|bearer|api[_-]?key)\b/i.test(code), false);
  assert.equal(code.includes('widget.open'), false);
  assert.equal(code.includes('usemessages'), false);
});

test('no loader and two equal choices before consent', () => {
  const page = boot();
  assert.equal(page.loaders().length, 0);
  const allow = page.byText('Allow HubSpot');
  const refuse = page.byText("Don't allow");
  assert.ok(allow && refuse);
  assert.equal(allow.className, refuse.className);
  assert.equal(allow.type, 'button');
  assert.equal(refuse.type, 'button');
  assert.equal(allow.hidden, false);
  assert.equal(refuse.hidden, false);
});

test('refusal is stored and still does not load', () => {
  const page = boot();
  page.byText("Don't allow").click();
  assert.equal(page.store['gcm-hubspot'], 'deny');
  assert.equal(page.loaders().length, 0);
  assert.equal(page.byText('Allow HubSpot'), null);
  const again = boot({ ls: { ...page.store } });
  assert.equal(again.loaders().length, 0);
  assert.equal(again.byText('Allow HubSpot'), null);
});

test('allow inserts one loader and a town change keeps one', () => {
  const page = boot({ pathname: '/map' });
  page.byText('Allow HubSpot').click();
  assert.equal(page.loaders().length, 1);
  assert.equal(page.loaders()[0].src, LOADER);
  assert.equal(page.loaders()[0].async, true);
  assert.equal(page.loaders()[0].defer, true);
  page.location.pathname = '/map/pacific-beach';
  page.sandbox.GCMHubSpot.load();
  vm.runInNewContext(code, page.sandbox, { filename: 'hubspot.js' });
  page.sandbox.GCMHubSpot.load();
  assert.equal(page.loaders().length, 1);
  assert.equal(page.loaders()[0].src, LOADER);
});

test('revoke stops a later load, calls the tracking opt-out, and expires HubSpot cookies', () => {
  let removed = 0;
  const page = boot({ conversations: { widget: { remove() { removed += 1; } } } });
  page.byText('Allow HubSpot').click();
  assert.equal(page.loaders().length, 1);
  assert.equal(page.document.getElementById('gcm-hs').className, 'float revoke');
  page.byText('Turn it off').click();
  assert.equal(page.store['gcm-hubspot'], 'deny');
  assert.equal(page.loaders().length, 0);
  assert.equal(removed, 1);
  const calls = page.sandbox._hsq.map((x) => x[0]);
  assert.ok(calls.includes('doNotTrack'));
  assert.ok(calls.includes('revokeCookieConsent'));
  assert.ok(page.sandbox._hsp.some((x) => x[0] === 'revokeCookieConsent'));
  const expired = page.cookies.join('\n');
  for (const name of ['__hstc', 'hubspotutk', '__hssc', '__hssrc', 'messagesUtk']) {
    assert.match(expired, new RegExp(name + '=; expires=Thu, 01 Jan 1970'));
  }
  assert.equal(expired.includes('__hs_do_not_track='), false);
  const later = boot({ ls: { 'gcm-hubspot': 'deny' } });
  assert.equal(later.loaders().length, 0);
});

test('a stored allow still loads once, including www and renter pages', () => {
  for (const opts of [
    { hostname: 'www.golfcartmap.com' },
    { pathname: '/p/beach-mode' },
    { pathname: '/privacy', slot: true },
    { doNotTrack: '0' },
  ]) {
    const page = boot({ ...opts, ls: { 'gcm-hubspot': 'allow' } });
    assert.equal(page.loaders().length, 1, JSON.stringify(opts));
  }
});

test('privacy signals block a stored allow and hide the allow button', () => {
  const cases = [
    ['GPC', { gpc: true }],
    ['DNT', { doNotTrack: '1' }],
    ['gcm-notrack', { ls: { 'gcm-notrack': '1', 'gcm-hubspot': 'allow' } }],
    ['NO_TRACK', { NO_TRACK: 1 }],
  ];
  for (const [label, opts] of cases) {
    const page = boot({ ls: { 'gcm-hubspot': 'allow' }, ...opts });
    assert.equal(page.loaders().length, 0, label);
    assert.equal(page.byText('Allow HubSpot'), null, label);
    page.sandbox.GCMHubSpot.allow();
    assert.equal(page.loaders().length, 0, label);
  }
});

test('native app, partner admin, preview hosts, and internal traffic stay unloaded', () => {
  const cases = [
    ['native', { Capacitor: { isNativePlatform: () => true } }],
    ['file', { protocol: 'file:' }],
    ['capacitor', { protocol: 'capacitor:' }],
    ['partner', { pathname: '/partner' }],
    ['partner shop', { pathname: '/partner/shops' }],
    ['localhost', { hostname: 'localhost' }],
    ['preview', { hostname: 'abc.golfcart-maps.pages.dev' }],
    ['webdriver', { webdriver: true }],
    ['GCM_INTERNAL', { GCM_INTERNAL: 'sim' }],
    ['gcm-internal', { ls: { 'gcm-internal': 'debug' } }],
  ];
  for (const [label, opts] of cases) {
    const page = boot({ ls: { 'gcm-hubspot': 'allow' }, ...opts });
    assert.equal(page.loaders().length, 0, label);
    assert.equal(page.byText('Allow HubSpot'), null, label);
  }
});

test('an existing tag without consent is removed', () => {
  const page = boot({ existing: true });
  assert.equal(page.loaders().length, 0);
});

test('DOMContentLoaded does not load before a choice', () => {
  const page = boot({ readyState: 'loading' });
  assert.equal(page.loaders().length, 0);
  page.fire('DOMContentLoaded');
  page.fire('DOMContentLoaded');
  assert.equal(page.loaders().length, 0);
  page.byText('Allow HubSpot').click();
  assert.equal(page.loaders().length, 1);
});

test('the privacy page can allow after a refusal', () => {
  const page = boot({ pathname: '/privacy', slot: true, ls: { 'gcm-hubspot': 'deny' } });
  assert.equal(page.loaders().length, 0);
  const allow = page.byText('Allow HubSpot');
  assert.ok(allow);
  assert.equal(page.document.getElementById('gcm-hs').className, 'page');
  allow.click();
  assert.equal(page.loaders().length, 1);
  assert.equal(page.store['gcm-hubspot'], 'allow');
});
