// node --test tests/analytics_rows.test.mjs
// gcm-analytics hit the Durable Object free limit (5M rows read/day) on Nov 19 2026: /stats re-ran the
// internal/test check (a 9-row json_each per event) over every stored event, 13 times per request.
// These tests pin the fix: same /stats and /shop-stats JSON as the old SQL, the check stored at ingest,
// and no statement that walks all stored events. Real billed rows: scripts/analytics_rows_read.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { computeStats } from '../lib/analytics_stats.js';
import { computeShopStats } from '../lib/shop_stats.js';
import { ensureSchema, insertEvent, purgeOld, signalVersion, SIGNAL_SQL } from '../lib/analytics_store.js';
import { computeStats as legacyStats } from './fixtures/analytics_stats_legacy.mjs';
import { computeShopStats as legacyShopStats } from './fixtures/shop_stats_legacy.mjs';
import { EXCLUDE_IIDS } from '../lib/analytics_exclude.js';

const NOW = Date.parse('2026-11-19T20:00:00Z');
const plain = v => JSON.parse(JSON.stringify(v));
const LEGACY_DDL = `CREATE TABLE events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT);
  CREATE INDEX ev_day ON events(day); CREATE INDEX ev_event_day ON events(event, day); CREATE INDEX ev_iid ON events(iid);`;

function store() {
  const db = new DatabaseSync(':memory:');
  const exec = (s, ...a) => { db.prepare(s).run(...a); };
  const q = (s, ...a) => db.prepare(s).all(...a);
  ensureSchema(exec, q);
  return { db, exec, q };
}
function legacy() {
  const db = new DatabaseSync(':memory:');
  db.exec(LEGACY_DDL);
  const ins = db.prepare('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)');
  return { db, q: (s, ...a) => db.prepare(s).all(...a), add: (r, ts) => ins.run(ts, new Date(ts).toISOString().slice(0, 10), r.event, r.town, r.platform, r.pwa, r.iid, r.sid, JSON.stringify(r.props)) };
}

// Deterministic mix: real installs, null iids, denylisted, props.internal, test UTMs in every field,
// look-alike words that must still count, partner events for two shops, 45 days of history.
const EVENTS = ['session', 'town_viewed', 'route_searched', 'route_completed', 'road_report_filed', 'partner_unlock', 'experience_started', 'experience_finished', 'affiliate_tap', 'map_open'];
const UTM = [undefined, 'flyer', 'e2e', 'testimonial', 'ci-nightly', 'city', 'Playwright', 'nextdoor', 'test', 'testing', 'tf'];
function synth(n) {
  let x = 12345;
  const rnd = k => { x = (Math.imul(x, 1103515245) + 12345) >>> 0; return (x >>> 8) % k; };
  const out = [];
  for (let i = 0; i < n; i++) {
    const event = EVENTS[rnd(EVENTS.length)];
    const props = {};
    const u = UTM[rnd(UTM.length * 4)];
    if (u) props[['utm_source', 'utm_medium', 'utm_campaign', 'ft_source', 'utm_term'][rnd(5)]] = u;
    if (rnd(60) === 0) props.internal = ['sim', 'tf', 'e2e'][rnd(3)];
    if (event === 'session') { props.new_install = rnd(3) === 0; if (rnd(2)) props.ref = 'google.com'; }
    if (event === 'route_searched') props.ok = rnd(2) === 0;
    if (/partner|experience|affiliate/.test(event)) { props.shop = rnd(3) ? 'beachmode' : 'other-shop'; props.code = 'c' + rnd(3); props.ride = 'r' + rnd(2); props.pin = 'p' + rnd(2); }
    const who = rnd(40);
    const iid = who === 0 ? null : who === 1 ? EXCLUDE_IIDS[0] : `iid-${String(rnd(300)).padStart(6, '0')}`;
    out.push({ ts: NOW - rnd(45 * 24) * 3600e3 - rnd(3600e3), r: { event, town: ['sd', 'myrtle', 'staug', null][rnd(4)], platform: ['web', 'ios', 'carplay'][rnd(3)], pwa: rnd(2), iid, sid: 'sess-' + i, props } });
  }
  return out;
}
function both(rows) {
  const a = store(), b = legacy();
  for (const { ts, r } of rows) { insertEvent(a.q, a.exec, r, ts); b.add(r, ts); }
  return { a, b };
}
const strip = s => { const c = plain(s); delete c.generated; return c; };

test('/stats is identical to the old read-time SQL for 1, 7, 30 and 400 days', () => {
  const { a, b } = both(synth(4000));
  for (const days of [1, 7, 30, 400]) {
    assert.deepEqual(strip(computeStats(a.q, days, NOW)), strip(legacyStats(b.q, days, NOW)), `days=${days}`);
  }
  const s = computeStats(a.q, 30, NOW);
  assert.ok(s.excluded.weekly_active > 0 && s.excluded.by_reason.length >= 2, 'fixture exercises the exclusion');
});

