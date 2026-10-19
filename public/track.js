// Golf Cart Maps usage analytics (web, iPhone app, CarPlay). Privacy rules, enforced again server-side
// in lib/analytics.js: no cookies; no names, emails, notes, IPs or coordinates; town level only.
// One random install id + a 30-minute session id live in localStorage. Honors Global Privacy
// Control and Do Not Track, and the "gcm-notrack" localStorage flag. Failures never touch the app.
(function () {
  const W = window, LS = (() => { try { return W.localStorage } catch (_) { return null } })();
  const get = k => { try { return LS && LS.getItem(k) } catch (_) { return null } }, set = (k, v) => { try { LS && LS.setItem(k, v) } catch (_) {} };
  const rid = () => { try { return crypto.randomUUID() } catch (_) { return 'r' + Math.random().toString(36).slice(2) + Date.now().toString(36) } };
  const native = () => { try { return !!(W.Capacitor && W.Capacitor.isNativePlatform && W.Capacitor.isNativePlatform()) } catch (_) { return false } };
  const platform = () => { if (!native()) return 'web'; try { const p = W.Capacitor.getPlatform(); return p === 'android' ? 'android' : 'ios' } catch (_) { return 'ios' } };
  const pwa = () => { try { return !!(matchMedia('(display-mode: standalone)').matches || navigator.standalone) } catch (_) { return false } };
  const optedOut = () => !!(W.NO_TRACK || get('gcm-notrack') || navigator.globalPrivacyControl === true || navigator.doNotTrack === '1');
  const SESSION_MS = 30 * 60000;
  let newInstall = false;
  function installId() { let i = get('gcm-iid'); if (!i) { i = rid(); set('gcm-iid', i); newInstall = true } return i }
  function session(now) {   // returns [id, isNew]
    let j = null; try { j = JSON.parse(get('gcm-sess') || 'null') } catch (_) {}
    const fresh = !j || !j.id || now - (j.t || 0) > SESSION_MS; if (fresh) j = { id: rid(), t: now }; j.t = now; set('gcm-sess', JSON.stringify(j)); return [j.id, fresh];
  }
  const tok = v => (v || '').toString().trim().toLowerCase().slice(0, 40);
  function source() {   // UTM params, referrer host (never the full URL), landing town page
    const q = new URLSearchParams(location.search), p = {};
    for (const k of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']) if (q.get(k)) p[k] = tok(q.get(k));
    try { if (document.referrer) { const h = new URL(document.referrer).hostname; if (h && h !== location.hostname) p.ref = h } } catch (_) {}
    p.landing = (location.pathname || '/').split('/')[1] || 'home';
    let ft = null; try { ft = JSON.parse(get('gcm-ft') || 'null') } catch (_) {}
    if (!ft) { ft = { s: p.utm_source || (p.ref ? 'ref:' + p.ref.slice(0, 30) : (native() ? 'app' : 'direct')), m: p.utm_medium || '', c: p.utm_campaign || '' }; set('gcm-ft', JSON.stringify(ft)) }
    if (ft.s) p.ft_source = tok(ft.s.replace(/[^a-z0-9._:-]/gi, '_')).replace(/:/g, '_'); if (ft.m) p.ft_medium = ft.m; if (ft.c) p.ft_campaign = ft.c;
    return p;
  }
  const ENDPOINT = () => W.GCM_ANALYTICS_URL || (native() || location.protocol === 'file:' ? 'https://golfcartmap.com/api/e' : '/api/e');
  function send(o) {
    const b = JSON.stringify(o); (W.__gcmSent = W.__gcmSent || []).push(o);
    if (W.GCM_TRACK_SINK) { try { W.GCM_TRACK_SINK(o) } catch (_) {} return }
    const url = ENDPOINT();
    try { if (navigator.sendBeacon && navigator.sendBeacon(url, new Blob([b], { type: 'text/plain' }))) return } catch (_) {}
    try { fetch(url, { method: 'POST', body: b, keepalive: true, headers: { 'content-type': 'text/plain' } }).catch(() => {}) } catch (_) {}
  }
  /** track(event, props, opts): opts.platform overrides ('carplay'); opts.town overrides the current region. */
  function track(e, props, opts) {
    try {
      if (optedOut()) return;
      opts = opts || {}; const now = Date.now(), i = installId(), [s, fresh] = session(now);
      const town = opts.town !== undefined ? opts.town : (W.REG && W.REG.id) || null, pl = opts.platform || platform();
      if (fresh && e !== 'session') send({ v: 1, e: 'session', t: town, pl, pwa: pwa(), i, s, p: Object.assign(source(), { new_install: newInstall }) });
      if (e === 'session') { if (!fresh && !opts.force) return; props = Object.assign(source(), { new_install: newInstall }, props || {}) }
      send({ v: 1, e, t: town, pl, pwa: pwa(), i, s, p: props || {} });
    } catch (_) {}
  }
  W.GCMTrack = { track, _source: source, _optedOut: optedOut };
  // a new visit = a session; returning to the app after 30 idle minutes starts a new one
  // (app.js sends town_viewed as soon as a town loads, which opens the session with its town; this is the fallback)
  setTimeout(() => track('session'), 5000);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') track('session') });
})();
