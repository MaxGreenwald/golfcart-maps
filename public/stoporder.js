// Visit order for a partner experience (Max, Oct 31 2026, t441u).
// When the partner leaves "Start riders at their nearest stop" on and we know where the rider is,
// begin at the stop nearest the rider and keep the partner's sequence from there:
//  - Loop (first and last stop close together): go around forward or backward, wrapping, whichever is shorter.
//  - Line: finish one side of the partner order, then come back for the other side, whichever is shorter.
// "Shorter" is straight-line distance from the rider through every stop. Off, or no location: partner order exactly.
(function (root, f) { const m = f(); if (typeof module === 'object' && module.exports) module.exports = m; else root.GCMStopOrder = m; })(this, function () {
  const R = 6371000, rad = d => d * Math.PI / 180;
  function dist(a, b) {
    const dLat = rad(b.lat - a.lat), dLon = rad(b.lon - a.lon);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  const ok = s => s && Number.isFinite(+s.lat) && Number.isFinite(+s.lon) && s.lat !== '' && s.lon !== '';
  const pt = s => ({ lat: +s.lat, lon: +s.lon });
  function pathLen(from, idx, stops) {
    let m = from ? dist(from, pt(stops[idx[0]])) : 0;
    for (let i = 1; i < idx.length; i++) m += dist(pt(stops[idx[i - 1]]), pt(stops[idx[i]]));
    return m;
  }
  // A ride is a loop when it ends near where it starts: within 400 m or a fifth of its own length.
  function isLoop(stops) {
    if (stops.length < 3) return false;
    const idx = stops.map((_, i) => i);
    const end = dist(pt(stops[0]), pt(stops[stops.length - 1]));
    return end <= Math.max(400, 0.2 * pathLen(null, idx, stops));
  }
  /** Returns { order: [partner indexes in visit order], reordered, mode, start }. */
  function plan(stops, rider, on) {
    stops = stops || [];
    const shop = stops.map((_, i) => i);
    const out = (order, mode) => ({ order, reordered: order.some((v, i) => v !== shop[i]), mode, start: order[0] });
    const good = shop.filter(i => ok(stops[i]));
    if (!on || !rider || !ok(rider) || good.length < 2) return out(shop, 'shop');
    const me = pt(rider);
    const g = good.map(i => stops[i]);
    let k = 0;
    g.forEach((s, i) => { if (dist(me, pt(s)) < dist(me, pt(g[k]))) k = i; });
    const n = g.length;
    let cands;
    if (isLoop(g)) {
      const fwd = [], back = [];
      for (let j = 0; j < n; j++) { fwd.push((k + j) % n); back.push((k - j + n) % n); }
      cands = [[fwd, 'loop-forward'], [back, 'loop-backward']];
    } else {
      const after = [], before = [];
      for (let j = k + 1; j < n; j++) after.push(j);
      for (let j = k - 1; j >= 0; j--) before.push(j);
      cands = [[[k, ...after, ...before], 'line-forward-first'], [[k, ...before, ...after], 'line-backward-first']];
    }
    // Ties keep the partner's forward direction.
    let best = cands[0];
    if (pathLen(me, cands[1][0], g) < pathLen(me, best[0], g) - 1) best = cands[1];
    const order = best[0].map(j => good[j]);
    shop.forEach(i => { if (!ok(stops[i])) order.push(i); });
    return out(order, best[1]);
  }
  return { plan, dist, isLoop };
});