test('/stats with an extra denylisted install matches the old SQL', () => {
  const { a, b } = both(synth(1500));
  const extra = ['iid-000007', 'iid-000011'];
  assert.deepEqual(strip(computeStats(a.q, 7, NOW, { extraIids: extra })), strip(legacyStats(b.q, 7, NOW, { extraIids: extra })));
});

// The shop dashboard (weekly rows, stop opens, map opens, routes) and partner stops (opens, navs) add fields the old SQL never had.
// Every field the old SQL returned must still match it exactly; the new ones are pinned in shop_stats.test.mjs.
const DASH_TOTALS = ['opens', 'routes', 'experience_opens', 'stop_opens', 'place_opens', 'partner_navs'];
function oldShape(s) {
  const c = strip(s);
  delete c.weekly; delete c.stops; delete c.partner_stops;
  for (const k of DASH_TOTALS) delete c.totals[k];
  for (const r of c.rides || []) delete r.opened;
  return c;
}

test('/shop-stats is identical to the old SQL', () => {
  const { a, b } = both(synth(4000));
  for (const shop of ['beachmode', 'other-shop', 'no-such-shop']) for (const days of [7, 30]) {
    assert.deepEqual(oldShape(computeShopStats(a.q, { shop, days, now: NOW })), strip(legacyShopStats(b.q, { shop, days, now: NOW })), `${shop} ${days}`);
  }
});

test('the flag stored at ingest equals the old SQL check on every row', () => {
  const { a } = both(synth(3000));
  const want = a.q(`SELECT rowid AS rid FROM events WHERE ${SIGNAL_SQL} ORDER BY rowid`).map(r => r.rid);
  assert.ok(want.length > 50);
  assert.deepEqual(a.q('SELECT rid FROM internal_rows ORDER BY rid').map(r => r.rid), want);
  const flaggedIids = a.q(`SELECT DISTINCT iid FROM events WHERE iid IS NOT NULL AND ${SIGNAL_SQL} ORDER BY iid`).map(r => r.iid);
  assert.deepEqual(a.q('SELECT iid FROM excluded_iids ORDER BY iid').map(r => r.iid), flaggedIids);
  assert.deepEqual(ensureSchema(a.exec, a.q), { migrated: false, checked: 0 }, 'ingest kept flagged_through current; a wake rechecks nothing');
});

test('upgrading a pre-change store flags every event once and gives the same /stats', () => {
  const b = legacy();
  for (const { ts, r } of synth(2000)) b.add(r, ts);
  const before = strip(legacyStats(b.q, 30, NOW));
  const exec = (s, ...a) => { b.db.prepare(s).run(...a); };
  assert.deepEqual(ensureSchema(exec, b.q), { migrated: true, checked: 'all' });
  assert.deepEqual(strip(computeStats(b.q, 30, NOW)), before);
  assert.deepEqual(ensureSchema(exec, b.q), { migrated: false, checked: 0 }, 'second wake does not rescan');
  assert.equal(b.q(`SELECT v FROM meta WHERE k='signal'`)[0].v, signalVersion());
});

test('rollback-safe: events written by the old Worker (9-value INSERT) are flagged on the next wake', () => {
  const rows = synth(2400);
  const a = store(), b = legacy();
  const oldInsert = a.db.prepare('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)');   // master's Events.add
  rows.forEach(({ ts, r }, i) => {
    b.add(r, ts);
    if (i % 3) insertEvent(a.q, a.exec, r, ts);
    else oldInsert.run(ts, new Date(ts).toISOString().slice(0, 10), r.event, r.town, r.platform, r.pwa, r.iid, r.sid, JSON.stringify(r.props));
  });
  const wake = ensureSchema(a.exec, a.q);
  assert.equal(wake.migrated, false);
  assert.ok(wake.checked > 0);
  assert.deepEqual(strip(computeStats(a.q, 30, NOW)), strip(legacyStats(b.q, 30, NOW)));
});

test('a changed internal/test rule re-flags stored events on the next wake', () => {
  const { a } = both(synth(800));
  a.exec('DELETE FROM internal_rows');
  a.exec('DELETE FROM excluded_iids');
  a.exec(`UPDATE meta SET v='old-rule' WHERE k='signal'`);
  assert.deepEqual(ensureSchema(a.exec, a.q), { migrated: true, checked: 'all' });
  const want = a.q(`SELECT COUNT(*) n FROM events WHERE ${SIGNAL_SQL}`)[0].n;
  assert.equal(a.q('SELECT COUNT(*) n FROM internal_rows')[0].n, want);
});

function planOf(db, sql, params) {
  return db.prepare('EXPLAIN QUERY PLAN ' + sql).all(...params).map(r => r.detail);
}
function recorder(db) {
  const seen = [];
  const q = (s, ...a) => { seen.push({ sql: s, plan: planOf(db, s, a) }); return db.prepare(s).all(...a); };
  return { q, seen };
}

