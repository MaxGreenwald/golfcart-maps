// HubSpot tracking and chat for portal 52245531.
// Public pages on golfcartmap.com insert the portal script on first view.
// This file does not show a consent banner, and it does not hide a banner
// HubSpot's own account may show. The native app, partner admin, other
// hosts, and internal or NO_TRACK sessions do not load the portal script.
(function () {
  var SRC = 'https://js.hs-scripts.com/52245531.js';
  var W = window;
  function lsGet(k) {
    try { return W.localStorage && W.localStorage.getItem(k); } catch (e) { return null; }
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
  function productionHost() {
    try { return (location.hostname || '') === 'golfcartmap.com'; } catch (e) { return false; }
  }
  function internal() {
    try { if (navigator.webdriver === true) return true; } catch (e) {}
    try {
      var marked = W.GCM_INTERNAL || lsGet('gcm-internal');
      if (marked && String(marked).trim()) return true;
    } catch (e) {}
    return false;
  }
  function operatorOff() {
    try { if (W.NO_TRACK) return true; } catch (e) {}
    return false;
  }
  function blocked() {
    return nativeApp() || adminPath() || !productionHost() || internal() || operatorOff();
  }
  function load() {
    var existing = document.getElementById('hs-script-loader');
    if (blocked()) {
      W.__gcmHs = 0;
      if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
      return;
    }
    if (W.__gcmHs || existing) { W.__gcmHs = 1; return; }
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
  function start() { load(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
