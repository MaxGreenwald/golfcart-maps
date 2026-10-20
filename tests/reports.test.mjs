// node --test tests/reports.test.mjs — report queue rules (lib/reports.js), /api/report proxy and the top-of-pyramid guard:
// reports can never change legality data, and routing only avoids reviewed, temporary closures/hazards.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { sanitizeReport, queued, review, activeAvoids, ISSUES, AVOIDABLE, MAX_AVOID_DAYS } from '../lib/reports.js';
import { queueFor, onRequestPost, onRequestGet } from '../functions/api/report.js';
const good = { issue: 'closed', lat: 32.80123456, lon: -117.25, region: 'sd', road: 'Grand Ave', notes: 'Fenced off for sewer work', app: 'mr-2026.10.13' };
const H = 3600000, D = 24 * H, now = 1_790_000_000_000;

test('sanitize: keeps only the schema, strips contact details', () => {
  const r = sanitizeReport({ ...good, speed: '25', email: 'a@b.com', iid: 'x', ip: '1.2.3.4', max_posted: 99, cls: 0,
    notes: 'call me 303-555-1212 or max@example.com, the road is closed' });
  assert.deepEqual(Object.keys(r).sort(), ['app', 'issue', 'lat', 'lon', 'notes', 'region', 'road', 'speed']);
  assert.equal(r.lat, 32.80123); assert.equal(r.speed, 25);
  assert.ok(!/303|example\.com/.test(r.notes), r.notes);
  assert.equal(sanitizeReport({ ...good, issue: 'set_speed_99' }), null);
  assert.equal(sanitizeReport({ ...good, lat: 'x' }), null);
  assert.equal(sanitizeReport({ ...good, speed: 500 }).speed, null);
  assert.equal(sanitizeReport({ ...good, region: '../etc' }).region, null);
  assert.equal(sanitizeReport({ ...good, notes: 'x'.repeat(2000) }).notes.length, 500);
});

test('new reports are pending and inactive', () => {
  const q = queued(sanitizeReport(good), now, 'a1');
  assert.equal(q.status, 'pending'); assert.equal(q.avoid_until, null);
  assert.deepEqual(activeAvoids([q], now), []);
});

test('review: only reviewed, accepted closures/hazards with a short expiry become avoids', () => {
  const q = queued(sanitizeReport(good), now, 'a1');
  const ok = review(q, { status: 'accepted', avoid_days: 3 }, now);
  assert.equal(activeAvoids([ok], now + D).length, 1);
  assert.equal(activeAvoids([ok], now + 4 * D).length, 0);                       // expires
  assert.equal(activeAvoids([review(q, { status: 'accepted' }, now)], now).length, 0);   // accepted but no avoid
  assert.equal(activeAvoids([review(q, { status: 'rejected' }, now)], now).length, 0);
  assert.throws(() => review(q, { status: 'rejected', avoid_days: 2 }, now));
  assert.throws(() => review(q, { status: 'accepted', avoid_days: MAX_AVOID_DAYS + 1 }, now));
  assert.throws(() => review(q, { status: 'live' }, now));
  for (const issue of ISSUES.filter(i => !AVOIDABLE.includes(i))) {             // wrong speed / allow / block never steer routing
    const w = queued(sanitizeReport({ ...good, issue, speed: 15 }), now, 'w');
    assert.throws(() => review(w, { status: 'accepted', avoid_days: 1 }, now));
    assert.deepEqual(activeAvoids([{ ...review(w, { status: 'accepted' }, now), avoid_until: now + D }], now), []);  // even if a row is tampered with
  }
  // a tampered row (never reviewed) is ignored
  assert.deepEqual(activeAvoids([{ ...q, status: 'accepted', avoid_until: now + D }], now), []);
  // review never edits the report's facts
  const r2 = review(q, { status: 'accepted', avoid_days: 1, issue: 'allow', lat: 0, speed: 99 }, now);
  assert.equal(r2.issue, 'closed'); assert.equal(r2.lat, q.lat); assert.equal(r2.speed, q.speed);
});

test('active avoid output carries no legality fields', () => {
  const a = activeAvoids([review(queued(sanitizeReport({ ...good, issue: 'hazard', speed: 10 }), now, 'h'), { status: 'accepted', avoid_days: 1 }, now)], now)[0];
  assert.deepEqual(Object.keys(a).sort(), ['id', 'issue', 'lat', 'lon', 'road', 'until']);
});

test('guard: no data build script, rules file or roadrule.js reads the report queue', () => {
  const files = [...readdirSync('scripts').filter(f => /^(build_|overrides|islands|heal_tiles|fetch_dot|mapillary|accuracy)/.test(f)).map(f => 'scripts/' + f), 'public/roadrule.js', 'public/data/rules.json', 'public/data/regions.json'];
  for (const f of files) { const s = readFileSync(f, 'utf8'); assert.ok(!/gcm-reports|api\/report|lib\/reports|reports\.js|AVOIDS/.test(s), f) }
});

test('guard: app.js uses reports only as a routing cost, never in cls()/popup legality', () => {
  const s = readFileSync('public/app.js', 'utf8');
  const cls = s.match(/const cls=s=>[^\n]*/)[0]; assert.ok(!/avoid|AVOIDS|report/i.test(cls));
  assert.ok(/if\(AVOIDS\.length&&avoided\(D\.segs\[si\]\)\)cost=w\*AVOID_W;/.test(s));   // weight only, no `continue`/forbidden
  assert.ok(!/AVOIDS[^\n]{0,80}fnode\.add/.test(s));
});

test('/api/report proxy: host routing, cleans before forwarding, falls back cleanly', async () => {
  assert.match(queueFor('golfcartmap.com', {}), /gcm-reports\./); assert.match(queueFor('feat-reports.golfcart-maps.pages.dev', {}), /gcm-reports-preview\./);
  let sent = null; const of = globalThis.fetch;
  globalThis.fetch = async (u, o) => { sent = { u, b: JSON.parse(o.body) }; return new Response(JSON.stringify({ id: 'z1', status: 'pending' }), { status: 202 }) };
  const req = b => new Request('https://feat-reports.golfcart-maps.pages.dev/api/report', { method: 'POST', body: JSON.stringify(b), headers: { 'x-forwarded-for': '1.2.3.4' } });
  let r = await onRequestPost({ request: req({ ...good, email: 'x@y.z' }), env: {} }); assert.equal(r.status, 202);
  assert.equal((await r.json()).status, 'pending'); assert.ok(!('email' in sent.b)); assert.match(sent.u, /preview.*\/r$/);
  r = await onRequestPost({ request: req({ issue: 'nope' }), env: {} }); assert.equal(r.status, 400);
  globalThis.fetch = async () => { throw new Error('down') };
  r = await onRequestPost({ request: req(good), env: {} }); assert.equal(r.status, 502);
  r = await onRequestGet({ request: new Request('https://x.pages.dev/api/report'), env: {} }); assert.deepEqual(await r.json(), []);
  globalThis.fetch = of;
});
