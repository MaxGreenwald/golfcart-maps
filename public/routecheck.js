// Rough ride check while a shop edits an experience.
// Miles come from the same legal-road router the renter page uses (public/router.js).
// Time and battery are estimates: 12 mph for a golf cart, 18 mph for an LSV, against a 30 mile charge.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMRouteCheck = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const MPH = { golf_cart: 12, lsv: 18 };
  const RANGE_MI = 30;
  const MI = 1609.344;

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function hav(a, b) {
    // points are [lat, lon], same as router geometry and public/nav.js
    const R = 6371000, rad = Math.PI / 180;
    const dlat = (b[0] - a[0]) * rad, dlon = (b[1] - a[1]) * rad;
    const x = Math.sin(dlat / 2) ** 2 + Math.cos(a[0] * rad) * Math.cos(b[0] * rad) * Math.sin(dlon / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(x)));
  }

  function metersOf(points) {
    let m = 0;
    for (let i = 1; i < (points || []).length; i++) m += hav(points[i - 1], points[i]);
    return m;
  }

  function vehicleOf(v) { return v === 'lsv' ? 'lsv' : 'golf_cart'; }
  function vehPhrase(v) { return v === 'lsv' ? 'street-legal LSV' : 'golf cart'; }

  /**
   * stops: ordered pins the shop would save. legs[i] is the router hop into stops[i + 1]
   * (same shape as GCMRouter.openRegion().legs: { points, dashed }).
   */
  function summarize(stops, legs, vehicle) {
    const veh = vehicleOf(vehicle);
    const list = stops || [];
    const hops = legs || [];
    let meters = 0;
    let routed = 0;
    let gaps = 0;
    const flags = [];
    for (let i = 0; i < Math.max(0, list.length - 1); i++) {
      const leg = hops[i];
      const dest = list[i + 1] || {};
      const label = String(dest.label || ('Stop ' + (i + 2)));
      if (!leg || !leg.points || leg.points.length < 2) {
        flags.push({ index: i + 1, label, reason: 'no_legal_route' });
        continue;
      }
      meters += metersOf(leg.points);
      routed++;
      if (leg.dashed) gaps++;
    }
    const miles = meters / MI;
    const mph = MPH[veh];
    const minutes = miles > 0 ? (miles / mph) * 60 : 0;
    const batteryPct = (miles / RANGE_MI) * 100;
    return { miles, minutes, batteryPct, mph, rangeMi: RANGE_MI, vehicle: veh, flags, gaps, routedHops: routed, stops: list.length };
  }

  function lines(summary) {
    const s = summary || summarize([], [], 'golf_cart');
    const who = vehPhrase(s.vehicle);
    if (!s.stops || s.stops < 2) {
      return { headline: 'Add two placed stops to check miles, ride time, and battery.', detail: '' };
    }
    if (!s.routedHops) {
      return {
        headline: 'No legal ' + who + ' route between these stops.',
        detail: 'Posted signs always take precedence.',
      };
    }
    const mi = s.miles < 0.1 ? 'Under 0.1' : (s.miles < 10 ? s.miles.toFixed(1) : String(Math.round(s.miles)));
    const min = s.minutes < 1 ? 'under 1' : String(Math.max(1, Math.round(s.minutes)));
    const bat = s.batteryPct < 1 ? 'under 1' : String(Math.max(1, Math.round(s.batteryPct)));
    const gap = s.gaps ? ' Includes a short gap with no road drawn.' : '';
    return {
      headline: 'About ' + mi + ' mi. About ' + min + ' min at ' + s.mph + ' mph. About ' + bat + '% of a ' + s.rangeMi + ' mi charge.',
      detail: 'Rough check for a ' + who + ' on legal roads.' + gap + ' Posted signs always take precedence.',
    };
  }

  function html(summary) {
    const s = summary || summarize([], [], 'golf_cart');
    const t = lines(s);
    const flags = (s.flags || []).map(f =>
      '<li>Stop ' + (f.index + 1) + ' ' + esc(f.label) + ': no legal ' + esc(vehPhrase(s.vehicle)) + ' route from the stop before it.</li>'
    ).join('');
    return '<p class="route-miles">' + esc(t.headline) + '</p>' +
      (t.detail ? '<p class="muted">' + esc(t.detail) + '</p>' : '') +
      (flags ? '<ul class="route-flags">' + flags + '</ul>' : '');
  }

  async function check(opts) {
    const o = opts || {};
    const fetchFn = o.fetchImpl || fetch;
    const Router = o.router || (typeof globalThis !== 'undefined' ? globalThis.GCMRouter : null);
    if (!Router || !Router.openRegion) throw new Error('Router did not load');
    const [regions, rules] = await Promise.all([
      fetchFn('/data/regions.json').then(r => { if (!r.ok) throw new Error('regions'); return r.json(); }),
      fetchFn('/data/rules.json').then(r => { if (!r.ok) throw new Error('rules'); return r.json(); }),
    ]);
    const region = (regions || []).find(r => r.id === o.regionId) || (regions || []).find(r => r.id === 'sd');
    if (!region) throw new Error('Unknown city');
    const vehicle = vehicleOf(o.vehicle);
    const stops = (o.stops || []).filter(s => Number.isFinite(+s.lat) && Number.isFinite(+s.lon)).map(s => ({
      label: s.label || '', lat: +s.lat, lon: +s.lon,
    }));
    if (stops.length < 2) return summarize(stops, [], vehicle);
    const api = await Router.openRegion(region, rules, vehicle, fetchFn);
    const legs = await api.legs(stops);
    return summarize(stops, legs, vehicle);
  }

  return { MPH, RANGE_MI, esc, summarize, lines, html, check, vehicleOf, vehPhrase };
});
