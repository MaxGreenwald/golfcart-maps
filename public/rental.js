// Rental code (Max t449u): renters type the code from the rental desk into Settings (or CarPlay),
// without needing the shop link. One code use; the answer is saved under 'gcm_partner_access',
// the same record p.js saves, which CarPlay Experiences and /p/<slug> read back.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMRental = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const KEY = 'gcm_partner_access', DAYS = 14;
  const native = w => { try { const C = w && w.Capacitor; return !!(C && C.isNativePlatform && C.isNativePlatform()); } catch (_) { return false; } };
  const apiBase = w => (native(w) ? 'https://golfcartmap.com' : '') + '/api/partner';
  /** Uppercase, no spaces or dashes; '' when it can't be a code. */
  function normalize(code) {
    const c = String(code || '').replace(/[\s-]+/g, '').toUpperCase();
    return /^[0-9A-Z]{4,16}$/.test(c) ? c : '';
  }
  function record(j, code, nowMs) {
    return { slug: j.slug || (j.shop && j.shop.slug) || '', code: j.code || code, at: nowMs, shop: j.shop,
      experiences: j.experiences || [], affiliates: j.affiliates || [], places: j.places || [] };
  }
  /** The saved unlock when it's still fresh (14 days), else null. */
  function load(storage, nowMs = Date.now()) {
    let a = null;
    try { a = JSON.parse(storage.getItem(KEY) || 'null'); } catch (_) {}
    if (!a || !a.slug || !Array.isArray(a.experiences) || !(nowMs - (+a.at || 0) < DAYS * 864e5)) return null;
    return a;
  }
  function remove(storage) {
    let a = null;
    try { a = JSON.parse(storage.getItem(KEY) || 'null'); } catch (_) {}
    try { storage.removeItem(KEY); if (a && a.slug) storage.removeItem('gcm_partner_grant:' + a.slug); } catch (_) {}
  }
  /** Unlock with a typed code: {ok:true, access} or {ok:false, reason}. Counts one code use. */
  async function enter(code, { fetch, storage, win, nowMs = Date.now() }) {
    const c = normalize(code);
    if (!c) return { ok: false, reason: 'That doesn’t look like a rental code.' };
    let r, j = {};
    try {
      r = await fetch(apiBase(win) + '/public-code/unlock?code=' + encodeURIComponent(c));
      try { j = await r.json(); } catch (_) {}
    } catch (_) { return { ok: false, reason: 'No connection. Try again in a moment.' }; }
    if (!r.ok || !j.unlocked) return { ok: false, reason: j.error || 'Could not unlock' };
    const access = record(j, c, nowMs);
    try {
      storage.setItem(KEY, JSON.stringify(access));
      if (j.grant) storage.setItem('gcm_partner_grant:' + access.slug, j.grant);
    } catch (_) {}
    return { ok: true, access };
  }
  /** Link to the shop's experiences page (bundled p.html in the app). */
  function shopUrl(slug, win) { return native(win) ? '/p.html?slug=' + encodeURIComponent(slug) : '/p/' + encodeURIComponent(slug); }

  // Settings row (index.html #rentRow), wired when present.
  function mountSettings(doc, win) {
    const row = doc.getElementById('rentRow');
    if (!row) return;
    const st = win.localStorage;
    const paint = (msg, err) => {
      const a = load(st);
      const n = a ? a.experiences.length : 0;
      row.querySelector('#rentSub').textContent = msg || (a
        ? `${(a.shop && a.shop.name) || a.slug} is active: ${n} experience${n === 1 ? '' : 's'}. Also in CarPlay.`
        : 'Got a code from your rental shop? Enter it to unlock its rides here and in CarPlay.');
      row.querySelector('#rentSub').classList.toggle('err', !!err);
      row.querySelector('#rentForm').hidden = !!a;
      row.querySelector('#rentOn').hidden = !a;
      if (a) row.querySelector('#rentView').href = shopUrl(a.slug, win);
    };
    row.querySelector('#rentForm').addEventListener('submit', async e => {
      e.preventDefault();
      const inp = row.querySelector('#rentCode'), btn = row.querySelector('#rentGo');
      btn.disabled = true; paint('Checking…');
      const res = await enter(inp.value, { fetch: win.fetch.bind(win), storage: st, win });
      btn.disabled = false;
      if (!res.ok) { paint(res.reason, true); return; }
      inp.value = ''; paint();
      win.location.href = shopUrl(res.access.slug, win);
    });
    row.querySelector('#rentRemove').addEventListener('click', () => { remove(st); paint(); });
    paint();
  }
  if (typeof document !== 'undefined' && typeof window !== 'undefined') {
    const go = () => mountSettings(document, window);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go); else go();
  }
  return { KEY, DAYS, normalize, record, load, remove, enter, shopUrl, apiBase, mountSettings };
});
