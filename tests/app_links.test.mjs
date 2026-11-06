// App links (Max t448u): AASA file + header, app-link helpers, handoff grant/token rules.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { grantExpiry, handoffProblem, GRANT_DAYS, HANDOFF_TTL } from '../lib/partner.js';
const require = createRequire(import.meta.url);
const AL = require('../public/applink.js');
const root = new URL('..', import.meta.url);
const read = p => readFileSync(new URL(p, root), 'utf8');

test('AASA is valid JSON for the app and covers shop links only', () => {
  const a = JSON.parse(read('public/.well-known/apple-app-site-association'));
  const d = a.applinks.details;
  assert.equal(d.length, 1);
  assert.deepEqual(d[0].appIDs, ['8AUV2FF925.com.matchimus.golfcartmaps']);
  const paths = d[0].components.map(c => c['/']);
  assert.deepEqual(paths, ['/p/*', '/map']);
  assert.deepEqual(d[0].components[1]['?'], { partner: '?*' }, 'plain /map stays on the web');
});

test('_headers serves the AASA as application/json and _redirects leaves it alone', () => {
  const h = read('public/_headers');
  const m = h.match(/^\/\.well-known\/apple-app-site-association\n((?:[ \t]+.+\n?)+)/m);
  assert.ok(m, 'header block present');
  assert.match(m[1], /Content-Type: application\/json/);
  assert.doesNotMatch(read('public/_redirects'), /well-known/);
});

test('slug comes from /p/<slug> on the web and ?slug= in the app', () => {
  assert.equal(AL.slugFrom('/p/BeachMode/go', '?code=AB12'), 'beachmode');
  assert.equal(AL.slugFrom('/p.html', '?slug=beach-mode&code=AB12'), 'beach-mode');
  assert.equal(AL.slugFrom('/p.html', '?slug=../x'), '');
  assert.equal(AL.slugFrom('/map', ''), '');
});

test('API base: relative on the web, golfcartmap.com in the app', () => {
  assert.equal(AL.apiBase({}), '/api/partner');
  const app = { Capacitor: { isNativePlatform: () => true } };
  assert.equal(AL.apiBase(app), 'https://golfcartmap.com/api/partner');
});

test('Open in the app button: iOS Safari only, never in the app or on desktop', () => {
  const nav = ua => ({ navigator: { userAgent: ua, maxTouchPoints: 5 } });
  assert.equal(AL.wantsAppButton(nav('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)')), true);
  assert.equal(AL.wantsAppButton({ navigator: { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)', maxTouchPoints: 0 } }), false);
  assert.equal(AL.wantsAppButton({ ...nav('iPhone'), Capacitor: { isNativePlatform: () => true } }), false);
  assert.equal(AL.handoffUrl('beach mode', 'a/b'), 'golfcartmaps://p/beach%20mode/go?handoff=a%2Fb');
});

test('grant lasts 14 days but never past the code expiry', () => {
  assert.equal(GRANT_DAYS, 14);
  assert.equal(grantExpiry(1000, 0), 1000 + 14 * 86400);
  assert.equal(grantExpiry(1000, 5000), 5000);
});

test('handoff token is single use and expires after 10 minutes', () => {
  assert.equal(HANDOFF_TTL, 600);
  const t = { shop_id: 's1', expires_at: 1000 + HANDOFF_TTL, used: 0 };
  assert.equal(handoffProblem(t, 1000, { shopId: 's1', single: true }), '');
  assert.equal(handoffProblem({ ...t, used: 1 }, 1000, { shopId: 's1', single: true }), 'already used');
  assert.equal(handoffProblem(t, 1000 + HANDOFF_TTL, { shopId: 's1', single: true }), 'expired');
  assert.equal(handoffProblem(t, 1000, { shopId: 'other', single: true }), 'not found');
  assert.equal(handoffProblem(null, 1000), 'not found');
});

test('worker: redeem marks the token used and never counts a code use', () => {
  const w = read('workers/partner/src/index.js');
  const redeem = w.slice(w.indexOf("parts[1] === 'redeem'"), w.indexOf("parts[1] === 'redeem'") + 900);
  assert.match(redeem, /single: true/);
  assert.match(redeem, /UPDATE handoffs SET used=1/);
  assert.doesNotMatch(redeem, /uses=uses\+1/);
  assert.match(w, /req\.method === 'POST' && .*handoff/, 'router forwards the handoff POST');
});

test('partner proxy allows any origin on /public/ (the app runs at capacitor://localhost)', () => {
  const p = read('functions/api/partner/[[path]].js');
  assert.match(p, /path\.startsWith\('\/public\/'\)[\s\S]{0,120}access-control-allow-origin', '\*'/);
});
