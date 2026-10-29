// Faster-road stretches of SHORT_LEGAL_FT (75) or less are legal. Longer stretches
// stay risky. Adjacent faster pieces are summed first. Explicit bans are not waived.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const GCMRouter = require('../public/router.js');
const GCMRule = require('../public/roadrule.js');
const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

const LSV = { max_posted: 25, cross: true, veh: 'lsv' };

function metersOfFeet(ft) {
  const m = ft / 3.281;
  assert.equal(GCMRouter.shownFeet(m), ft, 'shown feet for ' + ft);
  return m;
}

function eastFrom(p, meters) {
  let lo = 0, hi = 0.05;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    const L = GCMRouter.len([p, [p[0] + mid, p[1]]]);
    if (L < meters) lo = mid; else hi = mid;
  }
  return [p[0] + (lo + hi) / 2, p[1]];
}

function bulge(a, b, meters) {
  let lo = 0, hi = 0.05;
  for (let i = 0; i < 60; i++) {
    const mid = (lo + hi) / 2;
    const w = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + mid];
    const L = GCMRouter.len([a, w, b]);
    if (L < meters) lo = mid; else hi = mid;
  }
  const w = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (lo + hi) / 2];
  return [a, w, b];
}

// pieces: {ft, mph, code, hw, flag}. Optional detourM adds a legal edge from the
// first node to the last, of about that length, so the router can avoid the chain.
function graph(pieces, rule, detourM) {
  const segs = [];
  let p = [-73.62, 41.02];
  pieces.forEach((pc, i) => {
    const q = eastFrom(p, metersOfFeet(pc.ft));
    const seg = [0, pc.hw || 'residential', pc.mph, pc.code || 't', 0, i, i + 1, [p, q]];
    if (pc.flag != null) seg.push(0, pc.flag);
    segs.push(seg);
    p = q;
  });
  if (detourM) {
    const a = segs[0][7][0], b = segs[segs.length - 1][7][1];
    segs.push([1, 'residential', rule.max_posted || 25, 't', 1, 0, pieces.length, bulge(a, b, detourM)]);
  }
  const D = { segs, meta: {} };
  const buckets = {};
  GCMRouter.bucketize(buckets, D.segs, 0);
  const net = GCMRouter.create();
  const cls = s => GCMRule.cls(s, rule);
  net.build(D, 0, { cls, unk: () => false, rule });
  pieces.forEach((pc, i) => assert.equal(GCMRouter.shownFeet(D.segs[i]._len), pc.ft, 'segment ' + i));
  return { D, net, cls, rule, buckets, end: pieces.length };
}

function routeEnds(g, risky) {
  return g.net.astar(0, g.end, { risky, rule: g.rule, riskyMax: GCMRouter.RISKY_MAX });
}

function stretchFeet(g, parts) {
  const mask = GCMRouter.riskyMask(g.D.segs, parts, g.rule, g.cls);
  const out = [];
  let cur = null;
  parts.forEach(([si], i) => {
    if (!mask[i]) { cur = null; return; }
    const L = g.D.segs[si]._len;
    if (!cur) { cur = { len: 0 }; out.push(cur); }
    cur.len += L;
  });
  return out.map(s => GCMRouter.shownFeet(s.len));
}

function uses(parts, si) { return !!parts && parts.some(([i]) => i === si); }

test('shown feet matches the route summary rounding', () => {
  assert.equal(GCMRouter.SHORT_LEGAL_FT, 75);
  assert.equal(GCMRouter.shownFeet(75 / 3.281), 75);
  assert.equal(GCMRouter.shownFeet(76 / 3.281), 76);
  const router = fs.readFileSync(path.join(ROOT, 'public/router.js'), 'utf8');
  const app = fs.readFileSync(path.join(ROOT, 'public/app.js'), 'utf8');
  const car = fs.readFileSync(path.join(ROOT, 'public/carplay.js'), 'utf8');
  assert.equal((router.match(/SHORT_LEGAL_FT = 75/g) || []).length, 1);
  assert.doesNotMatch(app, /SHORT_LEGAL_FT\s*=/);
  assert.doesNotMatch(car, /SHORT_LEGAL_FT\s*=/);
  assert.match(app, /riskyMask/);
});

test('a 75 ft faster stretch is legal and a 76 ft stretch stays risky', () => {
  const ok = graph([
    { ft: 100, mph: 25, code: 't' },
    { ft: 75, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 100, mph: 25, code: 't' },
  ], LSV);
  const parts = routeEnds(ok, false);
  assert.ok(parts && parts.length, 'legal mode uses a 75 ft faster stretch');
  assert.equal(uses(parts, 1), true);
  assert.deepEqual(stretchFeet(ok, parts), []);
  assert.deepEqual(stretchFeet(ok, routeEnds(ok, true)), []);

  const over = graph([
    { ft: 100, mph: 25, code: 't' },
    { ft: 76, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 100, mph: 25, code: 't' },
  ], LSV);
  assert.equal(routeEnds(over, false), null, 'legal mode refuses a 76 ft faster stretch');
  const risky = routeEnds(over, true);
  assert.ok(risky && uses(risky, 1));
  assert.deepEqual(stretchFeet(over, risky), [76]);
});

