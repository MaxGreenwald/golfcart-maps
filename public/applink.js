// App links (Max t448u). Shared by p.js and the node tests.
// In the iOS app the page is served from capacitor://localhost, so shop API calls go to golfcartmap.com,
// and the app opens shop links as /p.html?slug=<slug>&code=... (see AppLinkRouter.swift).
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMAppLink = api;
})(typeof self !== 'undefined' ? self : this, function () {
  const SITE = 'https://golfcartmap.com';
  const APP_STORE = 'https://apps.apple.com/app/id6823958385';
  function isNative(win) {
    try { const C = win && win.Capacitor; return !!(C && C.isNativePlatform && C.isNativePlatform()); } catch (_) { return false; }
  }
  function apiBase(win) { return (isNative(win) ? SITE : '') + '/api/partner'; }
  /** Shop slug from /p/<slug>[/go] or, inside the app, p.html?slug=<slug>. */
  function slugFrom(pathname, search) {
    const parts = String(pathname || '').replace(/\/+$/, '').split('/').filter(Boolean);
    if (parts[0] === 'p' && parts[1]) return parts[1].toLowerCase();
    const q = new URLSearchParams(search || '').get('slug') || '';
    return /^[a-z0-9-]{1,64}$/i.test(q) ? q.toLowerCase() : '';
  }
  /** Show "Open in the app" only in iPhone/iPad Safari, never inside the app itself. */
  function wantsAppButton(win) {
    if (!win || isNative(win)) return false;
    const ua = (win.navigator && win.navigator.userAgent) || '';
    const touchMac = /Macintosh/.test(ua) && win.navigator && win.navigator.maxTouchPoints > 1;
    return /iPhone|iPad|iPod/.test(ua) || touchMac;
  }
  /** Custom-scheme link the button opens. Same-domain universal links stay in Safari, so this uses the scheme. */
  function handoffUrl(slug, token) {
    return `golfcartmaps://p/${encodeURIComponent(slug)}/go?handoff=${encodeURIComponent(token)}`;
  }
  return { SITE, APP_STORE, isNative, apiBase, slugFrom, wantsAppButton, handoffUrl };
});
