// anywhere.js: the map outside our mapped towns (Max t590u/t591u, Nov 22 2026).
// In the US but outside every region, the app still works: the map, search and location behave as usual and
// a route comes from general OpenStreetMap road data (Valhalla, FOSSGIS public server) with the scooter profile:
// no freeways, main roads avoided where a smaller road works. We have no golf cart or LSV speed data there,
// so the route is NOT checked against local rules and every such route shows WARNING.
// Outside the US the app keeps saying the spot is not covered (US_ONLY).
// Used by app.js (web, iPhone and CarPlay share it) and tests/anywhere.test.mjs.
(function (root) {
  const ID = 'other';
  const ENDPOINT = 'https://valhalla1.openstreetmap.de/route';
  const TIMEOUT_MS = 12000;
  // Short and accurate (Max: friendly, not alarming). Plain text; app.js escapes nothing else into it.
  const WARNING = 'We don\u2019t have golf cart and LSV speed data for this area yet, so this route isn\u2019t checked against local rules. Check posted speed limits and local laws.';
  const BANNER = 'We don\u2019t have golf cart and LSV speed data for this area yet. You can still plan a route.';
  const US_ONLY = 'Golf Cart Maps covers the US only for now.';
  const TOO_FAR = 'That trip is too long to plan here. Try a destination within 25 mi.';
  const MAX_MI = 25;

  // Coarse US outline ([lon, lat] rings). Good to a few km along the Canada and Mexico borders,
  // which is fine for "can we offer a route here"; routing itself follows real roads.
  const US = [
    // Lower 48
    [[-124.8, 48.4], [-123.3, 48.25], [-123.2, 48.7], [-123.05, 49.0], [-95.15, 49.0], [-95.15, 49.38], [-94.8, 49.32], [-93.6, 48.6],
     [-92.0, 48.3], [-89.6, 48.0], [-88.4, 48.3], [-84.9, 46.9], [-84.4, 46.5], [-83.6, 46.1], [-82.5, 45.3], [-82.4, 43.0],
     [-82.5, 42.6], [-83.1, 42.3], [-83.1, 42.0], [-81.3, 42.2], [-79.8, 42.5], [-79.05, 42.9], [-79.05, 43.25], [-77.0, 43.6],
     [-76.3, 44.2], [-75.0, 45.0], [-71.5, 45.0], [-71.1, 45.3], [-70.0, 46.7], [-69.2, 47.45], [-68.3, 47.35], [-67.8, 47.07],
     [-67.8, 45.7], [-67.4, 45.15], [-66.95, 44.8], [-67.0, 44.2], [-68.5, 42.0], [-72.0, 39.0], [-75.0, 34.0], [-79.0, 30.0],
     [-79.9, 27.0], [-80.0, 25.0], [-80.2, 24.3], [-83.2, 24.3], [-84.5, 25.5], [-90.0, 28.5], [-94.0, 28.5], [-97.15, 25.95],
     [-97.5, 25.88], [-99.1, 26.4], [-99.5, 27.5], [-100.3, 28.3], [-100.9, 29.3], [-101.4, 29.77], [-102.3, 29.9], [-102.7, 29.6],
     [-103.1, 28.98], [-104.0, 29.3], [-104.7, 30.0], [-105.0, 30.7], [-106.0, 31.4], [-106.5, 31.78], [-108.2, 31.78], [-108.2, 31.33],
     [-111.07, 31.33], [-114.8, 32.49], [-114.72, 32.72], [-117.12, 32.53], [-118.0, 32.3], [-121.0, 34.0], [-124.5, 40.3],
     [-124.9, 42.0], [-124.9, 46.0]],
    // Alaska (west of 141 W) and the panhandle
    [[-170.0, 51.0], [-141.0, 51.0], [-141.0, 60.3], [-139.0, 60.0], [-137.5, 59.0], [-135.5, 59.8], [-133.4, 58.4], [-131.8, 56.6],
     [-130.0, 55.9], [-130.0, 54.6], [-134.0, 54.3], [-141.0, 58.0], [-141.0, 71.5], [-170.0, 71.5]],
    // Hawaii
    [[-160.6, 18.8], [-154.6, 18.8], [-154.6, 22.4], [-160.6, 22.4]],
    // Puerto Rico and US Virgin Islands
    [[-67.4, 17.6], [-64.5, 17.6], [-64.5, 18.6], [-67.4, 18.6]],
  ];
  function inRing(x, y, P) {
    let c = false;
    for (let i = 0, j = P.length - 1; i < P.length; j = i++) {
      const [x1, y1] = P[i], [x2, y2] = P[j];
      if ((y1 > y) !== (y2 > y) && x < (x2 - x1) * (y - y1) / (y2 - y1) + x1) c = !c;
    }
    return c;
  }
  function inUS(lat, lon) { return isFinite(lat) && isFinite(lon) && US.some(r => inRing(lon, lat, r)); }

  // A region (data/regions.json row) whose bbox holds the point. Hidden regions only when keepId names them.
  function regionCovering(regions, lat, lon, keepId) {
    for (const r of regions || []) {
      if (r.hidden && r.id !== keepId) continue;
      const b = r.bbox;
      if (b && lat >= b[0] && lat <= b[2] && lon >= b[1] && lon <= b[3]) return r;
    }
    return null;
  }

  // The pseudo-region the app loads for an unmapped US spot.
  function region(lat, lon) {
    return { id: ID, name: 'Other US area', short: 'Other US area', state: '_any', general: true,
      center: [lat, lon], zoom: 15, bbox: null, cover: BANNER };
  }
  // Generic thresholds shown in settings; general routes are not checked against them.
  const RULES = { name: 'This area',
    lsv: { max_posted: 35, cross: true, cite: 'No local rule on file for this area. Check state and local law.' },
    golf_cart: { max_posted: 25, cross: true, cite: 'No local rule on file for this area. Check state and local law.' } };

  function miles(a, b) {
    const r = Math.PI / 180, dl = (b.lat - a.lat) * r, dn = (b.lng - a.lng) * r;
    const h = Math.sin(dl / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dn / 2) ** 2;
    return 2 * 3958.8 * Math.asin(Math.sqrt(h));
  }

  // Valhalla request body. motor_scooter: no motorways; use_primary 0 keeps to smaller roads when one connects;
  // top_speed 56 km/h (35 mph) is the time estimate cap for an LSV, 40 km/h (25 mph) for a golf cart.
  function request(a, b, veh) {
    return { locations: [{ lat: +a.lat.toFixed(6), lon: +a.lng.toFixed(6) }, { lat: +b.lat.toFixed(6), lon: +b.lng.toFixed(6) }],
      costing: 'motor_scooter',
      costing_options: { motor_scooter: { use_primary: 0, use_hills: 0.5, top_speed: veh === 'golf_cart' ? 40 : 56 } },
      directions_options: { units: 'kilometers' } };
  }

  // Google encoded polyline, precision 6 (Valhalla). Returns [[lon, lat], ...].
  function decode(str) {
    const out = []; let i = 0, lat = 0, lon = 0;
    while (i < str.length) {
      for (const k of [0, 1]) {
        let shift = 0, res = 0, b;
        do { b = str.charCodeAt(i++) - 63; res |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
        const d = (res & 1) ? ~(res >> 1) : (res >> 1);
        if (k === 0) lat += d; else lon += d;
      }
      out.push([+(lon / 1e6).toFixed(6), +(lat / 1e6).toFixed(6)]);
    }
    return out;
  }

  // Valhalla trip -> app segments, one per maneuver: [nameIdx, 'road', 0, 'g', 0, nodeA, nodeB, coords].
  // Speed 0 + source 'g' (general) so roadrule.js counts it as allowed and the app draws one plain blue line:
  // no risky or "speed unknown" marks, because the one WARNING covers the whole route.
  function toSegs(trip) {
    const names = [''], segs = [], idx = new Map([['', 0]]);
    const nm = n => { if (!idx.has(n)) { idx.set(n, names.length); names.push(n); } return idx.get(n); };
    let node = 1;
    for (const leg of (trip && trip.legs) || []) {
      const pts = decode(leg.shape || '');
      for (const m of leg.maneuvers || []) {
        const a = m.begin_shape_index, b = m.end_shape_index;
        if (!(b > a) || !pts[a] || !pts[b]) continue;
        const name = (m.street_names && m.street_names[0]) || '';
        segs.push([nm(name), 'road', 0, 'g', 0, node, node + 1, pts.slice(a, b + 1)]);
        node++;
      }
    }
    return { names, segs };
  }

  // fetchFn(url, init) => Response. Returns {ok:true, names, segs} or {ok:false, reason:'too_far'|'no_route'|'network'}.
  async function route(a, b, o) {
    o = o || {};
    if (miles(a, b) > MAX_MI) return { ok: false, reason: 'too_far' };
    const f = o.fetch || (typeof fetch === 'function' ? fetch.bind(root) : null);
    if (!f) return { ok: false, reason: 'network' };
    const ac = typeof AbortController === 'function' ? new AbortController() : null;
    const t = ac ? setTimeout(() => ac.abort(), o.timeout || TIMEOUT_MS) : null;
    try {
      // POST with text/plain: no CORS preflight, and the service worker never caches it (it only caches GET).
      const r = await f(o.endpoint || ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify(request(a, b, o.veh)), signal: ac ? ac.signal : undefined });
      const j = await r.json().catch(() => null);
      if (!r.ok || !j || !j.trip) return { ok: false, reason: j && j.error_code ? 'no_route' : 'network' };
      const out = toSegs(j.trip);
      if (!out.segs.length) return { ok: false, reason: 'no_route' };
      return { ok: true, ...out };
    } catch (e) {
      return { ok: false, reason: 'network' };
    } finally { if (t) clearTimeout(t); }
  }

  const api = { ID, ENDPOINT, WARNING, BANNER, US_ONLY, TOO_FAR, MAX_MI, RULES, inUS, regionCovering, region, request, decode, toSegs, route, miles };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.GCMAnywhere = api;
})(typeof window !== 'undefined' ? window : globalThis);
