// Off-limits zones a rental shop draws: an area (polygon) or a road segment (line). Shared by the
// partner Worker (validation), the admin (drawing), the router (avoid if there is another way) and
// the renter page (draw, warn before the ride, warn when close while driving).
// Points are [lat, lon]. Road segments from the tiles are [lon, lat] (router order).
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMOffLimits = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const MAX_ZONES = 30, MAX_POINTS = 80, NAME_MAX = 60, NOTE_MAX = 200;
  const LINE_BUFFER_M = 15; // a road counts as "on" a drawn segment within this distance
  const AREA_MAX_KM2 = 25;  // one zone can't swallow a whole town
  const R = 6371000;
  const rad = d => d * Math.PI / 180;
  function hav(a, b) { // [lat, lon]
    const dLat = rad(b[0] - a[0]), dLon = rad(b[1] - a[1]);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  // Local flat projection in meters around a reference latitude.
  function xy(p, lat0) { return [rad(p[1]) * R * Math.cos(rad(lat0)), rad(p[0]) * R]; }
  function areaKm2(pts) {
    const lat0 = pts[0][0];
    let s = 0;
    for (let i = 0; i < pts.length; i++) {
      const a = xy(pts[i], lat0), b = xy(pts[(i + 1) % pts.length], lat0);
      s += a[0] * b[1] - b[0] * a[1];
    }
    return Math.abs(s) / 2 / 1e6;
  }
  function cleanPoints(raw) {
    if (!Array.isArray(raw)) return null;
    const out = [];
    for (const p of raw) {
      const lat = Array.isArray(p) ? +p[0] : p && +p.lat, lon = Array.isArray(p) ? +p[1] : p && +p.lon;
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
      const q = [Math.round(lat * 1e6) / 1e6, Math.round(lon * 1e6) / 1e6];
      const last = out[out.length - 1];
      if (!last || last[0] !== q[0] || last[1] !== q[1]) out.push(q);
    }
    return out;
  }
  /** Worker and admin: { zone } or { error }. */
  function clean(body) {
    const b = body || {};
    const kind = b.kind === 'line' ? 'line' : b.kind === 'area' ? 'area' : '';
    if (!kind) return { error: 'Pick an area or a road segment' };
    const name = String(b.name || '').replace(/\s+/g, ' ').trim();
    if (!name) return { error: 'Name the off-limits zone (for example "Boardwalk")' };
    if ([...name].length > NAME_MAX) return { error: 'Name is too long' };
    const note = String(b.note || '').replace(/\s+/g, ' ').trim();
    if ([...note].length > NOTE_MAX) return { error: 'Note is too long' };
    const points = cleanPoints(b.points);
    if (!points) return { error: 'Points must be map coordinates' };
    if (points.length > MAX_POINTS) return { error: 'Too many points (up to ' + MAX_POINTS + ')' };
    if (kind === 'area' && points.length < 3) return { error: 'An area needs at least 3 points' };
    if (kind === 'line' && points.length < 2) return { error: 'A road segment needs at least 2 points' };
    for (let i = 1; i < points.length; i++) if (hav(points[i - 1], points[i]) > 20000) return { error: 'Points are too far apart' };
    if (kind === 'area' && areaKm2(points) > AREA_MAX_KM2) return { error: 'That area is too big. Draw just the part renters should stay out of.' };
    return { zone: { kind, name, note, points } };
  }
  function inPoly(p, poly) { // p [lat, lon]
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const yi = poly[i][0], xi = poly[i][1], yj = poly[j][0], xj = poly[j][1];
      if ((yi > p[0]) !== (yj > p[0]) && p[1] < (xj - xi) * (p[0] - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function distToSeg(p, a, b, lat0) {
    const P = xy(p, lat0), A = xy(a, lat0), B = xy(b, lat0);
    const dx = B[0] - A[0], dy = B[1] - A[1], L2 = dx * dx + dy * dy;
    const t = L2 ? Math.max(0, Math.min(1, ((P[0] - A[0]) * dx + (P[1] - A[1]) * dy) / L2)) : 0;
    return Math.hypot(P[0] - A[0] - t * dx, P[1] - A[1] - t * dy);
  }
  function distToLine(p, line) { return nearestOnLine(p, line).d; }
  // Distance to a polyline and the direction (degrees, 0-180) of the closest piece.
  function nearestOnLine(p, line) {
    let d = Infinity, dir = 0;
    for (let i = 1; i < line.length; i++) {
      const di = distToSeg(p, line[i - 1], line[i], p[0]);
      if (di < d) { d = di; dir = axis(line[i - 1], line[i]); }
    }
    return { d, dir };
  }
  function axis(a, b) { // direction of a-b, folded to 0-180 so both ways match
    const A = xy(a, a[0]), B = xy(b, a[0]);
    return ((Math.atan2(B[1] - A[1], B[0] - A[0]) * 180 / Math.PI) + 360) % 180;
  }
  const PARALLEL_DEG = 35;
  function bbox(pts, padDeg) {
    let s = 90, w = 180, n = -90, e = -180;
    for (const p of pts) { s = Math.min(s, p[0]); n = Math.max(n, p[0]); w = Math.min(w, p[1]); e = Math.max(e, p[1]); }
    return [s - padDeg, w - padDeg, n + padDeg, e + padDeg];
  }
  function inBox(p, b) { return p[0] >= b[0] && p[0] <= b[2] && p[1] >= b[1] && p[1] <= b[3]; }
  // Walk a path in ~5 m steps and measure how much of it is inside a zone.
  function metersInside(path, z) {
    let m = 0;
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1], b = path[i], d = hav(a, b), n = Math.max(1, Math.ceil(d / 5));
      for (let k = 0; k < n; k++) {
        const f = (k + 0.5) / n, p = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
        if (!inBox(p, z._box)) continue;
        let hit;
        if (z.kind === 'area') hit = inPoly(p, z.points);
        else {
          // Along the drawn road, not across it: near it and running the same way.
          const q = nearestOnLine(p, z.points);
          const da = Math.abs(axis(a, b) - q.dir), turn = Math.min(da, 180 - da);
          hit = q.d <= LINE_BUFFER_M && turn <= PARALLEL_DEG;
        }
        if (hit) m += d / n;
      }
    }
    return m;
  }
  /** Prepared zones (cached boxes). Bad rows are dropped. */
  function prepare(zones) {
    return (zones || []).map(z => {
      const c = clean(z);
      if (!c.zone) return null;
      const out = { id: z.id || '', ...c.zone };
      out._box = bbox(out.points, out.kind === 'line' ? 0.0003 : 0);
      return out;
    }).filter(Boolean);
  }
  /** Router: does this tile segment ([..., points [[lon,lat],...]]) run inside a zone? */
  function segAvoid(zones) {
    const Z = prepare(zones);
    if (!Z.length) return null;
    return s => {
      const p = s && s[7];
      if (!p || p.length < 2) return false;
      const path = p.map(q => [q[1], q[0]]);
      let total = 0;
      for (let i = 1; i < path.length; i++) total += hav(path[i - 1], path[i]);
      for (const z of Z) {
        const m = metersInside(path, z);
        // Crossing a drawn road at an intersection is fine; running along it or into an area is not.
        if (z.kind === 'area' ? m > 1 : m >= Math.min(10, total * 0.5)) return true;
      }
      return false;
    };
  }
  /** Renter page: zones a route ([[lat,lon],...]) goes through, with meters inside each. */
  function routeHits(path, zones) {
    const out = [];
    for (const z of prepare(zones)) {
      const m = metersInside(path || [], z);
      if (m >= (z.kind === 'area' ? 3 : 10)) out.push({ id: z.id, name: z.name, note: z.note, kind: z.kind, meters: Math.round(m) });
    }
    return out;
  }
  /** Stops placed inside an area. */
  function stopsInside(stops, zones) {
    const Z = prepare(zones).filter(z => z.kind === 'area');
    const out = [];
    (stops || []).forEach((s, i) => {
      const p = [+s.lat, +s.lon];
      const z = Z.find(z => inBox(p, z._box) && inPoly(p, z.points));
      if (z) out.push({ index: i, label: s.label || s.name || '', zone: z.name });
    });
    return out;
  }
  /** Live: the zone the rider is in or within `m` meters of, or null. */
  function near(ll, zones, m) {
    const p = [+ll.lat, +ll.lon];
    let best = null;
    for (const z of prepare(zones)) {
      let d;
      if (z.kind === 'area') {
        if (inPoly(p, z.points)) d = 0;
        else { const ring = z.points.concat([z.points[0]]); d = distToLine(p, ring); }
      } else d = Math.max(0, distToLine(p, z.points) - LINE_BUFFER_M);
      if (d <= (m || 40) && (!best || d < best.meters)) best = { id: z.id, name: z.name, note: z.note, kind: z.kind, meters: Math.round(d) };
    }
    return best;
  }
  function warnText(hits) {
    if (!hits || !hits.length) return '';
    const names = hits.map(h => h.name);
    const list = names.length === 1 ? names[0] : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
    const notes = hits.map(h => h.note).filter(Boolean);
    return `⛔ This route goes through ${list}, which the shop marked off limits. There is no other legal way here.` + (notes.length ? ' Shop note: ' + notes.join(' ') : '');
  }
  return { MAX_ZONES, MAX_POINTS, LINE_BUFFER_M, clean, prepare, segAvoid, routeHits, stopsInside, near, warnText, inPoly, hav, areaKm2 };
});
