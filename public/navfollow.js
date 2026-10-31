// Live navigation helpers shared by the city map (app.js) and renter pages (p.js):
// Start / End / Recenter, a heading arrow on the blue dot, follow mode, and off-route rerouting.
// Pure pieces (offTracker, pickHeading, compassFrom) are unit tested in tests/navfollow.test.mjs.
// Heading-up (Max t412u): while navigating with follow on, the map turns so the direction of travel points up.
// Leaflet 1.9 has no map bearing, so we rotate a wrapper div around the map pane with CSS (see rotator()).
(function (root) {
  const C = {
    OFF_ROUTE_M: 30,       // farther than this from the route counts as off route
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
  function routeBearing(route, ll, aheadM, proj) {
    if (!route || !route.pts || route.pts.length < 2 || !ll) return null;
    const r = withCum(route);
    const p = (proj || (root.GCMNav && root.GCMNav.project))(r, ll);
    if (!p || !(p.off <= C.OFF_ROUTE_M)) return null;
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

  const CSS = `.me-wrap{position:relative;width:22px;height:22px}.me-wrap .me-dot{position:absolute;inset:0;margin:auto}
.me-cone{display:none;position:absolute;left:50%;top:50%;width:0;height:0;margin-left:-11px;margin-top:-30px;border-left:11px solid transparent;border-right:11px solid transparent;border-bottom:22px solid rgba(29,111,224,.85);transform-origin:11px 30px;transform:rotate(var(--hd,0deg));filter:drop-shadow(0 0 1px #fff)}
.me-wrap.has-hd .me-cone{display:block}
#navCtl{position:fixed;z-index:1200;left:0;right:0;bottom:calc(16px + env(safe-area-inset-bottom,0px));display:flex;justify-content:center;gap:10px;pointer-events:none}
#navCtl button{pointer-events:auto;border:0;border-radius:999px;font:900 17px Nunito,system-ui,sans-serif;padding:14px 26px;box-shadow:0 6px 18px rgba(0,0,0,.28);cursor:pointer}
#navCtl #navStart{background:#12a150;color:#fff}#navCtl #navEnd{background:#e5484d;color:#fff}#navCtl #navRecenter{background:#fff;color:#0b3a78}
#navCtl [hidden]{display:none}
.gcm-rot{position:absolute;left:0;top:0;width:100%;height:100%;transition:transform ${C.ROTATE_MS}ms ease-out;will-change:transform}
#navNorth{position:fixed;z-index:1200;right:12px;top:calc(96px + env(safe-area-inset-top,0px));width:40px;height:40px;border-radius:50%;border:0;background:#fff;box-shadow:0 3px 10px rgba(0,0,0,.28);padding:0;cursor:pointer}
#navNorth[hidden]{display:none}#navNorth i{display:block;width:100%;height:100%;transition:transform ${C.ROTATE_MS}ms ease-out;font:900 11px Nunito,system-ui,sans-serif;color:#e5484d;position:relative}
#navNorth i:before{content:'';position:absolute;left:50%;top:7px;margin-left:-5px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:12px solid #e5484d}
#navNorth i:after{content:'N';position:absolute;left:0;right:0;bottom:6px;text-align:center;color:#0b3a78}`;
  function injectCss() {
    if (typeof document === 'undefined' || document.getElementById('navFollowCss')) return;
    const s = document.createElement('style'); s.id = 'navFollowCss'; s.textContent = CSS; document.head.appendChild(s);
  }
  const DOT = '<div class="me-wrap"><div class="me-cone"></div><div class="me-dot"></div></div>';

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
    let navigating = false, following = false, heading = null, compass = null, last = null, prevLL = null;
    let timer = 0, rerouting = false, moving = 0, previewing = false;
    let mapBearing = null; // unwrapped; null = north-up
    const rot = rotator(map);
    const ctl = document.createElement('div');
    ctl.id = 'navCtl';
    ctl.innerHTML = '<button type="button" id="navStart" hidden>▶ Start</button><button type="button" id="navRecenter" hidden>◎ Recenter</button><button type="button" id="navEnd" hidden>■ End</button>';
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
      if (t == null) return;
      const nb = nextBearing(mapBearing, t);
      if (nb !== mapBearing) { mapBearing = nb; paintHeading(true); }
    }
    // Paint the heading at most once per frame, only when it moved >= 3 deg or toggled on/off.
    // deviceorientation fires ~60/s on iPhone; painting every event (querySelectorAll + style write)
    // kept the main thread busy and made typing lag (Oct 31 2026).
    let painted, paintQueued = 0;
    function paintHeading(force) {
      if (force === true) painted = undefined;
      if (paintQueued) return;
      const raf = root.requestAnimationFrame || (f => setTimeout(f, 16));
      paintQueued = raf(() => {
        paintQueued = 0;
        const mb = headingUp() && mapBearing != null ? mapBearing : null;
        if (rot && (rot.get() || 0) !== (mb || 0)) rot.set(mb, C.FOLLOW_Y);
        north.firstChild.style.transform = mb ? 'rotate(' + (-mb) + 'deg)' : '';
        // Heading-up: the dot lives inside the turned map, so giving the arrow the map bearing points it straight up on screen.
        const h = heading == null && mb == null ? null : (mb != null ? Math.round(((mb % 360) + 360) % 360) : Math.round(heading));
        if (painted !== undefined && (h == null) === (painted == null) && (h == null || Math.abs(((h - painted + 540) % 360) - 180) < 3)) return;
        painted = h;
        root.__navHeadingPaints = (root.__navHeadingPaints || 0) + 1;
        document.querySelectorAll('.me-wrap').forEach(el => {
          el.classList.toggle('has-hd', h != null);
          if (h != null) el.style.setProperty('--hd', h + 'deg');
        });
      });
    }
    // Keep the dot a bit below center. Cheap: skip when it is already within a few px of the target.
    function center(ll) {
      if (!map || !ll) return;
      const z = Math.max(map.getZoom(), C.FOLLOW_ZOOM), sz = map.getSize();
      const off = L.point(0, sz.y * (C.FOLLOW_Y - 0.5));
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
    function userMoved() { if (!touching || !navigating || !following) return; following = false; paintBtns(); }
    if (map) {
      const el = map.getContainer();
      const down = () => { touching = true; }, up = () => { setTimeout(() => { touching = false; }, 0); };
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
        Promise.resolve(opts.reroute([last.latitude, last.longitude])).catch(() => {}).finally(() => { rerouting = false; track.reset(); });
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
        if (h != null) heading = h; else if (!Number.isFinite(compass)) heading = null;
        if (!prevLL || hav(prevLL, [coords.latitude, coords.longitude]) >= 8) prevLL = [coords.latitude, coords.longitude];
        last = coords;
        aimBearing();
        paintHeading();
        if (navigating && following) center([coords.latitude, coords.longitude]);
        check(Date.now());
      },
      preview(on) { previewing = !!on; if (!on && navigating) api.end(); paintBtns(); },
      start() {
        if (navigating) return;
        if (opts.canStart && !opts.canStart()) return;
        navigating = true; following = true; track.reset();
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
  const api = { C, offTracker, compassFrom, pickHeading, routeBearing, nextBearing, courseHeading, pointAt, controller, DOT };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMFollow = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