test('no /stats or /shop-stats statement walks every stored event or re-runs the internal check', () => {
  const { a } = both(synth(4000));
  a.db.exec('ANALYZE');
  for (const [name, run, count] of [
    ['/stats', q => computeStats(q, 30, NOW), 10],
    ['/shop-stats', q => computeShopStats(q, { shop: 'beachmode', days: 30, now: NOW }), 8],   // 5 + dashboard weekly and stops + partner stops
  ]) {
    const r = recorder(a.db);
    run(r.q);
    assert.equal(r.seen.length, count, `${name} statement count`);
    for (const { sql, plan } of r.seen) {
      const head = sql.replace(/\s+/g, ' ').slice(0, 120);
      assert.ok(!sql.includes('json_array('), `${name} re-runs the per-event internal check: ${head}`);
      for (const step of plan) {
        assert.ok(!/^SCAN events\b/.test(step), `${name} full scan (${step}): ${head}`);
        assert.ok(!/ANY\(event\)/.test(step), `${name} walks all of ev_event_day (${step}): ${head}`);
        assert.ok(!/USING INDEX ev_iid/.test(step), `${name} reads every event of an install (${step}): ${head}`);
      }
      assert.ok(plan.some(p => /SEARCH events USING (COVERING )?INDEX ev_(event_)?day/.test(p)), `${name} not bounded by day: ${head}`);
    }
  }
});

test('the old SQL did walk every stored event (what this change removes)', () => {
  const b = legacy();
  for (const { ts, r } of synth(500)) b.add(r, ts);
  const r = recorder(b.db);
  legacyStats(r.q, 7, NOW);
  assert.equal(r.seen.length, 13);
  // The excluded-install CTE: every event with an iid (ev_iid iid>?), json_each per row, in 11 of 13 statements.
  const walks = r.seen.filter(st => st.sql.includes('json_array(') && st.plan.some(p => /^SCAN events\b|ev_iid \(iid>\?\)/.test(p)));
  assert.equal(walks.length, 11);
});

test('purge drops events past 400 days by day and forgets installs only they excluded', () => {
  const a = store();
  const old = NOW - 401 * 864e5;
  insertEvent(a.q, a.exec, { event: 'session', town: 'sd', platform: 'web', pwa: 0, iid: 'iid-oldtest', sid: 'sess-1', props: { internal: 'sim' } }, old);
  insertEvent(a.q, a.exec, { event: 'session', town: 'sd', platform: 'web', pwa: 0, iid: 'iid-oldtest', sid: 'sess-2', props: {} }, NOW);
  insertEvent(a.q, a.exec, { event: 'session', town: 'sd', platform: 'web', pwa: 0, iid: 'iid-keeptest', sid: 'sess-3', props: { utm_source: 'e2e' } }, NOW);
  insertEvent(a.q, a.exec, { event: 'session', town: 'sd', platform: 'web', pwa: 0, iid: null, sid: 'sess-4', props: { utm_source: 'test' } }, old);
  assert.deepEqual(a.q('SELECT iid, internal FROM excluded_iids ORDER BY iid').map(plain), [{ iid: 'iid-keeptest', internal: 0 }, { iid: 'iid-oldtest', internal: 1 }]);
  assert.equal(a.q('SELECT COUNT(*) n FROM internal_rows')[0].n, 3);
  assert.equal(purgeOld(a.q, a.exec, NOW), 2);
  assert.deepEqual(a.q('SELECT iid FROM excluded_iids').map(r => r.iid), ['iid-keeptest']);
  assert.equal(a.q('SELECT COUNT(*) n FROM internal_rows')[0].n, 1, 'purged events leave internal_rows too');
  const plan = planOf(a.db, 'DELETE FROM events WHERE day < ?', ['2025-10-01']).join(' ');
  assert.match(plan, /ev_day/, 'purge uses the day index, not a full scan');
});

test('Worker: ingest flags once, purges once a day, caches /stats, logs store failures', () => {
  const src = readFileSync(new URL('../workers/analytics/src/index.js', import.meta.url), 'utf8');
  assert.match(src, /insertEvent\(/);
  assert.doesNotMatch(src, /ALTER TABLE events/, 'events keeps its columns so an older Worker can still insert');
  assert.match(src, /ensureSchema\(/);
  assert.doesNotMatch(src, /DELETE FROM events WHERE ts/, 'old purge read the whole table on 1% of events');
  assert.match(src, /purged_day/);
  assert.match(src, /STATS_TTL_MS = 5 \* 60 \* 1000/);
  assert.match(src, /console\.error\('gcm-analytics \/e: event not stored:/);
  assert.match(src, /return NC\(\);\n    \}/, 'POST /e still always answers 204');
});
