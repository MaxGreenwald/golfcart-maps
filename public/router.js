// Shared road router for the map (public/app.js) and renter pages (public/p.js).
// This is the map's snap + A* (legal roads; risky runs only when the caller asks).
// Experience lines call it so stop-to-stop connectors follow the road graph
// instead of a straight chord that can cut across water.
(function (root) {
  const G = 0.02;
  const RISKY_MAX = 152.4; // 500 ft, same cap as the map
  // Faster-road stretches that round to this many feet (or fewer) are legal.
  // One constant: the map, renter routes, and CarPlay/iOS (via app.js) all use this file.
  // shownFeet matches the route summary (app.js ft → shownFeet), so "75 ft" on screen is the cutoff.
  const SHORT_LEGAL_FT = 75;
  const UNKW = 1.8;
  // A miss longer than this is omitted. A short gap may be a dashed stub.
  // Anything longer would be the chord Max saw crossing the La Jolla water.
  const GAP_MAX_M = 70;

  function hav(a, b) {
    const R = 6371000, r = Math.PI / 180;
    const dlat = (b[1] - a[1]) * r, dlon = (b[0] - a[0]) * r;
    const x = Math.sin(dlat / 2) ** 2 + Math.cos(a[1] * r) * Math.cos(b[1] * r) * Math.sin(dlon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  function len(p) {
    let l = 0;
    for (let i = 1; i < p.length; i++) l += hav(p[i - 1], p[i]);
    return l;
  }
  function shownFeet(m) { return Math.round(m * 3.281); }

  // True when a forbidden segment is an explicit ban, not merely a faster road.
  // The 75 ft waiver does not apply: Fort Myers-style cart bans (flag 4), named /
  // posted bans (flag 1, including I-95 / Merritt stored as speed 99 code 'v'),
  // enforcement bars, undesignated roads in a designated-only town, and vehicles
  // that are not street-legal. Inferred-high majors (speed 99, code 'i') are the
  // faster-road class and DO get the waiver.
  function explicitBan(s, rule) {
    if (!rule || s[3] === 'c') return false;
    if (rule.not_street_legal) return true;
    if (s[9] === 1) return true;
    if (s[9] === 4 && rule.veh === 'golf_cart') return true;
    if (s[2] === 99 && (s[3] === 'v' || s[3] === 'r' || s[3] === 'k')) return true;
    if (rule.designated_only) {
      const speedOver = s[2] == null || s[2] > rule.max_posted;
      if (!speedOver) return true;
    }
    return false;
  }

  // Which parts of a route are still risky stretches. Adjacent faster-road
  // segments are summed before SHORT_LEGAL_FT is applied: a 36 ft piece glued
  // to 90 ft and 116 ft is one 242 ft stretch and stays risky. An explicit ban
  // breaks that run and is never waived, at any length.
  function riskyMask(segs, parts, rule, clsFn) {
    const mask = new Array(parts.length).fill(false);
    let start = -1, acc = 0, hard = false;
    const flush = (end) => {
      if (start < 0) return;
      if (hard || shownFeet(acc) > SHORT_LEGAL_FT) {
        for (let k = start; k < end; k++) mask[k] = true;
      }
      start = -1; acc = 0; hard = false;
    };
    for (let i = 0; i < parts.length; i++) {
      const s = segs[parts[i][0]];
      const forbidden = clsFn(s) === 3;
      const isHard = forbidden && explicitBan(s, rule);
      if (!forbidden) { flush(i); continue; }
      if (start >= 0 && isHard !== hard) flush(i);
      if (start < 0) { start = i; hard = isHard; acc = 0; }
      acc += s._len != null ? s._len : len(s[7]);
    }
    flush(parts.length);
    return mask;
  }

  function create() {
    let nodes = {}, adj = {}, fast = new Set(), fnode = new Set(), cnode = new Set();
    function reset() {
      nodes = {}; adj = {}; fast = new Set(); fnode = new Set(); cnode = new Set();
    }
    // Same edge build as app.js buildGraph. `from` is the first new segment index.
    function build(D, from, o) {
      const cls = o.cls, unk = o.unk || (() => false), rule = o.rule;
      if (D.meta && D.meta.xnodes) D.meta.xnodes.forEach(n => cnode.add(n));
      D.segs.slice(from).forEach((s, j) => {
        const i = from + j;
        const c = cls(s), a = s[5], b = s[6], p = s[7];
        s._len ??= len(p);
        nodes[a] = p[0];
        nodes[b] = p[p.length - 1];
        if ((s[3] === 't' || s[3] === 'o' || s[3] === 'm') && s[2] > rule.max_posted) { fast.add(a); fast.add(b); }
        if (c === 3) { fnode.add(a); fnode.add(b); }
        if (s[3] === 'c') { cnode.add(a); cnode.add(b); }
        // kind: 0 legal, 1 faster-road (75 ft waiver can apply), 2 explicit ban (never waived)
        const kind = c !== 3 ? 0 : explicitBan(s, rule) ? 2 : 1;
        const wmul = (unk(s) || s[3] === 'q') ? UNKW : 1;
        const geo = s._len;
        if (s[4] >= 0) (adj[a] || (adj[a] = [])).push([b, s._len * wmul, i, false, kind, geo]);
        if (s[4] <= 0) (adj[b] || (adj[b] = [])).push([a, s._len * wmul, i, true, kind, geo]);
      });
    }
    // Snap to the nearest allowed segment. Returns [node, meters, otherNode], same as app.js nearest.
    function nearest(D, buckets, ll, o) {
      const cls = o.cls, Gv = o.G || G;
      const q = [ll.lng, ll.lat], kx = Math.cos(ll.lat * Math.PI / 180);
      let best = null, bd = 1e18;
      const bx = Math.floor(q[0] / Gv), by = Math.floor(q[1] / Gv);
      const cand = [];
      for (let x = bx - 1; x <= bx + 1; x++)
        for (let y = by - 1; y <= by + 1; y++)
          (buckets[x + ',' + y] || []).forEach(i => cand.push(i));
      for (const i of cand) {
        const s = D.segs[i];
        if (cls(s) === 3) continue;
        const p = s[7];
        for (let j = 1; j < p.length; j++) {
          const ax = (p[j - 1][0] - q[0]) * kx, ay = p[j - 1][1] - q[1];
          const bx_ = (p[j][0] - q[0]) * kx, by_ = p[j][1] - q[1];
          const dx = bx_ - ax, dy = by_ - ay, L2 = dx * dx + dy * dy;
          let t = L2 ? -(ax * dx + ay * dy) / L2 : 0;
          t = Math.max(0, Math.min(1, t));
          const ex = ax + t * dx, ey = ay + t * dy, d = ex * ex + ey * ey;
          if (d < bd) {
            bd = d;
            const da = hav(q, p[0]), db = hav(q, p[p.length - 1]);
            best = [da <= db ? s[5] : s[6], da <= db ? s[6] : s[5]];
          }
        }
      }
      if (!best) return [null, 1e9];
      return [best[0], Math.sqrt(bd) * 111320, best[1]];
    }
    // A* over (node, risky-run metres, faster-run length). A faster-road run at or
    // under SHORT_LEGAL_FT is a normal edge, including in Legal-only mode. Crossing
    // 75 ft restores today's 6×+60 penalty for the whole run (so a longer stretch
    // does not get a cheap prefix). Explicit bans stay on the old rule.
    function astar(s, t, o) {
      const rule = o.rule, risky = !!o.risky, cap = o.riskyMax || RISKY_MAX;
      if (nodes[s] == null || nodes[t] == null) return null;
      // L = legal (run is the 500 ft risky cap). F = faster run still ≤75 ft.
      // H = that faster run already exceeded 75 ft.
      // A hold is the faster run suspended at the node where we left it. Coming
      // back to that same node continues the run, so a U-turn cannot split one
      // stretch into two short legal pieces.
      const holdKey = hld => hld
        ? hld.at + ':' + Math.round(hld.fastGeo * 100) + ':' + (hld.hot ? 1 : 0) + ':' + Math.round(hld.run) + ':' + hld.fastN
        : '';
      const keyOf = (n, run, fastCm, hot, nFast, hld) => (hot
        ? n + '|H|' + Math.round(run)
        : fastCm ? n + '|F|' + fastCm + '|' + nFast
        : n + '|L|' + Math.round(run)) + '|' + holdKey(hld);
      const T = nodes[t];
      const g = new Map(), prev = new Map();
      const k0 = keyOf(s, 0, 0, 0, 0, null);
      g.set(k0, 0);
      const h = [[hav(nodes[s], T), s, 0, 0, 0, 0, 0, null, k0]], done = new Set();
      const push = x => {
        h.push(x);
        let i = h.length - 1;
        while (i > 0) {
          const p = (i - 1) >> 1;
          if (h[p][0] <= h[i][0]) break;
          [h[p], h[i]] = [h[i], h[p]];
          i = p;
        }
      };
      const pop = () => {
        const top = h[0], last = h.pop();
        if (h.length) {
          h[0] = last;
          let i = 0;
          for (;;) {
            let a = 2 * i + 1, b = a + 1, m = i;
            if (a < h.length && h[a][0] < h[m][0]) m = a;
            if (b < h.length && h[b][0] < h[m][0]) m = b;
            if (m === i) break;
            [h[m], h[i]] = [h[i], h[m]];
            i = m;
          }
        }
        return top;
      };
      let goal = null;
      while (h.length) {
        const [, u, run, fastGeo, fastW, fastN, hot, hold, ku] = pop();
        if (done.has(ku)) continue;
        done.add(ku);
        // A short faster jog is legal, so the route may finish on it (run stays 0).
        if (u === t && run === 0 && !hot) { goal = ku; break; }
        for (const [v, w, si, rev, kind, geo] of (adj[u] || [])) {
          let nr = 0, nGeo = 0, nW = 0, nN = 0, nHot = 0, nHold = null, cost = w;
          const resume = kind === 1 && hold && hold.at === u ? hold : null;
          const onHot = kind === 1 && (hot || (resume && resume.hot));
          if (onHot) {
            const baseRun = hot ? run : resume.run;
            nr = baseRun + w;
            if (!risky || nr > cap) continue;
            cost = w * 6 + 60;
            nGeo = (hot ? fastGeo : resume.fastGeo) + geo;
            nW = (hot ? fastW : resume.fastW) + w;
            nN = (hot ? fastN : resume.fastN) + 1;
            nHot = 1;
          } else if (kind === 1) {
            const baseGeo = resume ? resume.fastGeo : fastGeo;
            const baseW = resume ? resume.fastW : fastW;
            const baseN = resume ? resume.fastN : fastN;
            const baseRun = resume ? resume.run : run;
            nGeo = baseGeo + geo; nW = baseW + w; nN = baseN + 1;
            if (shownFeet(nGeo) <= SHORT_LEGAL_FT) {
              cost = w;
            } else if (!risky) {
              continue;
            } else {
              nr = baseRun + nW;
              if (nr > cap) continue;
              // Prefix edges were priced as legal. Charge the unpaid 6×+60 now.
              cost = 6 * nW + 60 * nN - baseW;
              nHot = 1;
            }
          } else if (kind === 2) {
            if (!risky) continue;
            nr = run + w;
            if (nr > cap) continue;
            cost = w * 6 + 60;
          } else {
            if (rule.cross === false && fnode.has(v) && !cnode.has(v) && v !== t) continue;
            if (fast.has(v)) cost += 150;
            if (fastGeo > 0 || hot) nHold = { at: u, run, fastGeo, fastW, fastN, hot: hot ? 1 : 0 };
            else nHold = hold;
          }
          const cm = nHot ? 0 : (nGeo ? Math.round(nGeo * 100) : 0);
          const kv = keyOf(v, nr, cm, nHot, nHot ? 0 : nN, nHold);
          const ng = g.get(ku) + cost;
          if (!g.has(kv) || ng < g.get(kv)) {
            g.set(kv, ng);
            prev.set(kv, [ku, si, rev]);
            push([ng + hav(nodes[v], T), v, nr, nGeo, nW, nN, nHot ? 1 : 0, nHold, kv]);
          }
        }
      }
      if (!goal) return null;
      const parts = [];
      let x = goal;
      while (x !== k0) {
        const [pk, si, rev] = prev.get(x);
        parts.push([si, rev]);
        x = pk;
      }
      parts.reverse();
      return parts;
    }
    return { reset, build, nearest, astar };
  }

  function geometry(D, parts) {
    const ll = [];
    for (const [si, rev] of parts) {
      let p = D.segs[si][7];
      if (rev) p = p.slice().reverse();
      for (const pt of p) {
        const lat = pt[1], lon = pt[0];
        const last = ll[ll.length - 1];
        if (last && Math.abs(last[0] - lat) < 1e-7 && Math.abs(last[1] - lon) < 1e-7) continue;
        ll.push([lat, lon]);
      }
    }
    return ll;
  }

  function bucketize(buckets, segs, from) {
    segs.slice(from).forEach((s, j) => {
      const i = from + j, p = s[7][0];
      const k = Math.floor(p[0] / G) + ',' + Math.floor(p[1] / G);
      (buckets[k] || (buckets[k] = [])).push(i);
    });
  }

  // One hop. Routed legs are road vertices. Unroutable hops are a short dash or nothing.
  function routePair(net, D, buckets, a, b, o) {
    const A = net.nearest(D, buckets, { lat: +a.lat, lng: +a.lon }, o);
    const B = net.nearest(D, buckets, { lat: +b.lat, lng: +b.lon }, o);
    let parts = null;
    if (A[0] != null && B[0] != null) {
      for (const pair of [[A[0], B[0]], [A[2], B[0]], [A[0], B[2]], [A[2], B[2]]]) {
        parts = net.astar(pair[0], pair[1], o);
        if (parts && parts.length) break;
        parts = null;
      }
    }
    if (parts && parts.length) return { points: geometry(D, parts), dashed: false };
    const d = hav([a.lon, a.lat], [b.lon, b.lat]);
    if (d <= GAP_MAX_M) return { points: [[+a.lat, +a.lon], [+b.lat, +b.lon]], dashed: true };
    return { points: null, dashed: false };
  }

  function tilesIn(meta, south, west, north, east) {
    const T = meta.tileSize, have = new Set(meta.tiles), out = [];
    for (let x = Math.floor(west / T); x <= Math.floor(east / T); x++) {
      for (let y = Math.floor(south / T); y <= Math.floor(north / T); y++) {
        const k = x + '_' + y;
        if (have.has(k)) out.push(k);
      }
    }
    return out;
  }

  function rulesApi() {
    if (root.GCMRule) return root.GCMRule;
    // Node tests load this file via require; the browser sets window.GCMRule from roadrule.js.
    if (typeof module === 'object' && typeof module.require === 'function') return module.require('./roadrule.js');
    throw new Error('Road rules did not load');
  }

  // Load the region's road tiles and route an ordered stop list.
  // veh is 'golf_cart' or 'lsv' (public/roadrule.js). Risky is off, so no stretch
  // over SHORT_LEGAL_FT. A faster-road jog at or under that length is legal.
  async function openRegion(region, rules, veh, fetchImpl) {
    const fetchFn = fetchImpl || fetch;
    const base = '/data/' + region.id + '/';
    const Rule = rulesApi();
    const rule = Rule.ruleFor(rules, region, veh || Rule.DEFAULT_VEH);
    const cls = s => Rule.cls(s, rule);
    const unk = s => region.id !== 'sd' && region.id !== 'villages' && s[3] === 'i' && /^(secondary|tertiary|unclassified)/.test(s[1]) && cls(s) !== 3;
    const o = { cls, unk, rule, risky: false, G };
    const indexRes = await fetchFn(base + 'index.json');
    if (!indexRes.ok) throw new Error('road index');
    const index = await indexRes.json();
    const D = { meta: index.meta, segs: [] };
    const buckets = {};
    const net = create();
    const loaded = new Set();
    async function ensure(south, west, north, east) {
      const ks = tilesIn(index.meta, south, west, north, east).filter(k => !loaded.has(k));
      for (const k of ks) {
        const r = await fetchFn(base + 'tiles/' + k + '.json');
        if (!r.ok) continue;
        const segs = await r.json();
        if (loaded.has(k)) continue;
        loaded.add(k);
        const from = D.segs.length;
        D.segs.push(...segs);
        bucketize(buckets, D.segs, from);
        net.build(D, from, o);
      }
    }
    async function legs(stops) {
      const pad = 0.06;
      let south = 90, west = 180, north = -90, east = -180;
      for (const p of stops) {
        const lat = +p.lat, lon = +p.lon;
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        south = Math.min(south, lat); north = Math.max(north, lat);
        west = Math.min(west, lon); east = Math.max(east, lon);
      }
      if (south > north) return [];
      await ensure(south - pad, west - pad, north + pad, east + pad);
      const out = [];
      for (let i = 1; i < stops.length; i++) out.push(routePair(net, D, buckets, stops[i - 1], stops[i], o));
      return out;
    }
    // Same palette as app.js STY / mkLine, so the renter map reads like the city map.
    function roadStyle(s) {
      const c0 = cls(s);
      const c = s[3] === 'c' ? 2 : unk(s) ? 4 : c0;
      const STY = [
        { color: '#12a150', weight: 3.2 },
        { color: '#4cc38a', weight: 2.6, dashArray: '5 4' },
        { color: '#0b9fb3', weight: 3.4 },
        { color: '#e5484d', weight: 3, opacity: 0.75 },
        { color: '#e0a800', weight: 3.2, dashArray: '6 6' },
      ];
      return STY[c] || STY[0];
    }
    return { legs, rule, veh: rule.veh, cover: ensure, segments: () => D.segs, roadStyle };
  }

  const api = { G, RISKY_MAX, SHORT_LEGAL_FT, UNKW, GAP_MAX_M, hav, len, shownFeet, explicitBan, riskyMask, create, geometry, bucketize, routePair, tilesIn, openRegion };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMRouter = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
