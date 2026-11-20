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
  // One budget for every snap pair of a search (the map tries up to four).
  // A miss used to walk the whole graph on the UI thread until the phone killed the web view.
  const ROUTE_BUDGET_MS = 3000;
  const ROUTE_STATE_BUDGET = 200000;
  // A hold only has to survive a local U-turn. Past this much legal travel it cannot
  // change the 75 ft / 500 ft decision cheaply enough to be worth a second copy of the graph.
  const HOLD_TRAVEL_M = 400;
  const UNKW = 1.8;
  // A miss longer than this is omitted. A short gap may be a dashed stub.
  // Anything longer would be the chord Max saw crossing the La Jolla water.
  const GAP_MAX_M = 70;
  const UTURN_M = 1500;   // extra cost (as metres) to turn back on the street you are driving on at a reroute (Max t433u)

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
      const end = o.to != null ? o.to : D.segs.length;
      for (let i = from; i < end; i++) {
        const s = D.segs[i];
        if (!s) continue;
        const c = cls(s), a = s[5], b = s[6], p = s[7];
        s._len ??= len(p);
        nodes[a] = p[0];
        nodes[b] = p[p.length - 1];
        if ((s[3] === 't' || s[3] === 'o' || s[3] === 'm' || s[3] === 's') && s[2] > rule.max_posted) { fast.add(a); fast.add(b); }
        if (c === 3) { fnode.add(a); fnode.add(b); }
        if (s[3] === 'c') { cnode.add(a); cnode.add(b); }
        // kind: 0 legal, 1 faster-road (75 ft waiver can apply), 2 explicit ban (never waived)
        const kind = c !== 3 ? 0 : explicitBan(s, rule) ? 2 : 1;
        const wmul = (unk(s) || s[3] === 'q') ? UNKW : 1;
        const geo = s._len;
        if (s[4] >= 0) (adj[a] || (adj[a] = [])).push([b, s._len * wmul, i, false, kind, geo]);
        if (s[4] <= 0) (adj[b] || (adj[b] = [])).push([a, s._len * wmul, i, true, kind, geo]);
      }
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
    // 75 ft restores the 6×+60 penalty for the whole run (so a longer stretch does
    // not get a cheap prefix). Explicit bans stay on the old rule.
    //
    // The hold (the suspended faster run) is what stops a U-turn from splitting one
    // stretch into two short legal pieces. It is kept in the state only while the
    // legal detour is still short enough to change that decision. A loose pass
    // runs first: if even that cannot reach the end, the full search cannot either.
    const SLICE = 8000;
    function budgetHit(o, stat) {
      const capN = o.stateBudget != null ? o.stateBudget : ROUTE_STATE_BUDGET;
      if ((stat.expanded || 0) > capN) return 'budget';
      if (o.deadline && Date.now() > o.deadline) return 'timeout';
      return '';
    }
    function noteHeap(stat) {
      if (typeof process === 'object' && process.memoryUsage) {
        const h = process.memoryUsage().heapUsed;
        if (!stat.heap || h > stat.heap) stat.heap = h;
      }
    }
    function holdKey(hld) {
      if (!hld) return '';
      // Once the run is already over 75 ft, only the node and the metres toward the
      // 500 ft cap change the next decision. Length in centimetres does not.
      if (hld.hot) return '|h' + hld.at + 'H' + Math.round(hld.run);
      return '|h' + hld.at + 'c' + Math.round(hld.fastGeo * 100) + 'r' + Math.round(hld.run) + 'n' + hld.fastN;
    }
    function stateKey(n, nr, nGeo, nHot, nN, nHold) {
      const h = holdKey(nHold);
      const runM = nr ? Math.round(nr) : 0;
      if (nHot) return n + '|H|' + runM + h;
      const cm = nGeo ? Math.round(nGeo * 100) : 0;
      if (cm) return n + '|F|' + cm + '|' + nN + h;
      if (runM || h) return n + '|L|' + runM + h;
      return String(n);
    }
    // One edge. null means this edge is not allowed from this state.
    // cls is 'hot' when the edge is a risky stretch (over 75 ft, or an explicit ban).
    function stepEdge(u, edge, st, holdMax, target, o) {
      const rule = o.rule, risky = !!o.risky, cap = o.riskyMax || RISKY_MAX;
      const [v, w, , , kind, geo] = edge;
      let nr = 0, nGeo = 0, nW = 0, nN = 0, nHot = 0, nHold = null, nTravel = 0, cost = w;
      const hold = st.hold;
      const resume = kind === 1 && hold && hold.at === u ? hold : null;
      const onHot = kind === 1 && (st.hot || (resume && resume.hot));
      if (onHot) {
        const baseRun = st.hot ? st.run : resume.run;
        nr = baseRun + w;
        if (!risky || nr > cap) return null;
        cost = w * 6 + 60;
        nGeo = (st.hot ? st.fastGeo : resume.fastGeo) + geo;
        nW = (st.hot ? st.fastW : resume.fastW) + w;
        nN = (st.hot ? st.fastN : resume.fastN) + 1;
        nHot = 1;
      } else if (kind === 1) {
        const baseGeo = resume ? resume.fastGeo : st.fastGeo;
        const baseW = resume ? resume.fastW : st.fastW;
        const baseN = resume ? resume.fastN : st.fastN;
        const baseRun = resume ? resume.run : st.run;
        nGeo = baseGeo + geo; nW = baseW + w; nN = baseN + 1;
        if (shownFeet(nGeo) <= SHORT_LEGAL_FT) cost = w;
        else if (!risky) return null;
        else {
          nr = baseRun + nW;
          if (nr > cap) return null;
          // Prefix edges were priced as legal. Charge the unpaid 6×+60 now.
          cost = 6 * nW + 60 * nN - baseW;
          nHot = 1;
        }
      } else if (kind === 2) {
        if (!risky) return null;
        nr = st.run + w;
        if (nr > cap) return null;
        cost = w * 6 + 60;
      } else {
        if (rule.cross === false && fnode.has(v) && !cnode.has(v) && v !== target) return null;
        if (fast.has(v)) cost += 150;
        if (st.fastGeo > 0 || st.hot) {
          nHold = { at: u, run: st.run, fastGeo: st.fastGeo, fastW: st.fastW, fastN: st.fastN, hot: st.hot ? 1 : 0 };
          nTravel = geo;
        } else if (st.hold) {
          nTravel = st.holdTravel + geo;
          if (!(nTravel > holdMax)) nHold = st.hold;
        }
      }
      return { v, cost, nr, nGeo, nW, nN, nHot, nHold, nTravel, cls: (nHot || kind === 2) ? 'hot' : 'legal' };
    }
    function heapPush(h, x) {
      h.push(x);
      let i = h.length - 1;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (h[p][0] <= h[i][0]) break;
        [h[p], h[i]] = [h[i], h[p]];
        i = p;
      }
    }
    function heapPop(h) {
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
    }
    // Superset of the real search: each ≤75 ft faster edge is its own legal piece,
    // and a forbidden edge is allowed whenever Risky would allow it on its own.
    // If this cannot reach the end, the real search cannot either.
    function looseReach(s, t, o, stat) {
      if (nodes[s] == null || nodes[t] == null) return 'none';
      const rule = o.rule, risky = !!o.risky, cap = o.riskyMax || RISKY_MAX;
      const T = nodes[t];
      const g = new Map(), done = new Set();
      const h = [[hav(nodes[s], T), s, 0, s]];
      g.set(s, 0);
      while (h.length) {
        stat.expanded = (stat.expanded || 0) + 1;
        if (stat.expanded > (o.stateBudget != null ? o.stateBudget : ROUTE_STATE_BUDGET)) return 'budget';
        if ((stat.expanded & 4095) === 0) {
          if (o.deadline && Date.now() > o.deadline) return 'timeout';
          noteHeap(stat);
        }
        const [, u, run, ku] = heapPop(h);
        if (done.has(ku)) continue;
        done.add(ku);
        if (u === t && run === 0) return 'ok';
        for (const [v, w, , , kind, geo] of (adj[u] || [])) {
          let nr = 0, cost = w;
          if (kind === 1 && shownFeet(geo) <= SHORT_LEGAL_FT && run === 0) nr = 0;
          else if (kind === 1 || kind === 2) {
            if (!risky) continue;
            nr = run + w;
            if (nr > cap) continue;
            cost = w * 6 + 60;
          } else {
            if (rule.cross === false && fnode.has(v) && !cnode.has(v) && v !== t) continue;
            if (fast.has(v)) cost += 150;
            nr = 0;
          }
          const kv = nr ? v + '|' + Math.round(nr) : v;
          const ng = g.get(ku) + cost;
          if (!g.has(kv) || ng < g.get(kv)) {
            g.set(kv, ng);
            heapPush(h, [ng + hav(nodes[v], T), v, nr, kv]);
          }
        }
      }
      return 'none';
    }
    function fresh(s, t, holdMax) {
      const k0 = String(s);
      const g = new Map(), prev = new Map();
      g.set(k0, 0);
      return {
        holdMax, k0, g, prev, done: new Set(), goal: null,
        h: [[hav(nodes[s], nodes[t]), s, 0, 0, 0, 0, 0, null, 0, k0]],
      };
    }
    function rebuild(ctx) {
      const parts = [];
      let x = ctx.goal;
      while (x !== ctx.k0) {
        const row = ctx.prev.get(x);
        if (!row) return null;
        parts.push([row[1], row[2]]);
        x = row[0];
      }
      parts.reverse();
      return parts;
    }
    // Expand until the goal, the budget, or `slice` pops. ctx is resumed across slices.
    function searchSlice(s, t, o, stat, ctx, holdMax) {
      if (!ctx) ctx = fresh(s, t, holdMax);
      const T = nodes[t];
      let steps = 0;
      const slice = o.sliceEvery || SLICE;
      while (ctx.h.length) {
        if (steps++ >= slice) return { done: false, ctx };
        stat.expanded = (stat.expanded || 0) + 1;
        if (stat.expanded > (o.stateBudget != null ? o.stateBudget : ROUTE_STATE_BUDGET)) {
          stat.reason = 'budget'; noteHeap(stat); return { done: true, parts: null, reason: 'budget' };
        }
        if ((stat.expanded & 4095) === 0) {
          if (o.deadline && Date.now() > o.deadline) { stat.reason = 'timeout'; noteHeap(stat); return { done: true, parts: null, reason: 'timeout' }; }
          noteHeap(stat);
        }
        const [, u, run, fastGeo, fastW, fastN, hot, hold, holdTravel, ku] = heapPop(ctx.h);
        if (ctx.done.has(ku)) continue;
        ctx.done.add(ku);
        if (u === t && run === 0 && !hot) {
          ctx.goal = ku;
          stat.reason = 'ok';
          return { done: true, parts: rebuild(ctx), reason: 'ok' };
        }
        const st = { run, fastGeo, fastW, fastN, hot, hold, holdTravel };
        for (const edge of (adj[u] || [])) {
          const stepped = stepEdge(u, edge, st, ctx.holdMax, t, o);
          if (!stepped) continue;
          const uturn = o.backSeg != null && ku === ctx.k0 && edge[2] === o.backSeg ? UTURN_M : 0;
          const kv = stateKey(stepped.v, stepped.nr, stepped.nHot ? 0 : stepped.nGeo, stepped.nHot, stepped.nHot ? 0 : stepped.nN, stepped.nHold);
          const ng = ctx.g.get(ku) + stepped.cost + uturn;
          if (!ctx.g.has(kv) || ng < ctx.g.get(kv)) {
            ctx.g.set(kv, ng);
            ctx.prev.set(kv, [ku, edge[2], edge[3]]);
            heapPush(ctx.h, [ng + hav(nodes[stepped.v], T), stepped.v, stepped.nr, stepped.nGeo, stepped.nW, stepped.nN, stepped.nHot ? 1 : 0, stepped.nHold, stepped.nTravel, kv]);
          }
        }
      }
      stat.reason = 'none';
      return { done: true, parts: null, reason: 'none' };
    }
    // True when dropping the hold made this path cheaper than the full rules allow.
    // A path whose every edge has the same cost either way is still an optimal path.
    function underpriced(parts, s, t, o) {
      const walk = (holdMax) => {
        let st = { run: 0, fastGeo: 0, fastW: 0, fastN: 0, hot: 0, hold: null, holdTravel: 0 };
        let u = s;
        const costs = [];
        for (const [si, rev] of parts) {
          const edge = (adj[u] || []).find(ed => ed[2] === si && !!ed[3] === !!rev);
          if (!edge) return null;
          const stepped = stepEdge(u, edge, st, holdMax, t, o);
          if (!stepped) return null;
          costs.push(stepped.cost);
          st = { run: stepped.nr, fastGeo: stepped.nGeo, fastW: stepped.nW, fastN: stepped.nN, hot: stepped.nHot, hold: stepped.nHold, holdTravel: stepped.nTravel };
          u = stepped.v;
        }
        if (st.run !== 0 || st.hot) return null;
        return costs;
      };
      const full = walk(Infinity), lim = walk(HOLD_TRAVEL_M);
      if (!full || !lim || full.length !== lim.length) return true;
      for (let i = 0; i < full.length; i++) if (Math.abs(full[i] - lim[i]) > 0.5) return true;
      return false;
    }
    function astar(s, t, o) {
      o = o || {};
      const stat = o.stat || {};
      const t0 = Date.now();
      if (nodes[s] == null || nodes[t] == null) { stat.reason = 'none'; stat.ms = 0; stat.expanded = stat.expanded || 0; return null; }
      if (o.loose !== false) {
        const reach = looseReach(s, t, o, stat);
        if (reach !== 'ok') { stat.reason = reach; stat.ms = Date.now() - t0; noteHeap(stat); return null; }
      }
      let holdMax = o.holdMax != null ? o.holdMax : HOLD_TRAVEL_M;
      let ctx = null;
      let guard = 0;
      while (guard++ < 100000) {
        const r = searchSlice(s, t, o, stat, ctx, holdMax);
        if (!r.done) { ctx = r.ctx; continue; }
        if (r.reason === 'ok' && r.parts && r.parts.length && holdMax < Infinity && underpriced(r.parts, s, t, o)) {
          const why = budgetHit(o, stat);
          if (why) { stat.reason = why; stat.ms = Date.now() - t0; return null; }
          holdMax = Infinity;
          ctx = null;
          continue;
        }
        stat.reason = r.reason === 'ok' ? 'ok' : (r.reason || stat.reason || 'none');
        stat.ms = Date.now() - t0;
        noteHeap(stat);
        return r.reason === 'ok' ? (r.parts || []) : null;
      }
      stat.reason = 'budget';
      stat.ms = Date.now() - t0;
      return null;
    }
    async function astarAsync(s, t, o) {
      o = o || {};
      const stat = o.stat || {};
      const t0 = Date.now();
      const stop = () => o.stop && o.stop();
      if (nodes[s] == null || nodes[t] == null) { stat.reason = 'none'; stat.ms = 0; return null; }
      if (o.loose !== false) {
        const reach = looseReach(s, t, o, stat);
        if (reach !== 'ok') { stat.reason = reach; stat.ms = Date.now() - t0; noteHeap(stat); return null; }
        if (stop()) { stat.reason = 'cancel'; stat.ms = Date.now() - t0; return null; }
        await new Promise(res => setTimeout(res, 0));
      }
      let holdMax = o.holdMax != null ? o.holdMax : HOLD_TRAVEL_M;
      let ctx = null;
      let guard = 0;
      while (guard++ < 100000) {
        if (stop()) { stat.reason = 'cancel'; stat.ms = Date.now() - t0; return null; }
        const r = searchSlice(s, t, o, stat, ctx, holdMax);
        if (!r.done) {
          ctx = r.ctx;
          await new Promise(res => setTimeout(res, 0));
          continue;
        }
        if (r.reason === 'ok' && r.parts && r.parts.length && holdMax < Infinity && underpriced(r.parts, s, t, o)) {
          const why = budgetHit(o, stat);
          if (why) { stat.reason = why; stat.ms = Date.now() - t0; return null; }
          holdMax = Infinity;
          ctx = null;
          await new Promise(res => setTimeout(res, 0));
          continue;
        }
        stat.reason = r.reason === 'ok' ? 'ok' : (r.reason || stat.reason || 'none');
        stat.ms = Date.now() - t0;
        noteHeap(stat);
        return r.reason === 'ok' ? (r.parts || []) : null;
      }
      stat.reason = 'budget';
      stat.ms = Date.now() - t0;
      return null;
    }
    // Every node reachable from the seeds on legal roads (and short legal jogs) within maxM of
    // road length. seeds: [[node, startMeters], ...]. Returns Map node -> meters. Sales mode (/s/).
    function reach(seeds, maxM, o) {
      const rule = o.rule, dist = new Map(), h = [];
      for (const [n, m] of seeds) if (n != null && nodes[n] != null && !(dist.get(n) <= m)) { dist.set(n, m); heapPush(h, [m, n]); }
      while (h.length) {
        const [d, u] = heapPop(h);
        if (d > dist.get(u)) continue;
        for (const [v, , , , kind, geo] of (adj[u] || [])) {
          if (kind === 2 || (kind === 1 && shownFeet(geo) > SHORT_LEGAL_FT)) continue;
          if (rule.cross === false && fnode.has(v) && !cnode.has(v)) continue;
          const nd = d + geo;
          if (nd > maxM || dist.get(v) <= nd) continue;
          dist.set(v, nd);
          heapPush(h, [nd, v]);
        }
      }
      return dist;
    }
    return { reset, build, nearest, astar, astarAsync, reach };

  }


  // Max t433u: while driving, start the route at the corner AHEAD on the street you are on, not at
  // whichever end of that block is closer (which was often behind you, so every reroute said to turn
  // around). heading is the GPS course in degrees. Returns { node, backSeg, stub, stubLen, si } where
  // stub is [lon, lat] points from your spot to that corner, or null when no road is close.
  function bearingDeg(a, b) {
    const k = Math.PI / 180, y = Math.sin((b[0] - a[0]) * k) * Math.cos(b[1] * k);
    const x = Math.cos(a[1] * k) * Math.sin(b[1] * k) - Math.sin(a[1] * k) * Math.cos(b[1] * k) * Math.cos((b[0] - a[0]) * k);
    return (Math.atan2(y, x) / k + 360) % 360;
  }
  function aheadStart(D, buckets, ll, heading, o) {
    if (!Number.isFinite(heading)) return null;
    const cls = o.cls, Gv = o.G || G, q = [ll.lng, ll.lat], kx = Math.cos(ll.lat * Math.PI / 180);
    const bx = Math.floor(q[0] / Gv), by = Math.floor(q[1] / Gv);
    let best = null, bd = 1e18;
    for (let x = bx - 1; x <= bx + 1; x++) for (let y = by - 1; y <= by + 1; y++) for (const i of (buckets[x + ',' + y] || [])) {
      const sg = D.segs[i];
      if (cls(sg) === 3) continue;
      const p = sg[7];
      for (let j = 1; j < p.length; j++) {
        const ax = (p[j - 1][0] - q[0]) * kx, ay = p[j - 1][1] - q[1], ex_ = (p[j][0] - q[0]) * kx, ey_ = p[j][1] - q[1];
        const dx = ex_ - ax, dy = ey_ - ay, L2 = dx * dx + dy * dy;
        const t = Math.max(0, Math.min(1, L2 ? -(ax * dx + ay * dy) / L2 : 0));
        const ex = ax + t * dx, ey = ay + t * dy;
        // Prefer pieces that run along the heading (either way), so a cross street at a corner does not win.
        const bdeg = bearingDeg(p[j - 1], p[j]), dd = Math.abs(((bdeg - heading) % 180 + 270) % 180 - 90);
        const d = (ex * ex + ey * ey) * (dd > 60 ? 9 : 1);
        if (d < bd) { bd = d; best = { i, j, t, fwd: Math.abs(((bdeg - heading) % 360 + 540) % 360 - 180) <= 90 }; }
      }
    }
    if (!best || Math.sqrt(bd) * 111320 > 40) return null;
    const sg = D.segs[best.i], p = sg[7];
    // One-way against your heading: no forward option on this street, use the normal start.
    if ((best.fwd && sg[4] < 0) || (!best.fwd && sg[4] > 0)) return null;
    const a = p[best.j - 1], b = p[best.j];
    const snap = [a[0] + (b[0] - a[0]) * best.t, a[1] + (b[1] - a[1]) * best.t];
    const stub = [snap].concat(best.fwd ? p.slice(best.j) : p.slice(0, best.j).reverse());
    return { node: best.fwd ? sg[6] : sg[5], backSeg: best.i, si: best.i, stub, stubLen: len(stub) };
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

  // One run per route part with its OSM street name (D.names[s[0]]), for turn-by-turn.
  function namedRuns(D, parts, o) {
    const names = D.names || [];
    const mask = o && o.rule && o.cls ? riskyMask(D.segs, parts, o.rule, o.cls) : [];
    return parts.map(([si, rev], k) => {
      const s = D.segs[si];
      let p = s[7];
      if (rev) p = p.slice().reverse();
      return { name: names[s[0]] || '', hw: s[1], risky: !!mask[k], points: p.map(pt => [pt[1], pt[0]]) };
    });
  }

  function bucketize(buckets, segs, from) {
    segs.slice(from).forEach((s, j) => {
      const i = from + j, p = s[7][0];
      const k = Math.floor(p[0] / G) + ',' + Math.floor(p[1] / G);
      (buckets[k] || (buckets[k] = [])).push(i);
    });
  }

  // One hop. Routed legs are road vertices. Unroutable hops are a short dash or nothing.
  // Async so a long search yields the main thread (renter pages). The map uses a worker.
  async function routePair(net, D, buckets, a, b, o) {
    o = o || {};
    const deadline = o.deadline || (o.budgetMs === 0 ? 0 : Date.now() + (o.budgetMs || ROUTE_BUDGET_MS));
    let stateBudget = o.stateBudget != null ? o.stateBudget : ROUTE_STATE_BUDGET;
    let lastReason = 'none';
    const go = async (snode, tnode, extra) => {
      const stat = {};
      const parts = await net.astarAsync(snode, tnode, { ...o, ...extra, deadline, stateBudget, stat });
      stateBudget = Math.max(0, stateBudget - (stat.expanded || 0));
      lastReason = stat.reason || lastReason;
      return parts;
    };
    const A = net.nearest(D, buckets, { lat: +a.lat, lng: +a.lon }, o);
    const B = net.nearest(D, buckets, { lat: +b.lat, lng: +b.lon }, o);
    let parts = null;
    // Moving with a known course: start at the corner ahead and add the stretch up to it.
    const H = o.heading != null && B[0] != null ? aheadStart(D, buckets, { lat: +a.lat, lng: +a.lon }, o.heading, o) : null;
    if (H) {
      for (const tb of [B[0], B[2]]) { parts = await go(H.node, tb, { backSeg: H.backSeg }); if (parts && parts.length) break; if (lastReason === 'timeout' || lastReason === 'budget') break; parts = null; }
      if (parts) {
        const stubPts = H.stub.map(pt => [pt[1], pt[0]]), names = D.names || [], sg = D.segs[H.si];
        const runs = namedRuns(D, parts, o);
        const pts = geometry(D, parts);
        return { points: stubPts.concat(pts.slice(hav(H.stub[H.stub.length - 1], [pts[0][1], pts[0][0]]) < 0.5 ? 1 : 0)), dashed: false,
          runs: [{ name: names[sg[0]] || '', hw: sg[1], risky: false, points: stubPts }].concat(runs), ahead: true };
      }
    }
    if (!parts && A[0] != null && B[0] != null && lastReason !== 'timeout' && lastReason !== 'budget') {
      for (const pair of [[A[0], B[0]], [A[2], B[0]], [A[0], B[2]], [A[2], B[2]]]) {
        if (pair[0] == null || pair[1] == null) continue;
        parts = await go(pair[0], pair[1], {});
        if (parts && parts.length) break;
        if (lastReason === 'timeout' || lastReason === 'budget') break;
        parts = null;
      }
    }
    if (parts && parts.length) return { points: geometry(D, parts), dashed: false, runs: namedRuns(D, parts, o), reason: 'ok' };
    const d = hav([a.lon, a.lat], [b.lon, b.lat]);
    if (d <= GAP_MAX_M && lastReason !== 'timeout' && lastReason !== 'budget') return { points: [[+a.lat, +a.lon], [+b.lat, +b.lon]], dashed: true, reason: 'none' };
    return { points: null, dashed: false, reason: lastReason === 'budget' ? 'timeout' : lastReason };
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

  // Same edge classes the map builds in app.js. The route worker calls this too,
  // so a search off the main thread uses the graph the map drew.
  function graphOpts(rule, regionId, lenient) {
    const Rule = rulesApi();
    const cls = s => Rule.cls(s, rule, !!lenient);
    const unk = s => regionId !== 'sd' && regionId !== 'villages' && s[3] === 'i' && /^(secondary|tertiary|unclassified)/.test(s[1]) && cls(s) !== 3;
    return { cls, unk, rule };
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
    const D = { meta: index.meta, names: index.names || [], segs: [] };
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
    async function legs(stops, opts) {
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
      const h0 = opts && Number.isFinite(opts.heading) ? opts.heading : null;
      for (let i = 1; i < stops.length; i++) out.push(await routePair(net, D, buckets, stops[i - 1], stops[i], i === 1 && h0 != null ? { ...o, heading: h0 } : o));
      return out;
    }
    // One trip from a to b (renter "Navigate somewhere else"). risky: true allows the
    // map's ⚠️ Risky stretches (same RISKY_MAX cap); default is Legal only.
    async function trip(a, b, opts) {
      const pad = 0.04;
      await ensure(Math.min(a.lat, b.lat) - pad, Math.min(a.lon, b.lon) - pad, Math.max(a.lat, b.lat) + pad, Math.max(a.lon, b.lon) + pad);
      return routePair(net, D, buckets, a, b, { ...o, risky: !!(opts && opts.risky), heading: opts && Number.isFinite(opts.heading) ? opts.heading : null });
    }
    // Street-name matches among loaded tiles, for the renter search box.
    function streets(q, limit) {
      const n = String(q || '').toLowerCase().trim();
      if (!n) return [];
      const seen = new Set(), out = [];
      for (const s of D.segs) {
        const nm = D.names[s[0]];
        if (!nm || seen.has(nm) || !nm.toLowerCase().includes(n)) continue;
        seen.add(nm);
        out.push({ name: nm, sub: 'street', lat: s[7][0][1], lon: s[7][0][0], score: nm.toLowerCase().startsWith(n) ? 0.5 : 1.5 });
        if (out.length >= (limit || 5)) break;
      }
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
    // Sales mode: legal roads you can drive from `from` within `miles` of road (one way).
    // { ok, snapM, miles, roadMiles, segs: [[lat,lon]...][], at(lat, lon) -> road miles or null }
    async function reachable(from, miles) {
      const maxM = Math.max(0, +miles || 0) * 1609.34;
      const lat = +from.lat, lon = +from.lon;
      const dLat = maxM / 111320 + 0.01, dLon = dLat / Math.max(0.2, Math.cos(lat * Math.PI / 180));
      await ensure(lat - dLat, lon - dLon, lat + dLat, lon + dLon);
      const A = net.nearest(D, buckets, { lat, lng: lon }, o);
      if (A[0] == null || A[1] > 400) return { ok: false, reason: 'far', snapM: A[0] == null ? null : Math.round(A[1]) };
      const dist = net.reach([[A[0], A[1]], [A[2], A[1]]], maxM, o);
      const segs = [];
      let roadM = 0;
      for (const s of D.segs) {
        if (!s || cls(s) === 3) continue;
        const da = dist.get(s[5]), db = dist.get(s[6]);
        if (da == null || db == null) continue;
        segs.push(s[7].map(p => [p[1], p[0]]));
        roadM += s._len || len(s[7]);
      }
      function at(la, lo) {
        const P = net.nearest(D, buckets, { lat: +la, lng: +lo }, o);
        if (P[0] == null || P[1] > 400) return null;
        const d = Math.min(dist.has(P[0]) ? dist.get(P[0]) : Infinity, dist.has(P[2]) ? dist.get(P[2]) : Infinity);
        return Number.isFinite(d) ? Math.round((d + P[1]) / 160.934) / 10 : null;
      }
      return { ok: true, snapM: Math.round(A[1]), miles: +miles, roadMiles: Math.round(roadM / 160.934) / 10, segs, at };
    }
    return { legs, trip, reachable, streets, rule, veh: rule.veh, cover: ensure, segments: () => D.segs, roadStyle };
  }

  const api = { UTURN_M, aheadStart, bearingDeg, G, RISKY_MAX, SHORT_LEGAL_FT, ROUTE_BUDGET_MS, ROUTE_STATE_BUDGET, HOLD_TRAVEL_M, UNKW, GAP_MAX_M, hav, len, shownFeet, explicitBan, riskyMask, create, geometry, namedRuns, bucketize, routePair, tilesIn, graphOpts, openRegion };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMRouter = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