test('75 ft is priced as a normal edge, so legal mode prefers it to a detour', () => {
  // Penalty on 75 ft is about 6×length+60 ≈ 197, plus the approaches. A detour
  // between the legal-edge cost and that penalty is taken only if the waiver is missing.
  const g = graph([
    { ft: 80, mph: 25, code: 't' },
    { ft: 75, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 80, mph: 25, code: 't' },
  ], LSV, 150);
  const parts = routeEnds(g, false);
  assert.ok(parts);
  assert.equal(uses(parts, 1), true, 'legal mode takes the 75 ft stretch instead of the detour');
  assert.deepEqual(stretchFeet(g, parts), []);
});

test('adjacent faster pieces merge before the 75 ft cutoff', () => {
  // 25+25+25 = 75, legal. 25+25+26 = 76, one risky stretch. Judged one segment
  // at a time, the 26 ft piece would also be waived.
  const under = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 25, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 25, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 25, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  const u = routeEnds(under, false);
  assert.ok(u);
  assert.equal(uses(u, 1) && uses(u, 2) && uses(u, 3), true);
  assert.deepEqual(stretchFeet(under, u), []);

  const over = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 25, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 25, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 26, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 40, mph: 25, code: 't' },
  ], LSV, 400);
  const avoided = routeEnds(over, false);
  assert.ok(avoided, 'a legal detour still exists');
  assert.equal(uses(avoided, 1), false, 'legal mode does not split a 76 ft run into waived pieces');
  const r = routeEnds(over, true);
  assert.ok(uses(r, 1) && uses(r, 2) && uses(r, 3));
  assert.deepEqual(stretchFeet(over, r), [76]);

  // A legal segment between two short faster pieces keeps them separate.
  const split = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 30, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 40, mph: 25, code: 't' },
    { ft: 30, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  const s = routeEnds(split, false);
  assert.ok(s);
  assert.deepEqual(stretchFeet(split, s), []);
});

test('explicit bans stay risky under 75 ft', () => {
  const ban = (extra, rule) => graph([
    { ft: 40, mph: 25, code: 't' },
    extra,
    { ft: 40, mph: 25, code: 't' },
  ], rule, 200);

  const named = ban({ ft: 30, mph: 99, code: 'v', hw: 'primary', flag: 1 }, LSV);
  assert.equal(GCMRouter.explicitBan(named.D.segs[1], LSV), true);
  assert.equal(uses(routeEnds(named, false), 1), false);
  const namedR = routeEnds(named, true);
  assert.ok(uses(namedR, 1));
  assert.deepEqual(stretchFeet(named, namedR), [30]);

  const only = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 20, mph: 99, code: 'v', hw: 'motorway', flag: 1 },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  assert.equal(routeEnds(only, false), null, 'legal mode has no way through a short banned road');

  const cartRule = { max_posted: 35, cross: true, veh: 'golf_cart' };
  const fort = ban({ ft: 20, mph: 25, code: 't', hw: 'residential', flag: 4 }, cartRule);
  assert.equal(GCMRouter.explicitBan(fort.D.segs[1], cartRule), true);
  assert.equal(uses(routeEnds(fort, false), 1), false);
  const lsvOk = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 20, mph: 25, code: 't', hw: 'residential', flag: 4 },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  assert.equal(GCMRule.cls(lsvOk.D.segs[1], LSV), 0, 'flag 4 does not ban LSVs');
  assert.equal(uses(routeEnds(lsvOk, false), 1), true);

  const desig = { max_posted: 25, cross: true, veh: 'golf_cart', designated_only: true };
  const side = graph([
    { ft: 40, mph: 25, code: 'd' },
    { ft: 30, mph: 25, code: 'i', hw: 'residential' },
    { ft: 40, mph: 25, code: 'd' },
  ], desig);
  assert.equal(GCMRouter.explicitBan(side.D.segs[1], desig), true);
  assert.equal(routeEnds(side, false), null, 'a short undesignated street is not waived');

  const notLegal = { not_street_legal: true, max_posted: 0, cross: false, veh: 'golf_cart' };
  const plain = graph([
    { ft: 30, mph: 25, code: 't', hw: 'residential' },
  ], notLegal);
  assert.equal(GCMRouter.explicitBan(plain.D.segs[0], notLegal), true);
  assert.equal(routeEnds(plain, false), null);
});

