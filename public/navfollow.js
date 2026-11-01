// Live navigation helpers shared by the city map (app.js) and renter pages (p.js):
// Start / End / Recenter, a heading arrow on the blue dot, follow mode, and off-route rerouting.
// Pure pieces (offTracker, pickHeading, compassFrom) are unit tested in tests/navfollow.test.mjs.
// Heading-up (Max t412u): while navigating with follow on, the map turns so the direction of travel points up.
// Leaflet 1.9 has no map bearing, so we rotate a wrapper div around the map pane with CSS (see rotator()).
(function (root) {
  const C = {
    OFF_ROUTE_M: 30,       // farther than this from the route counts as off route
    START_AIM_M: 400,      // still aim heading-up along the route when this close to it but off it (Max t430u)
    START_GRACE_MS: 2000,  // after Start, only a real drag or pinch pauses follow (Max t430u)
    REROUTE_MOVING_MS: 1.5, // at or above this GPS speed a reroute starts the way you are driving (Max t433u)
    OFF_ROUTE_MS: 5000,    // ...for this long before a reroute
    REROUTE_COOLDOWN_MS: 10000, // at most one reroute per this window, so it can't loop
    MIN_SPEED_MS: 0.8,     // GPS course is trusted only above ~1.8 mph
    FOLLOW_ZOOM: 17,       // driving zoom
    FOLLOW_Y: 0.68,        // the dot sits a bit below the middle of the map
    BEARING_DEADBAND: 5,   // ignore bearing changes smaller than this (degrees), so the map doesn't jitter
    BEARING_AHEAD_M: 25,   // route bearing is measured over this stretch ahead of the dot
    ROTATE_MS: 600,        // ease time for a turn
  };
  const rad = Math.PI / 180;
  function hav(a, b) {
    const dl = (b[0] - a[0]) * rad, dn = (b[1] - a[1]) * rad;
    const x = Math.sin(dl / 2) ** 2 + Math.cos(a[0] * rad) * Math.cos(b[0] * rad) * Math.sin(dn / 2) ** 2;
    return 2 * 6371000 * Math.asin(Math.sqrt(x));
  }
  function bearing(a, b) {
    const y = Math.sin((b[1] - a[1]) * rad) * Math.cos(b[0] * rad);
    const x = Math.cos(a[0] * rad) * Math.sin(b[0] * rad) - Math.sin(a[0] * rad) * Math.cos(b[0] * rad) * Math.cos((b[1] - a[1]) * rad);
    return (Math.atan2(y, x) / rad + 360) % 360;
  }
  // Off route for offMs straight (not just one noisy fix) -> true once, then a cooldown.
  function offTracker(o) {
    o = Object.assign({ offM: C.OFF_ROUTE_M, offMs: C.OFF_ROUTE_MS, cooldownMs: C.REROUTE_COOLDOWN_MS }, o || {});
    let since = null, last = -Infinity;
    return {
      update(offM, now) {
        if (!(offM > o.offM)) { since = null; return false; }
        if (since == null) since = now;
        if (now - since >= o.offMs && now - last >= o.cooldownMs) { last = now; since = null; return true; }
        return false;
      },
      offSince() { return since; },
      reset() { since = null; },
      opts: o,
    };
  }
  // Compass degrees from a DeviceOrientation event (iOS webkitCompassHeading, else absolute alpha).
  function compassFrom(e) {
    if (!e) return null;
    if (Number.isFinite(e.webkitCompassHeading)) return (e.webkitCompassHeading + 360) % 360;
    if (e.absolute && Number.isFinite(e.alpha)) return (360 - e.alpha) % 360;
    return null;
  }
  // GPS course while moving; else the bearing between fixes when we moved; else the compass; else null.
  function pickHeading(coords, compass, prevLL) {
    const sp = coords && coords.speed, hd = coords && coords.heading;
    const stopped = Number.isFinite(sp) && sp < C.MIN_SPEED_MS;
    if (Number.isFinite(hd) && !stopped) return (hd + 360) % 360;
    if (!stopped && prevLL && coords && hav(prevLL, [coords.latitude, coords.longitude]) >= 8) return bearing(prevLL, [coords.latitude, coords.longitude]);
    return Number.isFinite(compass) ? compass : null;
  }

  // Point at distance d (m) along a route {pts, cum}.
  function pointAt(route, d) {
    const { pts, cum } = route;
    if (d <= 0) return pts[0];
    for (let i = 1; i < pts.length; i++) {
      if (cum[i] >= d) {
        const t = cum[i] > cum[i - 1] ? (d - cum[i - 1]) / (cum[i] - cum[i - 1]) : 0;
        return [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])];
      }
    }
    return pts[pts.length - 1];
  }
  function withCum(route) {
    if (route.cum && route.cum.length === route.pts.length) return route;
    const cum = [0];
    for (let i = 1; i < route.pts.length; i++) cum.push(cum[i - 1] + hav(route.pts[i - 1], route.pts[i]));
    return { pts: route.pts, cum };
  }
  // Direction of the road ahead: bearing from where we are on the route to a point aheadM further on.
  // Null when off the route (caller falls back to GPS course) or at the very end.
  // maxOff: how far from the route the position may be (default OFF_ROUTE_M).
  function routeBearing(route, ll, aheadM, proj, maxOff) {
    if (!route || !route.pts || route.pts.length < 2 || !ll) return null;
    const r = withCum(route);
    const p = (proj || (root.GCMNav && root.GCMNav.project))(r, ll);
    if (!p || !(p.off <= (maxOff == null ? C.OFF_ROUTE_M : maxOff))) return null;
    const total = r.cum[r.cum.length - 1];
    let a = Math.min(p.along, total), b = Math.min(a + (aheadM || C.BEARING_AHEAD_M), total);
    if (b - a < 3) a = Math.max(0, b - (aheadM || C.BEARING_AHEAD_M));
    if (b - a < 1) return null;
    return bearing(pointAt(r, a), pointAt(r, b));
  }
  // GPS course only (never the compass): stable while driving.
  function courseHeading(coords, prevLL) {
    return pickHeading(coords, null, prevLL);
  }
  // Next map bearing. prev is unwrapped (may be > 360) so CSS eases the short way round.
  // Changes under deadband degrees are ignored.
  function nextBearing(prev, target, deadband) {
    if (!Number.isFinite(target)) return prev;
    if (!Number.isFinite(prev)) return (target + 360) % 360;
    const d = ((target - prev) % 360 + 540) % 360 - 180;
    if (Math.abs(d) < (deadband == null ? C.BEARING_DEADBAND : deadband)) return prev;
    return prev + d;
  }

  // ---- Spoken guidance (Max t419u): one sentence at a time, never cut off, one prompt per turn.
  // engine: { speak(text, done), cancel() }. A sentence always finishes; a newer prompt replaces an older
  // one still waiting (e.g. a reroute), but only between sentences. stop() is for End and mute.
  function voice(engine) {
    let current = null, pending = null;
    function play(t) {
      current = t;
      root.__navSaid = (root.__navSaid || []).concat(t);
      let fin = false;
      const done = () => { if (fin) return; fin = true; current = null; if (pending != null) { const n = pending; pending = null; play(n); } };
      try { engine.speak(t, done); } catch (_) { done(); }
    }
    return {
      say(t) {
        if (!t || t === current || t === pending) return;
        if (current == null) play(t); else pending = t;
      },
      stop() { pending = null; current = null; try { engine.cancel(); } catch (_) {} },
      speaking: () => current != null,
      pending: () => pending,
    };
  }
  // Browser / WKWebView speech. If onend never fires (an iOS quirk), a length-based timer frees the queue.
  function webEngine() {
    let gen = 0;
    return {
      speak(t, done) {
        const S = root.speechSynthesis, U = root.SpeechSynthesisUtterance;
        if (!S || !U) { setTimeout(done, 0); return; }
        const my = ++gen, u = new U(t), fin = () => { if (my === gen) done(); };
        u.onend = fin; u.onerror = fin;
        setTimeout(fin, 1500 + t.length * 90);
        S.speak(u);
      },
      cancel() { gen++; if (root.speechSynthesis) root.speechSynthesis.cancel(); },
    };
  }
  // When to speak a maneuver: once, about LEAD_S seconds before it at the current speed (golf carts
  // 15-25 mph), so the sentence ends before the turn. If that moment was missed (late fix, short leg),
  // a short "Turn left onto X" at the turn instead. Never the same maneuver twice.
  const P = { LEAD_S: 12, MIN_LEAD_M: 35, MAX_LEAD_M: 180, NOW_M: 20, DEFAULT_MS: 8 };
  function promptPlan(o) {
    o = Object.assign({}, P, o || {});
    let said = new Set();
    return {
      // st: GCMNav.status(...); speed m/s (may be null). Returns the sentence to say now, or null.
      update(st, speed) {
        if (!st || st.arrived || !st.next) return null;
        const key = st.idx + ':' + Math.round(st.next.at);
        if (said.has(key)) return null;
        const v = Number.isFinite(speed) && speed > C.MIN_SPEED_MS ? speed : o.DEFAULT_MS;
        const lead = Math.min(o.MAX_LEAD_M, Math.max(o.MIN_LEAD_M, v * o.LEAD_S));
        if (st.toNext <= o.NOW_M) { said.add(key); return st.next.text; }
        if (st.toNext <= lead) { said.add(key); return st.text; }
        return null;
      },
      reset() { said = new Set(); },
      opts: o,
    };
  }

  const CSS = `.me-wrap{position:relative;width:22px;height:22px}.me-wrap .me-dot{position:absolute;inset:0;margin:auto}
.me-cone{display:none;position:absolute;left:50%;top:50%;width:0;height:0;margin-left:-11px;margin-top:-30px;border-left:11px solid transparent;border-right:11px solid transparent;border-bottom:22px solid rgba(29,111,224,.85);transform-origin:11px 30px;transform:rotate(var(--hd,0deg));filter:drop-shadow(0 0 1px #fff)}
.me-wrap.has-hd .me-cone{display:block}
.me-cart{display:none;position:absolute;left:50%;top:50%;width:48px;height:48px;margin:-24px 0 0 -24px;transform:rotate(var(--mb,0deg));transform-origin:50% 50%;will-change:transform;pointer-events:none}
.me-ico{width:100%;height:100%;filter:drop-shadow(0 2px 3px rgba(0,0,0,.3))}
.me-ico svg,.me-ico img{display:block;width:100%;height:100%}
.me-ico svg{transform:scaleX(var(--flip,1));will-change:transform}
.me-chev{display:none;position:absolute;left:50%;top:50%;width:78px;height:78px;margin:-39px 0 0 -39px;transform:rotate(var(--hd,0deg));will-change:transform;pointer-events:none}
.me-chev:before{content:'';position:absolute;left:50%;top:0;width:16px;height:10px;margin-left:-8px;background:#0b9fb3;clip-path:polygon(50% 0,100% 100%,50% 70%,0 100%);filter:drop-shadow(0 0 1px #fff)}
body.gcm-navigating .me-cart,body.gcm-navigating .me-wrap.has-hd .me-chev{display:block}
body.gcm-navigating .me-wrap .me-dot,body.gcm-navigating .me-wrap .me-cone{display:none}
#navCtl{position:fixed;z-index:1200;left:0;right:0;bottom:calc(16px + env(safe-area-inset-bottom,0px));display:flex;justify-content:center;gap:10px;pointer-events:none}
#navCtl button{pointer-events:auto;border:0;border-radius:999px;font:900 17px Nunito,system-ui,sans-serif;padding:14px 26px;box-shadow:0 6px 18px rgba(0,0,0,.28);cursor:pointer}
#navCtl #navStart{background:#12a150;color:#fff}#navCtl #navEnd{background:#e5484d;color:#fff}#navCtl #navRecenter{background:#fff;color:#0b3a78}
#navCtl [hidden]{display:none}
#navEta{display:none}
body.gcm-navigating #navCtl{left:0;right:0;bottom:0;padding:10px 12px calc(10px + env(safe-area-inset-bottom,0px));background:#fff;box-shadow:0 -6px 20px rgba(0,0,0,.18);border-radius:18px 18px 0 0;justify-content:flex-end;align-items:center;pointer-events:auto}
body.gcm-navigating #navEta{display:block;flex:1;font:900 18px Nunito,system-ui,sans-serif;color:#0b3a78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
body.gcm-navigating #navEta small{display:block;font:700 13px Nunito,system-ui,sans-serif;color:#5b6b7a}
body.gcm-navigating #navCtl button{padding:12px 20px;box-shadow:none}
body.gcm-navigating #navCtl #navRecenter{border:2px solid #d6e2ee}
.gcm-rot{position:absolute;left:0;top:0;width:100%;height:100%;transition:transform ${C.ROTATE_MS}ms ease-out;will-change:transform}
#navNorth{position:fixed;z-index:1200;right:12px;bottom:calc(150px + env(safe-area-inset-bottom,0px));width:40px;height:40px;border-radius:50%;border:0;background:#fff;box-shadow:0 3px 10px rgba(0,0,0,.28);padding:0;cursor:pointer}
#navNorth[hidden]{display:none}#navNorth i{display:block;width:100%;height:100%;transition:transform ${C.ROTATE_MS}ms ease-out;font:900 11px Nunito,system-ui,sans-serif;color:#e5484d;position:relative}
#navNorth i:before{content:'';position:absolute;left:50%;top:7px;margin-left:-5px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:12px solid #e5484d}
#navNorth i:after{content:'N';position:absolute;left:0;right:0;bottom:6px;text-align:center;color:#0b3a78}`;
  function injectCss() {
    if (typeof document === 'undefined' || document.getElementById('navFollowCss')) return;
    const s = document.createElement('style'); s.id = 'navFollowCss'; s.textContent = CSS; document.head.appendChild(s);
  }
  // Max t426u/t427u: while navigating the dot becomes the 48 px playful cart (design E), or the user's own
  // photo icon (Settings > Your map icon). E is a side view, so it stays upright (counter-turned by --mb, the
  // map bearing) and flips with --flip to face the way it moves on screen; a small teal chevron turned by --hd
  // shows the heading. All three are CSS variables set in the same once-per-frame paint, so no extra work.
  // The art faces left by default (golf bag at the back, on the right).
  const CART = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><ellipse cx="32" cy="56" rx="22" ry="4" fill="rgba(0,0,0,.22)"/><path d="M10 14q22-8 44 0" fill="#fff" stroke="#0b6e86" stroke-width="2" stroke-linecap="round"/><path d="M10 14q22-4 44 0" fill="none" stroke="#ffd23f" stroke-width="2.4"/><path d="M15 16v18M49 16v18" stroke="#0b6e86" stroke-width="3.2" stroke-linecap="round"/><path d="M8 36q0-6 8-6h32q8 0 8 6v6q0 6-8 6H16q-8 0-8-6z" fill="#2fc6d1" stroke="#fff" stroke-width="2"/><path d="M14 36h36" stroke="#e9fbfc" stroke-width="3" stroke-linecap="round"/><rect x="44" y="20" width="10" height="18" rx="5" fill="#ff8a3d" stroke="#fff" stroke-width="1.6"/><path d="M47 20V6" stroke="#fff" stroke-width="1.6"/><path d="M47 6l8 3-8 3z" fill="#e5484d"/><circle cx="24" cy="38" r="2" fill="#123b4a"/><circle cx="36" cy="38" r="2" fill="#123b4a"/><path d="M27 42q3 2 6 0" stroke="#123b4a" stroke-width="1.6" fill="none" stroke-linecap="round"/><g fill="#1d2a33" stroke="#fff" stroke-width="2.6"><circle cx="18" cy="49" r="6.5"/><circle cx="46" cy="49" r="6.5"/></g><circle cx="18" cy="49" r="2.2" fill="#ffd23f"/><circle cx="46" cy="49" r="2.2" fill="#ffd23f"/></svg>';
  // scaleX for the left-facing cart: -1 (face right) when the screen direction (heading minus map bearing)
  // points right, 1 when it points left, and the previous side inside a 10 degree band around up/down.
  function faceSide(heading, mapBearing, prev) {
    const sx = Math.sin((heading - (mapBearing || 0)) * Math.PI / 180);
    return sx > 0.17 ? -1 : sx < -0.17 ? 1 : (prev || 1);
  }
  const ICON_KEY = 'gcm_map_icon';
  function iconHtml() {
    let u = null; try { u = root.localStorage && localStorage.getItem(ICON_KEY); } catch (_) {}
    return u && /^data:image\/(png|jpeg|webp);base64,/.test(u) ? '<img alt="" src="' + u + '">' : CART;
  }
  function refreshIcon() {
    if (typeof document === 'undefined') return;
    const h = iconHtml(); document.querySelectorAll('.me-ico').forEach(el => { el.innerHTML = h; });
  }
  const dotHtml = () => '<div class="me-wrap"><div class="me-cone"></div><div class="me-dot"></div><div class="me-chev" aria-hidden="true"></div><div class="me-cart" aria-hidden="true"><div class="me-ico">' + iconHtml() + '</div></div></div>';

  // Max t427u/t428u: Settings > Your map icon. A photo is processed on this device only (never uploaded):
  // center square crop, 128 px, round with a white ring, saved as a small PNG data URL in localStorage.
  const ICON_PX = 128, ICON_MAX_BYTES = 50000, FILE_MAX_BYTES = 30 * 1024 * 1024;
  function loadImage(file) {
    return new Promise((ok, bad) => {
      const url = URL.createObjectURL(file), im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); ok(im); };
      im.onerror = () => { URL.revokeObjectURL(url); bad(new Error('decode')); };
      im.src = url;
    });
  }
  function roundIcon(im, px) {
    const c = document.createElement('canvas'); c.width = c.height = px;
    const g = c.getContext('2d'), w = im.naturalWidth || im.width, h = im.naturalHeight || im.height, side = Math.min(w, h);
    const ring = Math.max(3, Math.round(px * 0.06)), r = px / 2;
    g.save(); g.beginPath(); g.arc(r, r, r - ring, 0, Math.PI * 2); g.clip();
    g.imageSmoothingQuality = 'high';
    g.drawImage(im, (w - side) / 2, (h - side) / 2, side, side, ring, ring, px - 2 * ring, px - 2 * ring);
    g.restore();
    g.beginPath(); g.arc(r, r, r - ring / 2, 0, Math.PI * 2); g.lineWidth = ring; g.strokeStyle = '#fff'; g.stroke();
    return c.toDataURL('image/png');
  }
  // Resolves to the saved data URL, or rejects with a message for the user.
  async function setIconFromFile(file) {
    if (!file) throw new Error('No photo picked.');
    if (file.size > FILE_MAX_BYTES) throw new Error('That photo is too big (over 30 MB). Try a smaller one.');
    let im;
    try { im = await loadImage(file); } catch (_) {
      const heic = /hei[cf]/i.test(file.type || '') || /\.hei[cf]$/i.test(file.name || '');
      throw new Error(heic ? 'This browser cannot read HEIC photos. Pick a JPEG or PNG, or take a screenshot of the photo and use that.' : 'Could not read that file as a picture. Try a JPEG or PNG.');
    }
    if (!(im.naturalWidth > 0)) throw new Error('Could not read that file as a picture. Try a JPEG or PNG.');
    let px = ICON_PX, url = roundIcon(im, px);
    while (url.length > ICON_MAX_BYTES && px > 48) { px -= 16; url = roundIcon(im, px); }
    if (url.length > ICON_MAX_BYTES) throw new Error('Could not make that photo small enough. Try another one.');
    try { localStorage.setItem(ICON_KEY, url); } catch (_) { throw new Error('Could not save the icon on this device.'); }
    refreshIcon();
    return url;
  }
  function resetIcon() { try { localStorage.removeItem(ICON_KEY); } catch (_) {} refreshIcon(); }
  function hasCustomIcon() { try { return !!localStorage.getItem(ICON_KEY); } catch (_) { return false; } }
  function wireIconSetting() {
    if (typeof document === 'undefined') return;
    const file = document.getElementById('iconFile'), reset = document.getElementById('iconReset'), sub = document.getElementById('iconSub'), prev = document.getElementById('iconPrev');
    if (!file || file.dataset.wired) return; file.dataset.wired = '1';
    const show = (msg, err) => {
      prev.innerHTML = iconHtml(); reset.hidden = !hasCustomIcon();
      sub.textContent = msg || (hasCustomIcon() ? 'Your photo. Shows while you navigate.' : 'Default cart. Shows while you navigate.');
      sub.classList.toggle('err', !!err);
    };
    file.addEventListener('change', async () => {
      const f = file.files && file.files[0]; file.value = '';
      if (!f) return;
      sub.textContent = 'Making your icon...'; sub.classList.remove('err');
      try { await setIconFromFile(f); show(); } catch (e) { show(e.message, true); }
    });
    reset.addEventListener('click', () => { resetIcon(); show(); });
    show();
  }
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wireIconSetting); else wireIconSetting();
  }

  // Rotate a Leaflet map with CSS. The map pane goes inside a wrapper div that turns around the dot's
  // screen spot, so panning (which Leaflet does on the pane) and rotation never fight. While turned, tiles
  // and vector renderers load a margin big enough to fill the corners, and taps are un-rotated so a tap
  // still lands on the right latlng.
  function rotator(map) {
    if (!map || !map.getPane || typeof document === 'undefined') return null;
    const pane = map.getPane('mapPane'), box = map.getContainer();
    const wrap = document.createElement('div'); wrap.className = 'gcm-rot';
    box.insertBefore(wrap, pane); wrap.appendChild(pane);
    let deg = 0, on = false, origin = [0, 0];
    const GL = root.L && root.L.GridLayer && root.L.GridLayer.prototype;
    if (GL && !GL.__gcmRot) {
      GL.__gcmRot = 1;
      const orig = GL._getTiledPixelBounds;
      GL._getTiledPixelBounds = function (center) {
        const b = orig.call(this, center), pad = this._map && this._map.__gcmPad;
        if (!pad) return b;
        return root.L.bounds(b.min.subtract(pad), b.max.add(pad));
      };
    }
    const toCP = map.mouseEventToContainerPoint.bind(map);
    map.mouseEventToContainerPoint = function (e) {
      const p = toCP(e);
      if (!deg) return p;
      const a = deg * rad, x = p.x - origin[0], y = p.y - origin[1];
      // undo rotate(-deg): rotate the screen point by +deg around the origin
      return root.L.point(origin[0] + x * Math.cos(a) - y * Math.sin(a), origin[1] + x * Math.sin(a) + y * Math.cos(a));
    };
    function pads(turnOn) {
      const sz = map.getSize();
      if (turnOn) {
        const r = Math.hypot(Math.max(origin[0], sz.x - origin[0]), Math.max(origin[1], sz.y - origin[1]));
        const px = Math.max(0, r - sz.x / 2), py = Math.max(0, r - Math.min(origin[1], sz.y - origin[1]));
        map.__gcmPad = root.L.point(Math.ceil(px), Math.ceil(py));
      } else map.__gcmPad = null;
      Object.values(map._layers || {}).forEach(l => {
        if (root.L.Renderer && l instanceof root.L.Renderer) {
          if (l.__gcmPad0 == null) l.__gcmPad0 = l.options.padding;
          l.options.padding = turnOn ? Math.max(l.__gcmPad0, map.__gcmPad.x / sz.x, map.__gcmPad.y / sz.y) : l.__gcmPad0;
        }
      });
      map.fire('moveend'); // one refresh so the bigger (or normal) area draws
    }
    return {
      // bearing: map degrees clockwise from north that should point up; null = north-up
      set(bearingDeg, oy) {
        const want = bearingDeg != null;
        const sz = map.getSize();
        origin = [sz.x / 2, sz.y * oy];
        if (want !== on) { on = want; pads(on); }
        deg = want ? bearingDeg : 0;
        wrap.style.transformOrigin = origin[0] + 'px ' + origin[1] + 'px';
        wrap.style.transform = deg ? 'rotate(' + (-deg) + 'deg)' : '';
        root.__navMapBearing = deg;
      },
      get: () => deg,
      el: wrap,
    };
  }

  // opts: map, getRoute() -> {pts} | null, reroute(ll) -> Promise, say(text), onStart(), onEnd(), canStart()
  function controller(opts) {
    injectCss();
    const map = opts.map;
    const track = offTracker(opts.offRoute);
    let navigating = false, following = false, heading = null, compass = null, last = null, prevLL = null, course = null, courseAt = 0;
    let timer = 0, rerouting = false, moving = 0, previewing = false;
    let mapBearing = null; // unwrapped; null = north-up
    const rot = rotator(map);
    const ctl = document.createElement('div');
    ctl.id = 'navCtl';
    ctl.innerHTML = '<div id="navEta" aria-live="off"></div><button type="button" id="navStart" hidden>▶ Start</button><button type="button" id="navRecenter" hidden>◎ Recenter</button><button type="button" id="navEnd" hidden>■ End</button>';
    document.body.appendChild(ctl);
    const north = document.createElement('button');
    north.type = 'button'; north.id = 'navNorth'; north.hidden = true; north.title = 'North up';
    north.setAttribute('aria-label', 'Compass. Tap for north up'); north.innerHTML = '<i></i>';
    document.body.appendChild(north);
    const $b = id => ctl.querySelector('#' + id);
    function paintBtns() {
      $b('navStart').hidden = navigating || !previewing;
      $b('navEnd').hidden = !navigating;
      $b('navRecenter').hidden = !navigating || following;
      north.hidden = !navigating;
      // Max t417u: while driving, pages hide search, town picker, chips and other clutter via this class.
      if (document.body.classList.contains('gcm-navigating') !== navigating) {
        document.body.classList.toggle('gcm-navigating', navigating);
        fyAt = 0;
        if (map && map.invalidateSize) map.invalidateSize({ pan: false });
      }
      if (!(navigating && following) && mapBearing != null) { mapBearing = null; paintHeading(true); }
    }
    const headingUp = () => navigating && following && !!rot;
    // Target bearing from the road ahead, else GPS course when moving; keep the last one otherwise.
    function aimBearing() {
      if (!headingUp() || !last) return;
      const ll = [last.latitude, last.longitude];
      const r = opts.getRoute && opts.getRoute();
      let t = null;
      try { t = routeBearing(r, ll); } catch (_) { t = null; }
      if (t == null) t = courseHeading(last, prevLL);
      // Max t430u: standing still a bit off the line (driveway, parking lot, GPS drift at Start) gave no
      // bearing at all, so the map stayed north-up. Use the road ahead from the nearest route point.
      if (t == null) { try { t = routeBearing(r, ll, null, null, C.START_AIM_M); } catch (_) { t = null; } }
      if (t == null) return;
      const nb = nextBearing(mapBearing, t);
      if (nb !== mapBearing) { mapBearing = nb; paintHeading(true); }
    }
    // Paint the heading at most once per frame, only when it moved >= 3 deg or toggled on/off.
    // deviceorientation fires ~60/s on iPhone; painting every event (querySelectorAll + style write)
    // kept the main thread busy and made typing lag (Oct 31 2026).
    let painted, paintQueued = 0, flip = 1;
    function paintHeading(force) {
      if (force === true) painted = undefined;
      if (paintQueued) return;
      const raf = root.requestAnimationFrame || (f => setTimeout(f, 16));
      paintQueued = raf(() => {
        paintQueued = 0;
        const mb = headingUp() && mapBearing != null ? mapBearing : null;
        if (rot && (rot.get() || 0) !== (mb || 0)) rot.set(mb, followY());
        north.firstChild.style.transform = mb ? 'rotate(' + (-mb) + 'deg)' : '';
        // Heading-up: the dot lives inside the turned map, so giving the arrow the map bearing points it straight up on screen.
        const h = heading == null && mb == null ? null : (mb != null ? Math.round(((mb % 360) + 360) % 360) : Math.round(heading));
        if (painted !== undefined && (h == null) === (painted == null) && (h == null || Math.abs(((h - painted + 540) % 360) - 180) < 3)) return;
        painted = h;
        root.__navHeadingPaints = (root.__navHeadingPaints || 0) + 1;
        // Screen direction = heading minus map bearing. Face right when it points right (with a 10 degree
        // dead zone near straight up/down so the cart does not flicker), else keep the last side.
        const mbv = mb != null ? Math.round(((mb % 360) + 360) % 360) : 0;
        if (h != null) flip = faceSide(h, mbv, flip);
        document.documentElement.style.setProperty('--gcm-mb', mbv + 'deg'); // keeps the finish flag upright (navfx.js)
        document.querySelectorAll('.me-wrap').forEach(el => {
          el.classList.toggle('has-hd', h != null);
          if (h != null) el.style.setProperty('--hd', h + 'deg');
          el.style.setProperty('--mb', mbv + 'deg');
          el.style.setProperty('--flip', String(flip));
        });
      });
    }
    // Where the dot sits: lower-middle of the map area NOT covered by the turn card (top) or the
    // nav bar (bottom), as a fraction of the map height (Max t421u: the sheet hid the dot).
    let fyAt = 0, fy = C.FOLLOW_Y;
    function followY() {
      if (!map || typeof document === 'undefined') return C.FOLLOW_Y;
      const now = Date.now();
      if (now - fyAt < 1000) return fy;
      fyAt = now;
      const mb = map.getContainer().getBoundingClientRect(), h = mb.height || 1;
      let top = mb.top, bot = mb.bottom;
      (opts.topEls || ['#mapNav', '#navBanner']).forEach(sel => {
        const el = document.querySelector(sel);
        if (el && el.offsetParent !== null) { const r = el.getBoundingClientRect(); if (r.height && r.top < mb.top + h / 2) top = Math.max(top, r.bottom); }
      });
      if (navigating) { const r = ctl.getBoundingClientRect(); if (r.height && r.top > mb.top + h / 2) bot = Math.min(bot, r.top); }
      if (bot - top < h * 0.3) { fy = C.FOLLOW_Y; return fy; }
      fy = (top - mb.top + (bot - top) * 0.7) / h;
      return fy;
    }
    // Keep the dot a bit below center. Cheap: skip when it is already within a few px of the target.
    function center(ll) {
      if (!map || !ll) return;
      const z = Math.max(map.getZoom(), C.FOLLOW_ZOOM), sz = map.getSize();
      const off = L.point(0, sz.y * (followY() - 0.5));
      const c = map.unproject(map.project(L.latLng(ll[0], ll[1]), z).subtract(off), z);
      root.__navCenters = (root.__navCenters || 0) + 1;
      if (z !== map.getZoom()) { map.setView(c, z, { animate: false }); return; }
      const d = map.project(c, z).subtract(map.project(map.getCenter(), z));
      if (Math.abs(d.x) < 2 && Math.abs(d.y) < 2) return;
      // Big jumps (first fix, GPS catch-up) snap; small steps glide.
      if (Math.abs(d.x) > sz.x / 4 || Math.abs(d.y) > sz.y / 4) { map.setView(c, z, { animate: false }); return; }
      map.panTo(c, { animate: true, duration: 0.25, easeLinearity: 1, noMoveStart: true });
    }
    // Only a real finger/mouse drag or pinch on the map pauses follow. Leaflet move/zoom events also
    // fire for our own and the app's programmatic moves (fitBounds before Start, reroute framing,
    // animated zoom), which paused follow right after Start in the field (Max t409u).
    let touching = false;
    // Max t430u: follow was found paused right after Start (Recenter showing, north-up). A finger still
    // flagged as down from tapping the map to pick the destination, plus Start's own moves (sheet
    // collapse, invalidateSize, recenter), counted as the user panning. For a short time after Start only
    // a real drag or pinch counts.
    let startedAt = 0, fingers = 0;
    function userMoved(e) {
      if (!touching || !navigating || !following) return;
      if (Date.now() - startedAt < C.START_GRACE_MS && !(e && (e.type === 'dragstart' || (e.type === 'zoomstart' && fingers > 1)))) return;
      following = false; paintBtns();
    }
    if (map) {
      const el = map.getContainer();
      const down = e => { touching = true; if (e && e.touches) fingers = e.touches.length; }, up = () => { setTimeout(() => { touching = false; fingers = 0; }, 0); };
      ['pointerdown', 'touchstart', 'mousedown'].forEach(t => el.addEventListener(t, down, { passive: true }));
      ['pointerup', 'pointercancel', 'touchend', 'touchcancel', 'mouseup'].forEach(t => root.addEventListener(t, up, { passive: true }));
      el.addEventListener('wheel', () => { touching = true; userMoved(); touching = false; }, { passive: true });
      map.on('dragstart', userMoved); map.on('zoomstart', userMoved); map.on('movestart', userMoved);
    }
    function onOrient(e) { const c = compassFrom(e); if (c != null) { compass = c; if (!last || !Number.isFinite(last.heading) || !last.speed) { heading = c; paintHeading(); } } }
    // Compass only while navigating: listeners come off at End (they used to stay on forever).
    let compassOn = false;
    function listenCompass() {
      const D = root.DeviceOrientationEvent;
      if (!D || compassOn) return;
      const on = () => { if (!navigating || compassOn) return; compassOn = true; root.__navCompassOn = true; root.addEventListener('deviceorientationabsolute', onOrient); root.addEventListener('deviceorientation', onOrient); };
      if (typeof D.requestPermission === 'function') D.requestPermission().then(r => { if (r === 'granted') on(); }).catch(() => {});
      else on();
    }
    function stopCompass() {
      if (!compassOn) return;
      compassOn = false; root.__navCompassOn = false; compass = null;
      root.removeEventListener('deviceorientationabsolute', onOrient); root.removeEventListener('deviceorientation', onOrient);
    }
    function check(now) {
      const r = opts.getRoute && opts.getRoute();
      if (!navigating || rerouting || !last || !r || !r.pts || r.pts.length < 2) return;
      const off = root.GCMNav.project(r, [last.latitude, last.longitude]).off;
      if (track.update(off, now)) {
        rerouting = true;
        opts.say && opts.say('Rerouting');
        root.__navReroutes = (root.__navReroutes || 0) + 1;
        Promise.resolve(opts.reroute([last.latitude, last.longitude], api.travelCourse())).catch(() => {}).finally(() => { rerouting = false; track.reset(); });
      }
      clearTimeout(timer);
      const s = track.offSince();
      if (s != null) timer = setTimeout(() => check(Date.now()), Math.max(50, track.opts.offMs - (now - s) + 20));
    }
    const api = {
      // coords: a GeolocationCoordinates-like {latitude, longitude, heading, speed}
      fix(coords) {
        if (!coords || !Number.isFinite(coords.latitude)) return;
        const h = pickHeading(coords, compass, prevLL);
        const cr = courseHeading(coords, prevLL); if (cr != null) { course = cr; courseAt = Date.now(); }
        if (h != null) heading = h; else if (!Number.isFinite(compass)) heading = null;
        if (!prevLL || hav(prevLL, [coords.latitude, coords.longitude]) >= 8) prevLL = [coords.latitude, coords.longitude];
        last = coords;
        aimBearing();
        paintHeading();
        if (navigating && following) center([coords.latitude, coords.longitude]);
        check(Date.now());
      },
      // GPS course while clearly driving (speed >= REROUTE_MOVING_MS, or unknown speed but a fresh course
      // from movement), else null so a reroute may start in any direction.
      travelCourse() { return last ? travelCourseOf(course, Date.now() - courseAt, last.speed) : null; },
      preview(on) { previewing = !!on; if (!on && navigating) api.end(); paintBtns(); },
      start() {
        if (navigating) return;
        if (opts.canStart && !opts.canStart()) return;
        navigating = true; following = true; track.reset(); startedAt = Date.now(); touching = false;
        listenCompass();
        paintBtns();
        if (opts.onStart) opts.onStart();
        if (map && map.stop) map.stop();
        if (last) center([last.latitude, last.longitude]);
        aimBearing();
        check(Date.now());
      },
      end() {
        if (!navigating) return;
        navigating = false; following = false; clearTimeout(timer); track.reset(); stopCompass();
        paintBtns();
        if (opts.onEnd) opts.onEnd();
      },
      recenter() { following = true; paintBtns(); if (last) center([last.latitude, last.longitude]); aimBearing(); },
      pause() { if (navigating && following) { following = false; paintBtns(); } },
      paintHeading: () => paintHeading(true),
      // Bottom nav bar line: time and distance left (remaining metres; speed m/s, cart default ~18 mph).
      eta(remainingM, speed) {
        const el = $b('navEta');
        if (!el || !Number.isFinite(remainingM)) return;
        const v = Number.isFinite(speed) && speed > 2 ? speed : 8;
        const min = Math.max(1, Math.round(remainingM / v / 60)), mi = remainingM / 1609.34;
        const t = new Date(Date.now() + remainingM / v * 1000);
        const html = min + ' min<small>' + (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + ' mi · arrive ' + t.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) + '</small>';
        if (el.innerHTML !== html) el.innerHTML = html;
      },
      state: () => ({ navigating, following, previewing, heading, rerouting, compassOn, mapBearing: rot ? rot.get() : 0, headingUp: headingUp() && mapBearing != null }),
    };
    root.gcmFollowState = api.state; root.gcmFollowRoute = () => opts.getRoute && opts.getRoute(); // test hooks (read-only)
    $b('navStart').onclick = () => api.start();
    $b('navEnd').onclick = () => api.end();
    $b('navRecenter').onclick = () => api.recenter();
    north.onclick = () => api.pause();
    paintBtns();
    return api;
  }
  // Course a reroute should honor: a fresh (<10 s) course, unless GPS says we are slower than
  // REROUTE_MOVING_MS. Unknown speed with a fresh course from movement counts as moving.
  function travelCourseOf(course, ageMs, speed) {
    if (course == null || !(ageMs <= 10000)) return null;
    if (Number.isFinite(speed) && speed < C.REROUTE_MOVING_MS) return null;
    return course;
  }

  const api = { C, P, travelCourseOf, voice, webEngine, promptPlan, offTracker, compassFrom, pickHeading, routeBearing, nextBearing, courseHeading, pointAt, controller, faceSide, get DOT() { return dotHtml(); }, CART, ICON_KEY, refreshIcon, setIconFromFile, resetIcon };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMFollow = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
