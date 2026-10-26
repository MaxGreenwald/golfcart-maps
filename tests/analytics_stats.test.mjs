// node --test tests/analytics_stats.test.mjs
// Fails if denylisted installs, simulator / internal TestFlight, webdriver/e2e, or test UTMs
// would count as weekly active installs or route users. Same SQL as the Worker's /stats.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { computeStats } from '../lib/analytics_stats.js';
import { EXCLUDE_IIDS, utmIsExcluded, rowIsInternalSql, internalChannel, cleanInternal } from '../lib/analytics_exclude.js';

const NOW = Date.parse('2026-10-26T12:00:00Z');
const DAY = '2026-10-25';
const OLD = '2026-01-01';
const REAL = '11111111-1111-4111-8111-111111111111';
const E2E = '22222222-2222-4222-8222-222222222222';
const DENY = '33333333-3333-4333-8333-333333333333';
const SIM = '44444444-4444-4444-8444-444444444444';
const TF = '55555555-5555-4555-8555-555555555555';
const MIXED = '66666666-6666-4666-8666-666666666666';
const LATER = '77777777-7777-4777-8777-777777777777';

function dbWith(rows) {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT)`);
  const ins = db.prepare('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)');
  for (const r of rows) ins.run(r.ts || NOW, r.day || DAY, r.event, r.town ?? 'sd', r.platform || 'web', r.pwa || 0, r.iid ?? null, r.sid || 'sess-aaaaaaaa', JSON.stringify(r.props || {}));
  return db;
}
function qOf(db) {
  return (sql, ...params) => db.prepare(sql).all(...params);
}
function fixture() {
  return dbWith([
    { iid: REAL, event: 'session', props: { new_install: true, ft_source: 'direct' } },
    { iid: REAL, event: 'town_viewed', props: { how: 'picker' } },
    { iid: REAL, event: 'route_searched', props: { ok: true, mi: 2.5 } },
    { iid: E2E, event: 'session', props: { utm_source: 'e2e', utm_medium: 'ci', new_install: true } },
    { iid: E2E, event: 'route_searched', props: { ok: true } },
    { iid: DENY, event: 'session', props: { new_install: true, ft_source: 'app' } },
    { iid: DENY, event: 'route_searched', platform: 'ios', props: { ok: true } },
    { iid: SIM, event: 'session', platform: 'carplay', props: { internal: 'sim', new_install: true } },
    { iid: SIM, event: 'route_started', platform: 'carplay', props: { internal: 'sim' } },
    { iid: SIM, event: 'route_searched', platform: 'carplay', props: { ok: true, internal: 'sim' } },
    { iid: TF, event: 'session', platform: 'ios', props: { internal: 'tf', new_install: true } },
    { iid: MIXED, event: 'session', props: { new_install: true } },
    { iid: MIXED, event: 'route_searched', props: { ok: true, utm_source: 'playwright' } },
    { iid: LATER, event: 'session', day: OLD, props: { internal: 'sim' } },
    { iid: LATER, event: 'session', props: { new_install: false, ft_source: 'direct' } },
    { iid: null, event: 'session', props: { utm_source: 'test', utm_campaign: 'e2e-nightly' } },
    { iid: '88888888-8888-4888-8888-888888888888', event: 'session', props: { utm_source: 'flyer', ft_source: 'flyer', new_install: true } },
  ]);
}

test('excluded traffic does not count as weekly active installs or route users', () => {
  const s = computeStats(qOf(fixture()), 7, NOW, { extraIids: [DENY] });
  assert.equal(s.weekly_active, 2, 'real user + flyer');
  assert.equal(s.weekly_active_route_users, 1);
  assert.equal(s.weekly_active_unfiltered, 8);
  assert.equal(s.weekly_active_route_users_unfiltered, 5);
  assert.equal(s.excluded.weekly_active, 6);
  assert.equal(s.excluded.weekly_active_route_users, 4);
  assert.equal(s.totals.installs, 2);
  assert.equal(s.totals.sessions, 2);
  assert.equal(s.towns[0].installs, 2);
  assert.equal(s.towns[0].routes_searched, 1);
  const platforms = Object.fromEntries(s.platforms.map(p => [p.platform, p.installs]));
  assert.equal(platforms.web, 2);
  assert.equal(platforms.ios, undefined);
  assert.equal(platforms.carplay, undefined);
  const reasons = Object.fromEntries(s.excluded.by_reason.map(r => [r.reason, r.installs]));
  assert.equal(reasons.iid, 1);
  assert.equal(reasons.internal, 3);
  assert.equal(reasons.utm, 2);
});

test('EXCLUDE_IIDS in lib/analytics_exclude.js is what /stats applies', () => {
  EXCLUDE_IIDS.push(DENY);
  try {
    const s = computeStats(qOf(fixture()), 7, NOW);
    assert.equal(s.weekly_active_route_users, 1);
    assert.ok(s.excluded.by_reason.some(r => r.reason === 'iid' && r.installs === 1));
  } finally {
    const i = EXCLUDE_IIDS.indexOf(DENY);
    if (i >= 0) EXCLUDE_IIDS.splice(i, 1);
  }
});

test('utm predicate matches the SQL /stats uses, including words that must still count', () => {
  const samples = ['e2e', 'E2E', 'test', 'test_run', 'test-ci', 'test.nightly', 'testing', 'testimonial', 'ci', 'ci-1', 'city',
    'playwright', 'playwright-chromium', 'simulator', 'nextdoor', 'flyer', 'app', 'direct', 'ref_www.google.com', 'internal',
    'notrack', 'no_track', 'tf', 'sim', 'testflight', 'e2e_local'];
  const db = new DatabaseSync(':memory:');
  db.exec('CREATE TABLE events(props TEXT)');
  const ins = db.prepare('INSERT INTO events VALUES (?)');
  const hit = db.prepare(`SELECT ${rowIsInternalSql('props')} AS hit FROM events`);
  for (const s of samples) {
    db.exec('DELETE FROM events');
    ins.run(JSON.stringify({ utm_source: s }));
    assert.equal(!!hit.get().hit, utmIsExcluded(s), `utm_source ${s}`);
    db.exec('DELETE FROM events');
    ins.run(JSON.stringify({ ft_source: s }));
    assert.equal(!!hit.get().hit, utmIsExcluded(s), `ft_source ${s}`);
  }
  db.exec('DELETE FROM events');
  ins.run(JSON.stringify({ utm_source: 'nextdoor', internal: 'sim' }));
  assert.equal(hit.get().hit, 1);
  db.exec('DELETE FROM events');
  ins.run(JSON.stringify({ utm_source: 'flyer', ft_source: 'ref_www.google.com' }));
  assert.equal(hit.get().hit, 0);
});

test('client channel: simulator, internal TF, webdriver, test utm; real UTMs stay', () => {
  assert.equal(internalChannel({ gcmInternal: 'simulator' }), 'sim');
  assert.equal(internalChannel({ gcmInternal: 'testflight' }), 'tf');
  assert.equal(internalChannel({ stored: 'debug' }), 'debug');
  assert.equal(internalChannel({ build: '__GCM_ANALYTICS_INTERNAL__' }), null);
  assert.equal(internalChannel({ build: 'sim' }), 'sim');
  assert.equal(internalChannel({ webdriver: true }), 'e2e');
  assert.equal(internalChannel({ search: { utm_source: 'e2e', utm_medium: 'ci' } }), 'e2e');
  assert.equal(internalChannel({ search: { utm_source: 'nextdoor', utm_campaign: 'dm1018' } }), null);
  assert.equal(internalChannel({ search: { utm_source: 'flyer' } }), null);
  assert.equal(internalChannel({ search: { ft_source: 'app' } }), null);
  assert.equal(cleanInternal('no_track'), 'notrack');
  assert.equal(cleanInternal('Max'), null);
});

test('track.js does not beacon internal traffic and keeps the build stamp token', () => {
  const src = readFileSync(new URL('../public/track.js', import.meta.url), 'utf8');
  assert.match(src, /__GCM_ANALYTICS_INTERNAL__/);
  assert.match(src, /navigator\.webdriver/);
  assert.match(src, /GCM_INTERNAL/);
  assert.match(src, /gcm-internal/);
  assert.match(src, /if \(W\.GCM_TRACK_SINK\)[\s\S]{0,200}return[\s\S]{0,120}if \(o\.internal\) return/);
  const worker = readFileSync(new URL('../workers/analytics/src/index.js', import.meta.url), 'utf8');
  assert.match(worker, /computeStats/);
});
