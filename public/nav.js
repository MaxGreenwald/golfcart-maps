// Turn-by-turn guidance from a routed leg (router.js routePair -> runs with OSM street names).
// Pure geometry, no paid APIs: maneuvers come from the bearing change where the street name changes.
// Used by the renter page (public/p.js). Node tests load it with require.
(function (root) {
  const R = 6371000, rad = Math.PI / 180;
  const OFF_ROUTE_M = 35, ARRIVE_M = 25;
  function hav(a, b) { // [lat, lon]
    const dl = (b[0] - a[0]) * rad, dn = (b[1] - a[1]) * rad;
    const x = Math.sin(dl / 2) ** 2 + Math.cos(a[0] * rad) * Math.cos(b[0] * rad) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  function bearing(a, b) {
    const y = Math.sin((b[1] - a[1]) * rad) * Math.cos(b[0] * rad);
    const x = Math.cos(a[0] * rad) * Math.sin(b[0] * rad) - Math.sin(a[0] * rad) * Math.cos(b[0] * rad) * Math.cos((b[1] - a[1]) * rad);
    return (Math.atan2(y, x) / rad + 360) % 360;
  }
  // Point `d` metres back (dir -1) or ahead (dir +1) of index i along pts.
  function probe(pts, i, dir, d) {
    let acc = 0, j = i;
    while (j + dir >= 0 && j + dir < pts.length) {
      acc += hav(pts[j], pts[j + dir]); j += dir;
      if (acc >= d) break;
    }
    return pts[j];
  }
  function turnType(delta) { // delta in (-180, 180], + is right
    const a = Math.abs(delta), side = delta > 0 ? 'right' : 'left';
    if (a < 25) return { type: 'straight', mod: 'straight' };
    if (a < 50) return { type: 'slight', mod: 'slight ' + side };
    if (a < 140) return { type: 'turn', mod: side };
    return { type: 'sharp', mod: 'sharp ' + side };
  }
  const COMPASS = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
  // runs: [{name, points:[[lat,lon],...]}]; dest: label of the stop.
  function buildSteps(runs, dest) {
    const pts = [], cum = [], steps = [];
    const groups = [];
    for (const r of runs || []) {
      if (!r.points || !r.points.length) continue;
      const g = groups[groups.length - 1];
      if (g && g.name === r.name) g.points.push(...r.points); else groups.push({ name: r.name, points: r.points.slice() });
    }
    const starts = [];
    for (const g of groups) {
      starts.push(pts.length ? pts.length - 1 : 0);
      for (const p of g.points) {
        const last = pts[pts.length - 1];
        if (last && Math.abs(last[0] - p[0]) < 1e-7 && Math.abs(last[1] - p[1]) < 1e-7) continue;
        cum.push(last ? cum[cum.length - 1] + hav(last, p) : 0);
        pts.push(p);
      }
    }
    if (pts.length < 2) return { pts, cum, steps, total: 0 };
    const b0 = bearing(pts[0], probe(pts, 0, 1, 20));
    steps.push({ kind: 'depart', mod: 'straight', name: groups[0].name, at: 0, ll: pts[0],
      text: `Head ${COMPASS[Math.round(b0 / 45) % 8]}` + (groups[0].name ? ` on ${groups[0].name}` : '') });
    for (let k = 1; k < groups.length; k++) {
      const i = starts[k];
      const bin = bearing(probe(pts, i, -1, 15), pts[i]);
      const bout = bearing(pts[i], probe(pts, i, 1, 15));
      const delta = ((bout - bin + 540) % 360) - 180;
      const t = turnType(delta);
      const name = groups[k].name;
      // An unnamed connector straight ahead is not worth a prompt.
      if (t.type === 'straight' && (!name || !groups[k - 1].name)) continue;
      const verb = t.type === 'straight' ? 'Continue onto' : `Turn ${t.mod} onto`;
      steps.push({ kind: t.type === 'straight' ? 'continue' : 'turn', mod: t.mod, name, at: cum[i], ll: pts[i],
        text: name ? `${verb} ${name}` : `Turn ${t.mod}` });
    }
    const total = cum[cum.length - 1];
    steps.push({ kind: 'arrive', mod: 'arrive', name: dest || '', at: total, ll: pts[pts.length - 1],
      text: dest ? `Arrive at ${dest}` : 'Arrive at the stop' });
    steps.forEach((s, i) => { s.len = (steps[i + 1] ? steps[i + 1].at : total) - s.at; });
    return { pts, cum, steps, total };
  }
  // Snap [lat,lon] onto the route. Returns {along, off} in metres.
  function project(route, ll) {
    const { pts, cum } = route;
    const kx = Math.cos(ll[0] * rad);
    let best = { along: 0, off: Infinity };
    for (let i = 1; i < pts.length; i++) {
      const ax = (pts[i - 1][1] - ll[1]) * kx, ay = pts[i - 1][0] - ll[0];
      const bx = (pts[i][1] - ll[1]) * kx, by = pts[i][0] - ll[0];
      const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
      let t = L2 ? -(ax * dx + ay * dy) / L2 : 0;
      t = Math.max(0, Math.min(1, t));
      const ex = ax + t * dx, ey = ay + t * dy, d = Math.sqrt(ex * ex + ey * ey) * 111320;
      if (d < best.off) best = { along: cum[i - 1] + t * (cum[i] - cum[i - 1]), off: d };
    }
    return best;
  }
  function fmtDist(m) {
    const ft = m * 3.281;
    if (ft < 30) return 'Now';
    if (ft < 1000) return Math.max(50, Math.round(ft / 50) * 50) + ' ft';
    const mi = m / 1609.34;
    return (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + ' mi';
  }
  function phrase(step, m) {
    const d = fmtDist(m);
    const t = step.text.charAt(0).toLowerCase() + step.text.slice(1);
    return d === 'Now' ? step.text : `In ${d}, ${t}`;
  }
  // State for one live position. offCount carries across fixes (2 off fixes in a row = reroute).
  function status(route, ll, prev) {
    const pr = project(route, ll);
    const offCount = pr.off > OFF_ROUTE_M ? ((prev && prev.offCount) || 0) + 1 : 0;
    const remaining = Math.max(0, route.total - pr.along);
    const arrived = remaining < ARRIVE_M && pr.off < OFF_ROUTE_M + 15;
    let idx = route.steps.findIndex((s, i) => i > 0 && s.at > pr.along + 8);
    if (idx < 0) idx = route.steps.length - 1;
    const next = route.steps[idx];
    const toNext = Math.max(0, next.at - pr.along);
    return { along: pr.along, off: pr.off, offCount, offRoute: offCount >= 2, arrived, idx, next, toNext, remaining,
      text: arrived ? route.steps[route.steps.length - 1].text : phrase(next, toNext) };
  }
  const api = { OFF_ROUTE_M, ARRIVE_M, hav, bearing, turnType, buildSteps, project, status, fmtDist, phrase };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMNav = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
