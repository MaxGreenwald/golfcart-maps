// Local-first place search (Max, Oct 31 2026, t413u): results near you come first.
// Bias point: your location if known, else the start point, else the map center.
// Remote geocoder: Photon (komoot) with a ~50 mi box around the bias point, Nominatim fallback.
// Results are reranked by distance; anything past NEAR_MI goes below a "Farther away" label.
(function (root, f) { const m = f(); if (typeof module === 'object' && module.exports) module.exports = m; else root.GCMGeo = m; })(this, function () {
  const NEAR_MI = 50, BOX_DEG = 0.75;
  const R = 3958.8, rad = d => d * Math.PI / 180;
  function miles(a, b) {
    const dl = rad(b.lat - a.lat), dn = rad(b.lon - a.lon);
    const h = Math.sin(dl / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  const ok = p => p && isFinite(p.lat) && isFinite(p.lon);
  // me / start / center: {lat, lon} or null. First known one wins.
  function biasPoint(me, start, center) { return [me, start, center].find(ok) || null; }
  function box(p) { return [p.lon - BOX_DEG, p.lat - BOX_DEG, p.lon + BOX_DEG, p.lat + BOX_DEG]; }
  function photonUrl(q, p, limit, bounded) {
    let u = `https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=${limit || 8}`;
    if (p) { u += `&lat=${p.lat}&lon=${p.lon}&zoom=12&location_bias_scale=0.1`; if (bounded !== false) u += `&bbox=${box(p).join(',')}`; }
    return u;
  }
  function nominatimUrl(q, p, limit) {
    let u = `https://nominatim.openstreetmap.org/search?format=json&limit=${limit || 6}&q=${encodeURIComponent(q)}`;
    if (p) { const b = box(p); u += `&viewbox=${b[0]},${b[3]},${b[2]},${b[1]}&bounded=1`; }
    return u;
  }
  function fromPhoton(j) {
    return ((j && j.features) || []).map(f => { const p = f.properties || {};
      return { name: p.name || [p.housenumber, p.street].filter(Boolean).join(' '),
        sub: [p.housenumber && p.name ? p.street : null, p.city || p.district, p.state, p.osm_value].filter(Boolean).join(' · '),
        lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }; }).filter(x => x.name);
  }
  function fromNominatim(j) {
    return (j || []).map(x => ({ name: x.display_name.split(',')[0], sub: x.display_name.split(',').slice(1, 3).join(','), lat: +x.lat, lon: +x.lon }));
  }
  // Sort by distance from p (text score breaks near-ties), split into near and far.
  function rank(list, p, nearMi) {
    const lim = nearMi || NEAR_MI;
    const xs = list.filter(ok).map(x => ({ ...x, mi: p ? miles(p, x) : 0 }));
    xs.sort((a, b) => (a.mi + (a.score || 0) * 0.3) - (b.mi + (b.score || 0) * 0.3));
    return { near: xs.filter(x => x.mi <= lim), far: xs.filter(x => x.mi > lim) };
  }
  function dedupe(list, norm) { const seen = new Set(); return list.filter(x => { const k = norm(x.name) + '|' + x.lat.toFixed(3) + ',' + x.lon.toFixed(3); if (seen.has(k)) return false; seen.add(k); return true; }); }
  // fetchJson(url, signal) => json. Bounded near search first; an unbounded search only when nothing is near.
  async function remote(q, p, fetchJson, signal) {
    let near = [];
    try { near = fromPhoton(await fetchJson(photonUrl(q, p), signal)); }
    catch (e) { if (signal && signal.aborted) throw e; try { near = fromNominatim(await fetchJson(nominatimUrl(q, p), signal)); } catch (e2) { if (signal && signal.aborted) throw e2; } }
    if (near.length || !p) return near;
    try { return fromPhoton(await fetchJson(photonUrl(q, p, 6, false), signal)); } catch (e) { if (signal && signal.aborted) throw e; return []; }
  }
  return { NEAR_MI, miles, biasPoint, photonUrl, nominatimUrl, fromPhoton, fromNominatim, rank, dedupe, remote };
});
