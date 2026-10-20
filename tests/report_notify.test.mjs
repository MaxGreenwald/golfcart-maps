import test from 'node:test'; import assert from 'node:assert/strict';
import { NOTIFY_TO, MIN_GAP_MS, isTest, nextSendAt, buildEmail, mapLink } from '../lib/report_notify.js';
const r = { id: 'a1', ts: Date.UTC(2026, 9, 20, 16, 5), issue: 'hazard', road: 'La Jolla Blvd', region: 'sd', lat: 32.825, lon: -117.27, speed: null, notes: 'Cones <b>here</b>' };
test('only ever to Max', () => assert.equal(NOTIFY_TO, 'max@golfcartmap.com'));
test('rate limit: 5 min gap', () => { const now = 1e12; assert.equal(nextSendAt(0, now), now); assert.equal(nextSendAt(now - 60000, now), now - 60000 + MIN_GAP_MS); assert.equal(nextSendAt(now - MIN_GAP_MS - 1, now), now) });
test('automated test reports never notify', () => { assert.ok(isTest({ notes: '[automated test] x' })); assert.ok(!isTest(r)) });
test('single email has type, map link, note (escaped), ET time, review step', () => {
  const m = buildEmail([r]); assert.match(m.subject, /^New road report: Hazard on La Jolla Blvd/);
  assert.ok(m.html.includes(mapLink(r)) && mapLink(r).startsWith('https://golfcartmap.com/?lat=32.825&lon=-117.27'));
  assert.ok(m.html.includes('Cones &lt;b&gt;here&lt;/b&gt;') && !m.html.includes('<b>here'));
  assert.match(m.html, /12:05 PM ET/); assert.match(m.html, /review_reports\.py list pending --prod/); assert.doesNotMatch(m.html, /\bfree\b/i) });
test('digest + preview tag', () => { const m = buildEmail([r, { ...r, id: 'b2' }], { prod: false, more: 3 }); assert.equal(m.subject, '[preview] 5 new road reports'); assert.match(m.html, /3 more/); assert.doesNotMatch(m.html, /--prod/) });
