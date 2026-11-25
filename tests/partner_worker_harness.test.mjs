// The in-process partner Worker harness runs the real Worker: sign in, a shop, a code, an unlock.
import test from 'node:test';
import assert from 'node:assert/strict';
import { makePartner } from './partner_worker_harness.mjs';

test('owner signs in, makes a code, and a renter unlocks with it', async () => {
  const p = makePartner();
  const { owner } = await p.seedShop();
  const s = await p.call('/shop', { as: owner });
  assert.equal(s.status, 200);
  assert.equal(s.body.shop.slug, 'lajollacartco');
  const c = await p.call('/shop/codes', { as: owner, json: { code: 'ABCD' } });
  assert.equal(c.status, 201);
  const u = await p.call('/public/lajollacartco/unlock?code=ABCD');
  assert.equal(u.status, 200);
  assert.equal(u.body.unlocked, true);
  const anon = await p.call('/shop');
  assert.equal(anon.status, 401);
});

test('Google OAuth callback sends session and cleared state as two Set-Cookie headers', async () => {
  const p = makePartner({
    env: { GOOGLE_CLIENT_ID: 'test-client-id', GOOGLE_CLIENT_SECRET: 'test-client-secret' },
    fetch: async (url) => {
      const u = String(url);
      if (u.startsWith('https://oauth2.googleapis.com/token')) {
        return new Response(JSON.stringify({ access_token: 'atok' }), { headers: { 'content-type': 'application/json' } });
      }
      if (u.startsWith('https://www.googleapis.com/oauth2/v2/userinfo')) {
        return new Response(JSON.stringify({ email: 'owner@example.com', name: 'Owner' }), { headers: { 'content-type': 'application/json' } });
      }
    },
  });
  const res = await p.call('/auth/callback?code=abc&state=st123', {
    headers: { cookie: 'gcm_oauth_st=st123' },
  });
  assert.equal(res.status, 302);
  assert.equal(res.headers.get('location'), 'https://golfcartmap.test/partner');
  const cookies = res.headers.getSetCookie();
  assert.equal(cookies.length, 2);
  const session = cookies.find(c => c.startsWith('gcm_partner='));
  const clear = cookies.find(c => c.startsWith('gcm_oauth_st='));
  assert.ok(session, 'expected a gcm_partner Set-Cookie');
  assert.ok(clear, 'expected a gcm_oauth_st Set-Cookie');
  assert.match(session, /Max-Age=1209600/);
  assert.equal(/Max-Age=0/.test(session), false);
  assert.match(clear, /Max-Age=0/);
  assert.match(clear, /Path=\//);
  assert.match(clear, /HttpOnly/);
  assert.match(clear, /Secure/);
  assert.match(clear, /SameSite=Lax/);
});

test('Worker /auth/start 302s to accounts.google.com; /auth/google stays an alias', async () => {
  const p = makePartner({
    env: { GOOGLE_CLIENT_ID: 'test-client-id', GOOGLE_CLIENT_SECRET: 'test-client-secret' },
  });
  for (const path of ['/auth/start', '/auth/google']) {
    const res = await p.call(path);
    assert.equal(res.status, 302, path);
    const loc = res.headers.get('location');
    const url = new URL(loc);
    assert.equal(url.origin + url.pathname, 'https://accounts.google.com/o/oauth2/v2/auth');
    assert.equal(url.searchParams.get('client_id'), 'test-client-id');
    assert.equal(url.searchParams.get('redirect_uri'), 'https://golfcartmap.test/api/partner/auth/callback');
    assert.equal(url.searchParams.get('response_type'), 'code');
    assert.equal(url.searchParams.get('scope'), 'openid email profile');
    assert.equal(url.searchParams.get('access_type'), 'online');
    assert.equal(url.searchParams.get('prompt'), 'select_account');
    assert.ok(url.searchParams.get('state'));
    const cookie = res.headers.get('set-cookie') || '';
    assert.match(cookie, /gcm_oauth_st=/);
    assert.match(cookie, /Max-Age=600/);
    assert.match(cookie, /Path=\//);
    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /Secure/);
    assert.match(cookie, /SameSite=Lax/);
    const st = /gcm_oauth_st=([^;]+)/.exec(cookie)[1];
    assert.equal(url.searchParams.get('state'), st);
  }
});
