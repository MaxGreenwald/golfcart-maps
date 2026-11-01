// Navigation extras (Max t446u): finish-flag pin, route line trimmed behind the rider, arrival celebration.
// Shared by the city map (app.js) and the renter page (p.js). trim() is pure for node tests.
(function (root) {
  const R = 6371000, k = Math.PI / 180;
  function hav(a, b) {
    const x = Math.sin((b[0] - a[0]) * k / 2) ** 2 + Math.cos(a[0] * k) * Math.cos(b[0] * k) * Math.sin((b[1] - a[1]) * k / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }
  // pts: [[lat,lon],...]; along: metres driven along pts. Returns the part still ahead, starting at the
  // exact point `along` metres in, so the blue line begins under the rider and nothing is drawn behind.
  function trim(pts, along) {
    if (!pts || pts.length < 2 || !(along > 0)) return pts ? pts.slice() : [];
    let d = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1], s = hav(a, b);
      if (d + s >= along) {
        const t = s > 0 ? (along - d) / s : 0;
        return [[a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]].concat(pts.slice(i + 1));
      }
      d += s;
    }
    return [pts[pts.length - 1], pts[pts.length - 1]];
  }
  function length(pts) { let d = 0; for (let i = 1; i < (pts || []).length; i++) d += hav(pts[i - 1], pts[i]); return d; }

  // Checkered finish flag on a pole, bigger than the numbered stop pins (44 px vs 30).
  const FLAG_SVG = '<svg viewBox="0 0 44 56" width="44" height="56" aria-hidden="true">' +
    '<ellipse cx="9" cy="53" rx="7" ry="2.5" fill="rgba(0,0,0,.25)"/>' +
    '<rect x="7" y="4" width="4" height="49" rx="2" fill="#2b2b2b"/>' +
    '<g transform="translate(11 5)"><rect width="30" height="22" rx="2" fill="#fff" stroke="#111" stroke-width="2"/>' +
    [0, 1, 2, 3, 4].map(c => [0, 1, 2].map(r => (c + r) % 2 ? '' : `<rect x="${c * 6}" y="${r * 7.33}" width="6" height="7.33" fill="#111"/>`).join('')).join('') +
    '</g><circle cx="9" cy="4" r="3.5" fill="#ffc400" stroke="#111" stroke-width="1.5"/></svg>';
  function flagIcon(L) {
    return L.divIcon({ className: 'gcm-flag', html: FLAG_SVG, iconSize: [44, 56], iconAnchor: [9, 53] });
  }
  function flag(L, map, ll) {
    return L.marker(ll, { icon: flagIcon(L), zIndexOffset: 1500, interactive: false, keyboard: false, title: 'Destination' }).addTo(map);
  }

  // ---- arrival celebration ----
  const TEXT = 'Have a wonderful life, you legend! 🦄';
  const listeners = [];
  function unicorn(c) {
    // Original cartoon unicorn facing right: body, legs, head, mane, horn. c = mane color.
    return '<svg viewBox="0 0 120 90" width="150" height="112" aria-hidden="true">' +
      '<g class="u-legs"><rect class="u-l1" x="32" y="52" width="9" height="28" rx="4" fill="#f4eefe"/><rect class="u-l2" x="46" y="52" width="9" height="28" rx="4" fill="#ece3fb"/>' +
      '<rect class="u-l1" x="70" y="52" width="9" height="28" rx="4" fill="#f4eefe"/><rect class="u-l2" x="82" y="52" width="9" height="28" rx="4" fill="#ece3fb"/></g>' +
      '<path d="M22 40 q-14 -6 -16 8 q8 -4 14 2" fill="' + c + '"/>' +
      '<ellipse cx="60" cy="44" rx="38" ry="18" fill="#fff" stroke="#c9b8f0" stroke-width="2"/>' +
      '<path d="M86 34 l10 -16 q4 -6 10 -4 l8 6 q3 4 -1 7 l-8 2 l-4 12 z" fill="#fff" stroke="#c9b8f0" stroke-width="2"/>' +
      '<path d="M103 15 l6 -15 l1 16 z" fill="#ffd34d" stroke="#e0a800" stroke-width="1"/>' +
      '<circle cx="105" cy="20" r="2.2" fill="#222"/><circle cx="108" cy="25" r="2" fill="#ff8fb1"/>' +
      '<path d="M90 16 q-10 2 -8 12 q-6 2 -6 10 q8 -4 10 -10 q6 -2 8 -10 z" fill="' + c + '"/>' +
      '</svg>';
  }
  function css() {
    if (document.getElementById('gcm-fx-css')) return;
    const s = document.createElement('style'); s.id = 'gcm-fx-css';
    s.textContent = `
#gcmArrive{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;overflow:hidden;
 background:radial-gradient(circle at 50% 45%,rgba(255,255,255,.88),rgba(186,160,255,.78) 60%,rgba(120,90,220,.82));cursor:pointer;animation:gcmFade .3s ease-out}
#gcmArrive .msg{position:relative;z-index:3;max-width:86vw;text-align:center;font:800 clamp(26px,7vw,46px)/1.15 system-ui,-apple-system,sans-serif;color:#4b1fa8;
 text-shadow:0 2px 0 #fff,0 0 18px #fff;animation:gcmPop .6s cubic-bezier(.2,1.6,.4,1) .2s both}
#gcmArrive .sub{display:block;margin-top:10px;font:600 15px system-ui,sans-serif;color:#5b3fb0;opacity:.85}
#gcmArrive .u{position:absolute;left:0;z-index:2;animation:gcmRun var(--d,4s) linear var(--dl,0s) var(--n,3) both}
#gcmArrive .u.rtl{animation-name:gcmRunL}
#gcmArrive .u .fl{transform:scaleX(-1)}
#gcmArrive .u .wv{animation:gcmWave var(--w,1.6s) ease-in-out infinite alternate}
#gcmArrive .cf{position:absolute;top:-20px;z-index:1;width:9px;height:14px;border-radius:2px;animation:gcmFall var(--d,5s) linear var(--dl,0s) infinite}
#gcmArrive .arc{position:absolute;left:50%;bottom:-38vmin;width:110vmin;height:110vmin;margin-left:-55vmin;border-radius:50%;z-index:0;opacity:.55;
 background:radial-gradient(circle,transparent 52%,#a06bff 52%,#a06bff 56%,#4dafff 56%,#4dafff 60%,#5ddc7a 60%,#5ddc7a 64%,#ffe14d 64%,#ffe14d 68%,#ffa64d 68%,#ffa64d 72%,#ff5d5d 72%,#ff5d5d 76%,transparent 76%);
 animation:gcmRise 1.6s cubic-bezier(.2,1.3,.4,1) .3s both}
#gcmArrive .msg{animation:gcmPop .6s cubic-bezier(.2,1.6,.4,1) .2s both,gcmPulse 1.8s ease-in-out 1s infinite}
#gcmArrive .u svg{animation:gcmBob .32s ease-in-out infinite alternate;filter:drop-shadow(0 6px 6px rgba(60,20,140,.25))}
#gcmArrive .u .u-l1{animation:gcmLeg .32s ease-in-out infinite alternate;transform-origin:top center;transform-box:fill-box}
#gcmArrive .u .u-l2{animation:gcmLeg .32s ease-in-out infinite alternate-reverse;transform-origin:top center;transform-box:fill-box}
#gcmArrive .u .rb{position:absolute;right:120px;top:44px;width:60vw;height:22px;border-radius:12px;
 background:linear-gradient(#ff5d5d,#ffa64d,#ffe14d,#5ddc7a,#4dafff,#a06bff);opacity:.85;filter:blur(.5px)}
#gcmArrive .sp{position:absolute;z-index:1;font-size:22px;animation:gcmTw 1.2s ease-in-out infinite}
@keyframes gcmRun{from{transform:translateX(-200px)}to{transform:translateX(calc(100vw + 60vw))}}
@keyframes gcmRunL{from{transform:translateX(calc(100vw + 40px))}to{transform:translateX(calc(-200px - 60vw))}}
@keyframes gcmWave{from{transform:translateY(calc(var(--a,24px) * -1))}to{transform:translateY(var(--a,24px))}}
@keyframes gcmFall{from{transform:translateY(0) rotate(0)}to{transform:translateY(110vh) rotate(720deg)}}
@keyframes gcmRise{from{transform:translateY(40vmin) scale(.6);opacity:0}to{transform:none;opacity:.55}}
@keyframes gcmPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
@keyframes gcmBob{from{transform:translateY(0) rotate(-2deg)}to{transform:translateY(-10px) rotate(2deg)}}
@keyframes gcmLeg{from{transform:rotate(-22deg)}to{transform:rotate(22deg)}}
@keyframes gcmPop{from{transform:scale(.3);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes gcmFade{from{opacity:0}to{opacity:1}}
@keyframes gcmTw{0%,100%{transform:scale(.4);opacity:.2}50%{transform:scale(1.2);opacity:1}}
#gcmArrive.calm{background:rgba(30,20,60,.45)}
#gcmArrive.calm .card{background:#fff;border-radius:18px;padding:22px 26px;text-align:center;font:700 22px/1.3 system-ui,sans-serif;color:#4b1fa8;box-shadow:0 10px 30px rgba(0,0,0,.25);max-width:84vw}`;
    document.head.appendChild(s);
  }
  function reducedMotion() {
    try { return !!(root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) { return false; }
  }
  let shown = null, timer = null;
  function dismiss() { if (timer) clearTimeout(timer); timer = null; if (shown) { shown.remove(); shown = null; } }
  // Full-screen unicorn parade, 15 s (Max t451u: 3.8 s was way too fast), tap to dismiss. Eight unicorns on
  // different lanes, speeds, directions and waves, plus confetti and a rainbow. Reduced motion: a still card, 6 s.
  const PARADE_MS = 15000, CALM_MS = 6000, UNICORNS = 8;
  function celebrate(o) {
    o = o || {};
    if (typeof document === 'undefined') return null;
    dismiss(); css();
    const el = document.createElement('div');
    el.id = 'gcmArrive'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', TEXT);
    const sub = o.place ? `<span class="sub">You made it to ${String(o.place).replace(/[<>&]/g, '')}</span>` : '';
    if (o.calm != null ? o.calm : reducedMotion()) {
      el.className = 'calm';
      el.innerHTML = `<div class="card">🦄<br>${TEXT}${sub}</div>`;
    } else {
      const cols = ['#ff7eb6', '#7ec8ff', '#b28bff', '#ffd34d', '#5ddc7a'];
      let us = '';
      for (let i = 0; i < UNICORNS; i++) {
        const d = 3.2 + (i % 3) * 0.9, dl = i * 0.8, n = Math.max(1, Math.floor((PARADE_MS / 1000 - 1 - dl) / d));
        us += `<div class="u${i % 2 ? ' rtl' : ''}" style="top:${6 + (i * 23) % 72}%;--d:${d}s;--dl:${dl}s;--n:${n};scale:${[1, .8, .65][i % 3]}">` +
          `<div class="wv" style="--a:${14 + (i % 4) * 8}px;--w:${1.2 + (i % 3) * 0.5}s"><div class="${i % 2 ? 'fl' : ''}"><div class="rb"></div>${unicorn(cols[i % cols.length])}</div></div></div>`;
      }
      let cf = '';
      const cc = ['#ff5d5d', '#ffa64d', '#ffe14d', '#5ddc7a', '#4dafff', '#a06bff', '#ff7eb6'];
      for (let i = 0; i < 40; i++) cf += `<i class="cf" style="left:${(i * 29) % 100}%;background:${cc[i % cc.length]};--d:${4 + (i % 5)}s;--dl:${(i % 10) * 0.3}s"></i>`;
      us = '<div class="arc"></div>' + cf + us;
      let sp = '';
      for (let i = 0; i < 18; i++) sp += `<span class="sp" style="left:${(i * 53) % 100}%;top:${(i * 37) % 100}%;animation-delay:${(i % 6) * 0.2}s">${i % 3 ? '✨' : '⭐'}</span>`;
      el.innerHTML = sp + us + `<div class="msg">${TEXT}${sub}</div>`;
    }
    el.addEventListener('click', dismiss);
    document.body.appendChild(el);
    shown = el;
    timer = setTimeout(dismiss, o.ms || (el.className === 'calm' ? CALM_MS : PARADE_MS));
    if (o.say) try { o.say('Have a wonderful life, you legend!'); } catch (e) {}
    return el;
  }
  // One celebration per trip: arrive(tripKey) shows it the first time for that key only.
  let lastKey = null;
  function arrive(key, o) {
    if (key != null && key === lastKey) return false;
    lastKey = key;
    root.__gcmArrivals = (root.__gcmArrivals || 0) + 1;
    celebrate(o);
    const detail = { place: o && o.place || '' };
    listeners.slice().forEach(f => { try { f(detail); } catch (e) {} });
    try { root.dispatchEvent && root.dispatchEvent(new CustomEvent('gcm:arrive', { detail })); } catch (e) {}
    return true;
  }
  function resetTrip() { lastKey = null; }
  // Bridge hook (CarPlay or others): GCM.onArrive(fn) is called with {place} on each arrival; returns an unsubscribe.
  const GCM = root.GCM = root.GCM || {};
  GCM.onArrive = function (fn) { listeners.push(fn); return () => { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); }; };
  GCM.celebrate = celebrate;

  // While navigating, the finish flag replaces the plain destination pin.
  if (typeof document !== 'undefined' && document.head) {
    const st = document.createElement('style');
    st.textContent = 'body.gcm-navigating .gcm-to-pin{display:none}.gcm-flag{background:none;border:0}.gcm-flag svg{transform:rotate(var(--gcm-mb,0deg));transform-origin:9px 53px;transition:transform .4s ease-out}';
    document.head.appendChild(st);
  }

  const api = { PARADE_MS, CALM_MS, UNICORNS, trim, length, hav, flag, flagIcon, FLAG_SVG, TEXT, celebrate, dismiss, arrive, resetTrip };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.GCMNavFx = api;
})(typeof window !== 'undefined' ? window : globalThis);