test('a U-turn cannot split one faster stretch into two legal pieces', () => {
  const g = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 50, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 50, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  const at = g.D.segs[1][7][1];
  g.D.segs.push([2, 'residential', 25, 't', 0, 2, 9, [at, eastFrom(at, metersOfFeet(40))]]);
  const net = GCMRouter.create();
  net.build(g.D, 0, { cls: g.cls, unk: () => false, rule: g.rule });
  g.net = net;
  assert.equal(routeEnds(g, false), null, 'legal mode still sees one 100 ft stretch');
  const r = routeEnds(g, true);
  assert.ok(r);
  assert.equal(uses(r, 4), false, 'risky mode does not detour up the side street');
  assert.deepEqual(stretchFeet(g, r), [100]);
});

test('a short faster piece beside a ban is waived and the ban is not', () => {
  const g = graph([
    { ft: 40, mph: 25, code: 't' },
    { ft: 30, mph: 99, code: 'i', hw: 'secondary' },
    { ft: 30, mph: 99, code: 'v', hw: 'primary', flag: 1 },
    { ft: 40, mph: 25, code: 't' },
  ], LSV);
  assert.equal(routeEnds(g, false), null);
  const r = routeEnds(g, true);
  assert.ok(r);
  const mask = GCMRouter.riskyMask(g.D.segs, r, g.rule, g.cls);
  const bySi = Object.fromEntries(r.map(([si], i) => [si, mask[i]]));
  assert.equal(bySi[1], false, '30 ft faster piece is legal');
  assert.equal(bySi[2], true, '30 ft ban stays risky');
  assert.deepEqual(stretchFeet(g, r), [30]);
});

test('Greenwich screenshot route drops the 37 ft jog and keeps 242 and 92', { timeout: 30000 }, () => {
  // Live pins from the screenshot (dropped pin labels, 4 decimals): 41.0156,-73.644 → 41.0339,-73.628.
  // Risky stretches before this change: 37 ft West Putnam Ave, 242 ft Glenville Rd (116+90+36), 92 ft Lake Ave.
  const index = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/greenwich/index.json'), 'utf8'));
  const rules = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/rules.json'), 'utf8'));
  const regions = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/regions.json'), 'utf8'));
  const region = regions.find(r => r.id === 'greenwich');
  const rule = GCMRule.ruleFor(rules, region, 'lsv');
  const D = { meta: index.meta, segs: [], names: index.names };
  for (const k of index.meta.tiles) {
    D.segs.push(...JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/greenwich/tiles', k + '.json'), 'utf8')));
  }
  const cls = s => GCMRule.cls(s, rule);
  const unk = s => s[3] === 'i' && /^(secondary|tertiary|unclassified)/.test(s[1]) && cls(s) !== 3;
  const buckets = {};
  GCMRouter.bucketize(buckets, D.segs, 0);
  const net = GCMRouter.create();
  net.build(D, 0, { cls, unk, rule });
  const near = { cls, G: GCMRouter.G };
  const A = net.nearest(D, buckets, { lat: 41.0156, lng: -73.644 }, near);
  const B = net.nearest(D, buckets, { lat: 41.0339, lng: -73.628 }, near);
  const parts = net.astar(A[0], B[0], { risky: true, rule, riskyMax: GCMRouter.RISKY_MAX });
  assert.ok(parts && parts.length);
  const mask = GCMRouter.riskyMask(D.segs, parts, rule, cls);
  const stretches = [];
  let cur = null;
  parts.forEach(([si], i) => {
    const s = D.segs[si];
    if (!mask[i]) { cur = null; return; }
    if (!cur) { cur = { len: 0, name: D.names[s[0]] }; stretches.push(cur); }
    cur.len += s._len;
  });
  const got = stretches.map(s => [GCMRouter.shownFeet(s.len), s.name]);
  assert.deepEqual(got, [[242, 'Glenville Road'], [92, 'Lake Avenue']]);
  const putnam = parts.filter(([si]) => D.names[D.segs[si][0]] === 'West Putnam Avenue' && cls(D.segs[si]) === 3);
  assert.equal(putnam.length, 1);
  assert.equal(GCMRouter.shownFeet(D.segs[putnam[0][0]]._len), 37);
  assert.equal(GCMRouter.explicitBan(D.segs[putnam[0][0]], rule), false);
  assert.equal(mask[parts.findIndex(([si]) => si === putnam[0][0])], false);

  const banned = D.segs.filter(s => D.names[s[0]] === 'I 95');
  assert.ok(banned.length > 0);
  banned.forEach(s => assert.equal(GCMRouter.explicitBan(s, rule), true));
});
