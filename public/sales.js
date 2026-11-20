// Sales mode for cart dealers: a shareable /s/<shop>?at=<lat>,<lon>&home=<label> page that shows
// the legal roads a cart can reach from that home, with a "buy from this shop" card.
// Shared by the partner Worker (validation), the admin (settings and link maker) and /s/ (s.js).
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMSales = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const DEFAULTS = { on: false, headline: '', blurb: '', url: '', phone: '', cta: 'Buy from this shop', reach_mi: 5 };
  const MAX = { headline: 80, blurb: 400, url: 300, phone: 40, cta: 40 };
  const LABEL = { headline: 'Headline', blurb: 'About', url: 'Shop link', phone: 'Sales phone', cta: 'Button' };
  const REACH = [2, 3, 5, 8, 10, 15];
  function one(s) { return String(s == null ? '' : s).replace(/[\r\n\t]+/g, ' ').replace(/ {2,}/g, ' ').trim(); }
  /** { sales } or { error }. Missing keys keep the defaults. */
  function clean(body) {
    const b = body && typeof body === 'object' ? body : {};
    const out = { ...DEFAULTS, on: !!b.on };
    for (const k of ['headline', 'blurb', 'url', 'phone', 'cta']) {
      if (b[k] === undefined) continue;
      const v = one(b[k]);
      if ([...v].length > MAX[k]) return { error: LABEL[k] + ' is too long' };
      out[k] = v;
    }
    if (!out.cta) out.cta = DEFAULTS.cta;
    if (out.url) {
      let u;
      try { u = new URL(out.url); } catch (e) { return { error: 'Shop link must be a web address (https://...)' }; }
      if (u.protocol !== 'https:') return { error: 'Shop link must start with https://' };
      out.url = u.href;
    }
    if (out.phone) {
      const d = out.phone.replace(/\D/g, '');
      if (d.length < 7 || d.length > 15 || !/^[0-9+().\-\s]+$/.test(out.phone)) return { error: 'Sales phone should be a phone number' };
    }
    if (b.reach_mi !== undefined) {
      const n = Number(b.reach_mi);
      if (!REACH.includes(n)) return { error: 'Reach must be one of ' + REACH.join(', ') + ' miles' };
      out.reach_mi = n;
    }
    return { sales: out };
  }
  function fromRow(raw) {
    let o = {};
    if (raw && typeof raw === 'object') o = raw;
    else { try { o = JSON.parse(raw || '{}') || {}; } catch (e) { o = {}; } }
    const c = clean(o);
    return c.sales || { ...DEFAULTS };
  }
  function round(n) { return Math.round(+n * 1e5) / 1e5; }
  /** Link a dealer sends: /s/<slug>?at=lat,lon&home=label (the address is the label only). */
  function link(origin, slug, home) {
    const q = new URLSearchParams();
    if (home && Number.isFinite(+home.lat) && Number.isFinite(+home.lon)) q.set('at', round(home.lat) + ',' + round(home.lon));
    if (home && home.label) q.set('home', one(home.label).slice(0, 80));
    const s = q.toString();
    return (origin || '') + '/s/' + encodeURIComponent(slug) + (s ? '?' + s : '');
  }
  /** Parse the page URL: { slug, home: {lat, lon, label} | null }. */
  function parse(pathname, search) {
    const m = /^\/s\/([^/?#]+)/.exec(pathname || '');
    const slug = m ? decodeURIComponent(m[1]).toLowerCase() : '';
    const q = new URLSearchParams(search || '');
    const at = /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/.exec(q.get('at') || '');
    let home = null;
    if (at && Math.abs(+at[1]) <= 90 && Math.abs(+at[2]) <= 180) home = { lat: +at[1], lon: +at[2], label: one(q.get('home') || '').slice(0, 80) };
    return { slug, home };
  }
  function telHref(p) { const d = String(p || '').replace(/[^0-9+]/g, ''); return d ? 'tel:' + d : ''; }
  return { DEFAULTS, REACH, clean, fromRow, link, parse, telHref };
});
