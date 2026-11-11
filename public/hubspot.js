// Public-site HubSpot loader (portal 52245531).
// The script is not inserted until this browser has an explicit allow,
// and a privacy signal (GPC, Do Not Track, gcm-notrack, NO_TRACK) blocks it.
// Native app, partner admin, and non-public hosts are skipped.
// Town changes use history.pushState and do not insert a second tag.
(function () {
  var SRC = 'https://js.hs-scripts.com/52245531.js';
  var KEY = 'gcm-hubspot';
  // Analytics and chat cookies named in HubSpot's cookie documentation.
  // __hs_do_not_track is left in place: that cookie is the stop signal.
  var CLEAR = ['__hstc', 'hubspotutk', '__hssc', '__hssrc', 'messagesUtk', 'hs-messages-is-open', 'hs-messages-hide-welcome-message', '__hs_cookie_cat_pref', '__hs_initial_opt_in'];
  var W = window;
  function lsGet(k) {
    try { return W.localStorage && W.localStorage.getItem(k); } catch (e) { return null; }
  }
  function lsSet(k, v) {
    try { if (W.localStorage) W.localStorage.setItem(k, v); } catch (e) {}
  }
  function privacySignal() {
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
  function excluded() { return !publicHost() || nativeApp() || adminPath() || internal(); }
  function choice() {
    var v = lsGet(KEY);
    return v === 'allow' || v === 'deny' ? v : '';
  }
  function onPolicy() {
    var p = location.pathname || '';
    return p === '/privacy' || p === '/privacy/';
  }
  function load() {
    var ok = !excluded() && !privacySignal() && choice() === 'allow';
    var existing = document.getElementById('hs-script-loader');
    if (!ok) {
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
  function allow() {
    if (excluded() || privacySignal()) return;
    lsSet(KEY, 'allow');
    var q = (W._hsq = W._hsq || []);
    q.push(['doNotTrack', { track: true }]);
    load();
    render();
  }
  function clearCookies() {
    var host = '';
    try { host = location.hostname || ''; } catch (e) {}
    var domains = [''];
    if (host) domains.push(host);
    if (host.indexOf('.') > 0) domains.push('.' + host.replace(/^www\./, ''));
    for (var i = 0; i < CLEAR.length; i++) {
      for (var d = 0; d < domains.length; d++) {
        var tail = '; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
        if (domains[d]) tail += '; domain=' + domains[d];
        try { document.cookie = CLEAR[i] + '=' + tail; } catch (e) {}
      }
    }
  }
  function stopHubSpot() {
    try {
      var q = (W._hsq = W._hsq || []);
      q.push(['doNotTrack']);
      q.push(['revokeCookieConsent']);
      var hsp = (W._hsp = W._hsp || []);
      hsp.push(['revokeCookieConsent']);
    } catch (e) {}
    try {
      if (W.HubSpotConversations && W.HubSpotConversations.widget && W.HubSpotConversations.widget.remove) W.HubSpotConversations.widget.remove();
    } catch (e) {}
    clearCookies();
  }
  function deny() {
    if (excluded()) return;
    lsSet(KEY, 'deny');
    stopHubSpot();
    load();
    render();
  }
  function css() {
    if (document.getElementById('gcm-hs-style')) return;
    var tag = document.createElement('style');
    tag.id = 'gcm-hs-style';
    tag.textContent = '#gcm-hs{box-sizing:border-box;font:16px/1.45 system-ui,-apple-system,sans-serif;color:#17384a}'
      + '#gcm-hs.float{position:fixed;z-index:5000;left:max(12px,env(safe-area-inset-left));right:max(12px,env(safe-area-inset-right));bottom:max(12px,env(safe-area-inset-bottom));max-width:36rem;margin:0 auto;background:#fff;border:2px solid #0b6e86;border-radius:16px;padding:14px 14px 12px;box-shadow:0 8px 28px rgba(11,60,80,.2)}'
      + '#gcm-hs.float.revoke{right:auto;width:max-content;max-width:16rem;padding:10px 12px}'
      + '#gcm-hs.page{position:static;background:#fff;border:2px solid #0b6e86;border-radius:16px;padding:14px;margin:12px 0 0}'
      + '#gcm-hs p{margin:0 0 10px}'
      + '#gcm-hs .row{display:flex;flex-wrap:wrap;gap:8px}'
      + '#gcm-hs button{flex:1 1 10rem;min-height:44px;margin:0;padding:10px 12px;font:700 16px/1.2 system-ui,-apple-system,sans-serif;border-radius:12px;border:2px solid #0b6e86;background:#fff;color:#0b3d4d;cursor:pointer}'
      + '#gcm-hs button:focus-visible{outline:3px solid #14b8c4;outline-offset:2px}';
    (document.head || document.body || document.documentElement).appendChild(tag);
  }
  function para(text) {
    var p = document.createElement('p');
    p.textContent = text;
    return p;
  }
  function button(label, fn) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'gcm-hs-btn';
    b.textContent = label;
    b.addEventListener('click', fn);
    return b;
  }
  function row(btns) {
    var d = document.createElement('div');
    d.className = 'row';
    for (var i = 0; i < btns.length; i++) d.appendChild(btns[i]);
    return d;
  }
  function empty(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }
  function mount(policy) {
    css();
    var slot = policy && document.getElementById('gcm-hs-slot');
    var root = document.getElementById('gcm-hs');
    if (!root) {
      root = document.createElement('div');
      root.id = 'gcm-hs';
      (slot || document.body || document.documentElement).appendChild(root);
    } else if (slot && root.parentNode !== slot) slot.appendChild(root);
    root.className = slot ? 'page' : 'float';
    root.hidden = false;
    return root;
  }
  function removeBox() {
    var root = document.getElementById('gcm-hs');
    if (root && root.parentNode) root.parentNode.removeChild(root);
  }
  function render() {
    if (excluded()) return;
    var policy = onPolicy();
    if (privacySignal()) {
      removeBox();
      if (!policy) return;
      var note = mount(true);
      empty(note);
      note.appendChild(para('HubSpot stays off. This browser sent a privacy signal (Global Privacy Control, Do Not Track, or a local opt-out), so the script is not loaded.'));
      return;
    }
    var c = choice();
    if (!policy && c === 'deny') { removeBox(); return; }
    var root = mount(policy);
    empty(root);
    if (c === 'allow') {
      if (!policy) root.className = 'float revoke';
      root.appendChild(para(policy
        ? 'HubSpot is allowed in this browser. Its script can set cookies, record page views, and collect form submissions while this stays on. Turn it off to stop that and clear those cookies.'
        : 'HubSpot is on.'));
      root.appendChild(row([button('Turn it off', deny)]));
    } else if (c === 'deny') {
      root.appendChild(para('HubSpot is off in this browser. Its script is not loaded.'));
      root.appendChild(row([button('Allow HubSpot', allow)]));
    } else {
      root.appendChild(para("HubSpot stays off until you allow it. Allowing loads HubSpot's script on this site. That script sets HubSpot cookies, records page views, and can send form submissions to HubSpot when form collection is on in the HubSpot account. This site cannot switch that off. The map works if you do not allow it."));
      root.appendChild(row([button('Allow HubSpot', allow), button("Don't allow", deny)]));
    }
  }
  W.GCMHubSpot = { load: load, allow: allow, deny: deny };
  function start() { load(); render(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
