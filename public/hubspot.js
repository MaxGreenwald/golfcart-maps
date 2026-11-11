// Public-site HubSpot tracking loader (portal 52245531).
// Inserts the portal script once, at the end of body. Town changes on the map
// use history.pushState and do not run this file again; load() is also idempotent.
// Skips the native app, partner admin, non-public hosts, and the same opt-out
// signals as public/track.js. Does not add a chat widget.
(function () {
  var SRC = 'https://js.hs-scripts.com/52245531.js';
  var W = window;
  function lsGet(k) {
    try { return W.localStorage && W.localStorage.getItem(k); } catch (e) { return null; }
  }
  function optedOut() {
    try {
      if (W.NO_TRACK) return true;
      if (navigator.globalPrivacyControl === true) return true;
      if (navigator.doNotTrack === '1') return true;
      if (lsGet('gcm-notrack')) return true;
    } catch (e) {}
    return false;
  }
  function nativeApp() {
    try {
      if (W.Capacitor && W.Capacitor.isNativePlatform && W.Capacitor.isNativePlatform()) return true;
      var proto = location.protocol || '';
      if (proto === 'file:' || proto === 'capacitor:' || proto === 'ionic:') return true;
    } catch (e) {}
    return false;
  }
  function adminPath() {
    try { return /^\/partner(?:\/|$)/.test(location.pathname || ''); } catch (e) { return false; }
  }
  function publicHost() {
    try {
      var h = location.hostname || '';
      return h === 'golfcartmap.com' || h === 'www.golfcartmap.com';
    } catch (e) { return false; }
  }
  function internal() {
    try { if (navigator.webdriver === true) return true; } catch (e) {}
    try {
      var marked = W.GCM_INTERNAL || lsGet('gcm-internal');
      if (marked && String(marked).trim()) return true;
    } catch (e) {}
    return false;
  }
  function load() {
    if (W.__gcmHs) return;
    if (document.getElementById('hs-script-loader')) { W.__gcmHs = 1; return; }
    if (!publicHost() || nativeApp() || adminPath() || optedOut() || internal()) return;
    W.__gcmHs = 1;
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.id = 'hs-script-loader';
    s.async = true;
    s.defer = true;
    s.src = SRC;
    (document.body || document.documentElement).appendChild(s);
  }
  W.GCMHubSpot = { load: load };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
