// Pages partner proxy must not follow Worker OAuth 302s. The browser needs
// status, Location, and Set-Cookie so Google sign-in can start on golfcartmap.com.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { onRequest, partnerBase } from '../functions/api/partner/[[path]].js';

const read = (p) => readFileSync(new URL('../' + p, import.meta.url), 'utf8');

const GOOGLE = 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test&redirect_uri=https%3A%2F%2Fgolfcartmap.com%2Fapi%2Fpartner%2Fauth%2Fcallback';
const STATE_COOKIE = 'gcm_oauth_st=abc123; Max-Age=600; Path=/; HttpOnly; Secure; SameSite=Lax';

async function withMockFetch(handler, run) {
  const orig = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    return handler(url, init);
  };
  try {
    return await run(calls);
  } finally {
    globalThis.fetch = orig;
  }
}

test('partnerBase sends production host to gcm-partner and previews to the preview Worker', () => {
  assert.equal(partnerBase('golfcartmap.com', {}), 'https://gcm-partner.maxgreenwald-assistant.workers.dev');
  assert.equal(partnerBase('www.golfcartmap.com', {}), 'https://gcm-partner.maxgreenwald-assistant.workers.dev');
  assert.equal(partnerBase('abc.golfcart-maps.pages.dev', {}), 'https://gcm-partner-preview.maxgreenwald-assistant.workers.dev');
  assert.equal(partnerBase('example.com', { PARTNER_URL: 'https://example.workers.dev/' }), 'https://example.workers.dev');
});

test('proxy returns the Worker 302 Location and Set-Cookie and calls fetch with redirect:manual', async () => {
  await withMockFetch(() => {
    const headers = new Headers();
    headers.set('location', GOOGLE);
    headers.append('set-cookie', STATE_COOKIE);
    headers.set('cache-control', 'no-store');
    return new Response(null, { status: 302, headers });
  }, async (calls) => {
    const res = await onRequest({
      request: new Request('https://golfcartmap.com/api/partner/auth/google', { method: 'GET' }),
      env: {},
      params: { path: ['auth', 'google'] },
    });
    assert.equal(res.status, 302);
    assert.equal(res.headers.get('location'), GOOGLE);
    const cookies = res.headers.getSetCookie();
    assert.equal(cookies.length, 1);
    assert.equal(cookies[0], STATE_COOKIE);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, 'https://gcm-partner.maxgreenwald-assistant.workers.dev/auth/google');
    assert.equal(calls[0].init.redirect, 'manual');
    assert.equal(calls[0].init.method, 'GET');
    assert.equal(calls[0].init.headers.get('x-partner-origin'), 'https://golfcartmap.com');
  });
});

test('proxy also forwards a callback 302 to /partner with the session cookie', async () => {
  const session = 'gcm_partner=tok.sig; Max-Age=1209600; Path=/; HttpOnly; Secure; SameSite=Lax';
  await withMockFetch(() => {
    const headers = new Headers();
    headers.set('location', 'https://golfcartmap.com/partner');
    headers.append('set-cookie', session);
    headers.append('set-cookie', 'gcm_oauth_st=; Max-Age=0; Path=/');
    return new Response(null, { status: 302, headers });
  }, async (calls) => {
    const res = await onRequest({
      request: new Request('https://golfcartmap.com/api/partner/auth/callback?code=x&state=y', {
        method: 'GET',
        headers: { cookie: 'gcm_oauth_st=y' },
      }),
      env: {},
      params: { path: ['auth', 'callback'] },
    });
    assert.equal(res.status, 302);
    assert.equal(res.headers.get('location'), 'https://golfcartmap.com/partner');
    const cookies = res.headers.getSetCookie();
    assert.equal(cookies.length, 2);
    assert.ok(cookies.includes(session));
    const sessionCookie = cookies.find(c => c.startsWith('gcm_partner='));
    const clear = cookies.find(c => c.startsWith('gcm_oauth_st='));
    assert.ok(sessionCookie);
    assert.ok(clear);
    assert.match(sessionCookie, /Max-Age=1209600/);
    assert.equal(/Max-Age=0/.test(sessionCookie), false);
    assert.match(clear, /Max-Age=0/);
    assert.equal(calls[0].init.redirect, 'manual');
    assert.equal(calls[0].init.headers.get('cookie'), 'gcm_oauth_st=y');
    assert.equal(calls[0].url, 'https://gcm-partner.maxgreenwald-assistant.workers.dev/auth/callback?code=x&state=y');
  });
});

test('Worker OAuth cookies use Path=/ and SameSite=Lax and do not pin Domain to workers.dev', () => {
  const src = read('workers/partner/src/index.js');
  assert.match(src, /gcm_oauth_st=\$\{st\}; Max-Age=600; Path=\/; HttpOnly; Secure; SameSite=Lax/);
  assert.match(src, /gcm_partner=\$\{encodeURIComponent\(token\)\}; Max-Age=\$\{maxAge\}; Path=\/; HttpOnly; Secure; SameSite=Lax/);
  assert.equal(/set-cookie[\s\S]{0,200}Domain=/i.test(src), false);
  assert.equal(/workers\.dev/.test(src.split('function setCookie')[1].slice(0, 400)), false);
  assert.equal(src.includes("setCookie(token) + ', gcm_oauth_st="), false);
  const proxy = read('functions/api/partner/[[path]].js');
  assert.match(proxy, /redirect:\s*'manual'/);
});

test('portal Continue with Google links to /api/partner/auth/start, not /auth/google', () => {
  const admin = read('public/partner/admin.js');
  assert.match(admin, /href="\/api\/partner\/auth\/start"/);
  assert.equal(admin.includes('/api/partner/auth/google'), false);
});

test('proxy also returns a 302 for the unflagged /auth/start path', async () => {
  await withMockFetch(() => {
    const headers = new Headers();
    headers.set('location', GOOGLE);
    headers.append('set-cookie', STATE_COOKIE);
    headers.set('cache-control', 'no-store');
    return new Response(null, { status: 302, headers });
  }, async (calls) => {
    const res = await onRequest({
      request: new Request('https://golfcartmap.com/api/partner/auth/start', { method: 'GET' }),
      env: {},
      params: { path: ['auth', 'start'] },
    });
    assert.equal(res.status, 302);
    assert.equal(res.headers.get('location'), GOOGLE);
    assert.equal(calls[0].url, 'https://gcm-partner.maxgreenwald-assistant.workers.dev/auth/start');
    assert.equal(calls[0].init.redirect, 'manual');
  });
});
