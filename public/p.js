/* Renter page at /p/<slug> and /p/<slug>/go?code=.
   Locked: waitlist-style landing. Unlocked: full-screen map, experience sheet, Start experience. */
const panel = document.getElementById('panel');
const titleEl = document.getElementById('title');
const blurbEl = document.getElementById('blurb');
const eyebrowEl = document.getElementById('eyebrow');
const fullMap = document.getElementById('fullMap');
const ticker = document.getElementById('ticker');
const mapCard = document.getElementById('mapCard');
const confetti = document.getElementById('confetti');
const logoEl = document.getElementById('logo');
const nextBar = document.getElementById('nextBar');
const nextLabel = document.getElementById('nextLabel');
const nextBtn = document.getElementById('nextBtn');

function slugFromPath() {
  const parts = location.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
  if (parts[0] === 'p' && parts[1]) return parts[1].toLowerCase();
  return '';
}

const slug = slugFromPath();
const params = new URLSearchParams(location.search);
const codeParam = (params.get('code') || '').trim().toUpperCase();
const isGo = /\/go\/?$/.test(location.pathname) || !!codeParam;

let map, pins = null, routeLayer = null, liveLayer = null, regions = [], region = null, rules = null;
let unlocked = null, activeEx = null, stopIdx = 0, drawToken = 0, startToken = 0;
let roadApi = null, roadKey = '', roadChain = Promise.resolve();
let roadCanvas = null, roadCtx = null, routeR = null, roadTimer = 0, roadPaintToken = 0;
let meLL = null, meMarker = null, guided = false;
const affMarks = [];

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function reduceMotion() {
  return matchMedia('(prefers-reduced-motion: reduce)').matches;
}
function motion() {
  return reduceMotion() ? 'auto' : 'smooth';
}
function setRouteNote(text) {
  const el = document.getElementById('routeNote');
  if (el) el.textContent = text;
}
function setStartNote(text) {
  const el = document.getElementById('startNote');
  if (el) el.textContent = text;
}

async function loadRegions() {
  if (regions.length) return regions;
  regions = await fetch('/data/regions.json').then(r => r.json());
  return regions;
}
async function loadRules() {
  if (rules) return rules;
  rules = await fetch('/data/rules.json').then(r => r.json());
  return rules;
}

function onBrand(color) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(color || '').trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  const lin = c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const r = lin(parseInt(h.slice(0, 2), 16) / 255);
  const g = lin(parseInt(h.slice(2, 4), 16) / 255);
  const b = lin(parseInt(h.slice(4, 6), 16) / 255);
  const L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const contrast = (a, c) => (Math.max(a, c) + 0.05) / (Math.min(a, c) + 0.05);
  return contrast(L, 1) >= contrast(L, 0.03) ? '#ffffff' : '#073044';
}
function applyColor(color) {
  const c = String(color || '').trim();
  if (!c || /[;{}]|url\s*\(/i.test(c)) return;
  const root = document.documentElement;
  root.style.setProperty('--brand', c);
  const on = onBrand(c);
  if (on) {
    root.style.setProperty('--cta', c);
    root.style.setProperty('--on-brand', on);
  } else {
    root.style.setProperty('--cta', '#0b6e86');
    root.style.setProperty('--on-brand', '#ffffff');
  }
}
function safeLogo(url) {
  try {
    const u = new URL(url, location.origin);
    if (u.protocol === 'https:' || u.protocol === 'http:') return u.href;
  } catch (e) { /* ignore bad logo urls */ }
  return '';
}
function pitchFor(shop, open) {
  const b = (shop.blurb || '').trim();
  if (b) return b;
  return open
    ? 'You’re in. Pick a ride and follow the stops.'
    : 'Your cart, the coast, and stops worth pulling over for.';
}
function applyRegion(id) {
  region = regions.find(r => r.id === id) || regions.find(r => r.id === 'sd') || regions[0] || null;
  if (!region) return;
  const citySlug = region.slug || 'sandiego';
  const code = unlocked ? (unlocked.code || codeParam) : '';
  fullMap.href = `/map/${citySlug}?r=${encodeURIComponent(region.id)}&partner=${encodeURIComponent(slug)}${code ? '&code=' + encodeURIComponent(code) : ''}${unlocked ? '&veh=' + shopVeh() : ''}`;
  eyebrowEl.textContent = `☀️ ${region.short || region.name} · hop in`;
}
function applyShop(shop, open) {
  titleEl.textContent = shop.name || 'Golf Cart Maps';
  blurbEl.textContent = pitchFor(shop, open);
  document.title = `${shop.name || 'Partner'} · Golf Cart Maps`;
  applyColor(shop.color);
  const logo = safeLogo(shop.logo_url);
  if (logo) {
    logoEl.hidden = false;
    logoEl.src = logo;
    logoEl.onerror = () => { logoEl.hidden = true; };
  } else {
    logoEl.hidden = true;
    logoEl.removeAttribute('src');
  }
  applyRegion(shop.region_id || 'sd');
}

function setLockedChrome() {
  document.body.classList.remove('is-open', 'has-next');
  ticker.hidden = false;
  mapCard.hidden = true;
  confetti.hidden = true;
  nextBar.classList.remove('show');
  guided = false;
}

function countWord(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}
function statsHTML(data) {
  if (data.experience_count == null && data.affiliate_count == null) return '';
  const ex = Number(data.experience_count) || 0;
  const af = Number(data.affiliate_count) || 0;
  const waiting = ex + af === 0
    ? '<p class="fine">The shop is still packing the cooler. Ask the desk, or check back.</p>'
    : '';
  return `<div class="stats">
    <div class="stat"><b>${ex}</b><span>${countWord(ex, 'experience waiting', 'experiences waiting')}</span></div>
    <div class="stat"><b>${af}</b><span>${countWord(af, 'partner offer', 'partner offers')}</span></div>
  </div>${waiting}`;
}

function renderLocked(data, error) {
  setLockedChrome();
  if (data && data.shop) applyShop(data.shop, false);
  const ex = data && data.experience_count;
  const af = data && data.affiliate_count;
  panel.innerHTML = `${error ? `<div class="msg err" role="alert">${esc(error)}</div>` : ''}
    ${statsHTML({ experience_count: ex, affiliate_count: af })}
    <p class="ask">Got a code from the shop?</p>
    <form class="join" id="unlockForm">
      <label class="sr" for="codeIn">Access code</label>
      <input id="codeIn" name="code" placeholder="Access code" enterkeyhint="go" autocapitalize="characters" autocomplete="off" spellcheck="false" maxlength="64" value="${esc(codeParam)}">
      <button type="submit" id="unlockBtn">Unlock</button>
    </form>
    <p class="fine">Ask your rental shop for a code. Experiences unlock after you pay the add-on at checkout.</p>
    <p class="fine free">The city map is free to use.</p>`;
  document.getElementById('unlockForm').onsubmit = ev => {
    ev.preventDefault();
    const form = ev.currentTarget;
    const input = document.getElementById('codeIn');
    const c = (input.value || '').trim();
    if (!c) {
      form.classList.remove('shake');
      void form.offsetWidth;
      form.classList.add('shake');
      input.focus();
      return;
    }
    location.assign(`/p/${encodeURIComponent(slug)}/go?code=${encodeURIComponent(c.toUpperCase())}`);
  };
}

let leafletP = null;
function loadLeaflet() {
  if (window.L) return Promise.resolve();
  if (leafletP) return leafletP;
  leafletP = new Promise((resolve, reject) => {
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = '/vendor/leaflet/leaflet.css';
    document.head.appendChild(css);
    const s = document.createElement('script');
    s.src = '/vendor/leaflet/leaflet.js';
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('Map failed to load'));
    document.body.appendChild(s);
  });
  return leafletP;
}
function wideMap() {
  return matchMedia('(min-width: 900px)').matches;
}
function framePad() {
  const wide = wideMap();
  const dock = wide ? 36 : Math.round(window.innerHeight * 0.48) + 28;
  return {
    paddingTopLeft: wide ? [408, 78] : [28, 72],
    paddingBottomRight: wide ? [28, dock] : [28, dock],
    maxZoom: 15,
    animate: false,
  };
}
function panIntoView(ll, zoom) {
  if (!map) return;
  const size = map.getSize();
  const wide = wideMap();
  const dock = wide ? 24 : Math.round(window.innerHeight * 0.48);
  const left = wide ? 400 : 0;
  const top = 72;
  const cx = (left + size.x) / 2;
  const cy = (top + Math.max(top + 80, size.y - dock)) / 2;
  const z = zoom || map.getZoom();
  const want = L.point(cx, cy);
  const off = want.subtract(size.divideBy(2));
  const c = map.unproject(map.project(ll, z).subtract(off), z);
  map.setView(c, z, { animate: !reduceMotion() });
}
function frameLatLngs(latlngs) {
  if (!map || !latlngs.length) return;
  if (latlngs.length === 1) {
    panIntoView(L.latLng(latlngs[0][0], latlngs[0][1]), 15);
    return;
  }
  map.fitBounds(latlngs, framePad());
}

function ensureMap() {
  mapCard.hidden = false;
  if (!map) {
    map = L.map('map', { zoomControl: false, attributionControl: true }).setView(region ? region.center : [32.8565, -117.2555], (region && region.zoom) || 13);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    }).addTo(map);
    L.control.zoom({ position: 'topright' }).addTo(map);
    map.createPane('roads');
    const roadsPane = map.getPane('roads');
    roadsPane.style.zIndex = '410';
    roadsPane.style.pointerEvents = 'none';
    roadCanvas = document.createElement('canvas');
    roadCanvas.className = 'road-canvas';
    roadsPane.appendChild(roadCanvas);
    roadCtx = roadCanvas.getContext('2d');
    map.createPane('route');
    const routePane = map.getPane('route');
    routePane.style.zIndex = '450';
    routePane.style.pointerEvents = 'none';
    routeR = L.svg({ pane: 'route' });
    pins = L.layerGroup().addTo(map);
    routeLayer = L.layerGroup().addTo(map);
    liveLayer = L.layerGroup().addTo(map);
    map.on('moveend', scheduleRoads);
  }
  map.invalidateSize();
}

function scheduleRoads() {
  clearTimeout(roadTimer);
  roadTimer = setTimeout(paintRoads, 60);
}
function withRoads(fn) {
  const run = roadChain.then(fn, fn);
  roadChain = run.then(() => {}, () => {});
  return run;
}
async function paintRoads() {
  if (!map || !roadApi || !roadApi.cover) return;
  const token = ++roadPaintToken;
  const b = map.getBounds();
  const pad = 0.04;
  try {
    await withRoads(() => roadApi.cover(b.getSouth() - pad, b.getWest() - pad, b.getNorth() + pad, b.getEast() + pad));
  } catch (e) {
    return;
  }
  if (token !== roadPaintToken || !map) return;
  drawRoadCanvas();
}
function drawRoadCanvas() {
  if (!roadCanvas || !map || !roadApi || !roadApi.segments) return;
  const size = map.getSize();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  roadCanvas.width = Math.max(1, Math.round(size.x * dpr));
  roadCanvas.height = Math.max(1, Math.round(size.y * dpr));
  roadCanvas.style.width = size.x + 'px';
  roadCanvas.style.height = size.y + 'px';
  L.DomUtil.setPosition(roadCanvas, map.containerPointToLayerPoint([0, 0]));
  const ctx = roadCtx;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size.x, size.y);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const view = map.getBounds().pad(0.08);
  const south = view.getSouth(), north = view.getNorth(), west = view.getWest(), east = view.getEast();
  const segs = roadApi.segments();
  for (let n = 0; n < segs.length; n++) {
    const s = segs[n];
    const pts = s[7];
    if (!pts || pts.length < 2) continue;
    let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
    for (let i = 0; i < pts.length; i++) {
      const lon = pts[i][0], lat = pts[i][1];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    }
    if (maxLat < south || minLat > north || maxLon < west || minLon > east) continue;
    const st = roadApi.roadStyle(s);
    ctx.beginPath();
    for (let i = 0; i < pts.length; i++) {
      const pt = map.latLngToContainerPoint([pts[i][1], pts[i][0]]);
      if (i === 0) ctx.moveTo(pt.x, pt.y);
      else ctx.lineTo(pt.x, pt.y);
    }
    ctx.globalAlpha = st.opacity == null ? 1 : st.opacity;
    ctx.strokeStyle = st.color;
    ctx.lineWidth = st.weight;
    ctx.setLineDash(st.dashArray ? st.dashArray.split(/[\s,]+/).map(Number) : []);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
  ctx.setLineDash([]);
}

function stopIcon(n) {
  return L.divIcon({
    className: '',
    html: `<div class="pin-stop"><span>${n}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
  });
}
function affIcon() {
  return L.divIcon({
    className: '',
    html: '<div class="pin-aff">★</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}
function meIcon() {
  return L.divIcon({
    className: '',
    html: '<div class="me-dot"></div>',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}
function finite(lat, lon) {
  return Number.isFinite(+lat) && Number.isFinite(+lon);
}
function placeMe() {
  if (meMarker) {
    map.removeLayer(meMarker);
    meMarker = null;
  }
  if (!map || !meLL) return;
  meMarker = L.marker([meLL.lat, meLL.lon], { icon: meIcon(), zIndexOffset: 1000, interactive: false, keyboard: false }).addTo(map);
}

// Bold casing matches the city map route: dark edge, white, then #1d6fe0.
// A short off-network hop stays a thin dash, never this casing.
function addRouteLine(points, layer, dashed) {
  const base = { renderer: routeR, opacity: 1, lineCap: 'round', lineJoin: 'round', interactive: false, pane: 'route' };
  if (dashed) {
    L.polyline(points, { ...base, color: '#1d6fe0', weight: 3, opacity: 0.75, dashArray: '4 8' }).addTo(layer);
    return;
  }
  L.polyline(points, { ...base, color: '#0b3a78', weight: 22 }).addTo(layer);
  L.polyline(points, { ...base, color: '#fff', weight: 18 }).addTo(layer);
  L.polyline(points, { ...base, color: '#1d6fe0', weight: 12 }).addTo(layer);
}

// The shop's rental vehicle picks the road rules. Unset means golf cart (stricter).
function shopVeh() { const s = unlocked && unlocked.shop; return s && s.vehicle === 'lsv' ? 'lsv' : 'golf_cart'; }
function vehWord() { return shopVeh() === 'lsv' ? 'street-legal LSV' : 'golf cart'; }
function vehLegend() {
  return shopVeh() === 'lsv'
    ? 'Street-legal LSV rules: roads up to 35 mph.'
    : 'Golf cart rules: roads up to 25 mph.';
}

function connectStops(stops) {
  return withRoads(async () => {
    await loadRules();
    const veh = shopVeh();
    const key = (region && region.id || 'sd') + ':' + veh;
    if (!roadApi || roadKey !== key) {
      roadApi = await GCMRouter.openRegion(region, rules, veh);
      roadKey = key;
    }
    return roadApi.legs(stops);
  });
}
function describeRoute(legs, nStops) {
  if (nStops < 2) return nStops ? 'One stop. Hit Start experience to route there from you.' : '';
  if (!legs) return 'Roads didn’t load. The stops are still pinned.';
  const skipped = legs.filter(l => !l.points).length;
  if (skipped) return `Follows legal ${vehWord()} roads. A hop off that network is left open.`;
  if (legs.some(l => l.dashed) && !legs.some(l => l.points && !l.dashed)) return 'A short hop off the mapped roads.';
  return `The line follows legal ${vehWord()} roads.`;
}

async function drawUnlocked() {
  const token = ++drawToken;
  if (!map || !pins || !routeLayer) return;
  const stops = (activeEx && activeEx.stops) || [];
  const goodStops = stops.filter(s => finite(s.lat, s.lon));
  let legs = null;
  if (goodStops.length > 1) {
    setRouteNote(`Tracing ${vehWord()} roads…`);
    try { legs = await connectStops(goodStops); }
    catch (e) { legs = null; }
  }
  if (token !== drawToken || !pins) return;
  routeLayer.clearLayers();
  pins.clearLayers();
  affMarks.length = 0;
  const bounds = [];
  (legs || []).forEach(leg => {
    if (!leg.points || leg.points.length < 2) return;
    addRouteLine(leg.points, routeLayer, leg.dashed);
    leg.points.forEach(p => bounds.push(p));
  });
  (unlocked.affiliates || []).forEach(a => {
    if (!finite(a.lat, a.lon)) return;
    const m = L.marker([+a.lat, +a.lon], { icon: affIcon(), zIndexOffset: 600 }).addTo(pins);
    m.bindPopup(`<b>${esc(a.name)}</b><br>${esc(a.offer || '')}${a.coupon ? `<br>Coupon: <code>${esc(a.coupon)}</code>` : ''}<br><span class="muted">Partner offer</span>`);
    affMarks.push({ id: a.id, marker: m });
    bounds.push([+a.lat, +a.lon]);
  });
  if (activeEx) {
    (activeEx.stops || []).forEach((s, i) => {
      if (!finite(s.lat, s.lon)) return;
      const m = L.marker([+s.lat, +s.lon], { icon: stopIcon(i + 1), zIndexOffset: 700 }).addTo(pins);
      m.bindPopup(`<b>${i + 1}. ${esc(s.label)}</b>${s.note ? `<br>${esc(s.note)}` : ''}`);
      bounds.push([+s.lat, +s.lon]);
    });
  }
  setRouteNote(describeRoute(legs, goodStops.length));
  if (bounds.length) frameLatLngs(bounds);
  scheduleRoads();
  updateNext();
}

function updateNext(opts) {
  const stops = activeEx && activeEx.stops;
  if (!guided || !stops || !stops.length || !stops.some(s => finite(s.lat, s.lon))) {
    nextBar.classList.remove('show');
    document.body.classList.remove('has-next');
    return;
  }
  const usable = stops.map((s, i) => ({ s, i })).filter(x => finite(x.s.lat, x.s.lon));
  if (!usable.length) {
    nextBar.classList.remove('show');
    document.body.classList.remove('has-next');
    return;
  }
  if (!usable.some(x => x.i === stopIdx)) stopIdx = usable[0].i;
  nextBar.classList.add('show');
  document.body.classList.add('has-next');
  const s = stops[stopIdx];
  nextLabel.textContent = `Stop ${stopIdx + 1}/${stops.length}: ${s.label || 'Stop'}`;
  if (opts && opts.pan && map && finite(s.lat, s.lon)) panIntoView(L.latLng(+s.lat, +s.lon), 16);
}
nextBtn.onclick = () => {
  const stops = activeEx && activeEx.stops;
  if (!guided || !stops || !stops.length) return;
  stopIdx = (stopIdx + 1) % stops.length;
  updateNext({ pan: true });
};

function locateMe() {
  if (!navigator.geolocation || !navigator.geolocation.getCurrentPosition) return Promise.resolve(null);
  return new Promise(resolve => {
    let done = false;
    const finish = v => {
      if (done) return;
      done = true;
      resolve(v);
    };
    const timer = setTimeout(() => finish(null), 8500);
    navigator.geolocation.getCurrentPosition(
      p => {
        clearTimeout(timer);
        const lat = p.coords.latitude, lon = p.coords.longitude;
        finish(finite(lat, lon) ? { lat, lon } : null);
      },
      () => { clearTimeout(timer); finish(null); },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 15000 }
    );
  });
}
function clearLiveRoute() {
  if (liveLayer) liveLayer.clearLayers();
  setStartNote('');
}
async function startExperience() {
  const token = ++startToken;
  const btn = document.getElementById('startEx');
  const stops = ((activeEx && activeEx.stops) || []).filter(s => finite(s.lat, s.lon));
  if (!map || !stops.length) {
    setStartNote('This ride has no stops yet.');
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Finding you…';
  }
  let from = meLL;
  let usedCenter = false;
  if (!from) {
    const loc = await locateMe();
    if (token !== startToken) return;
    if (loc) {
      meLL = loc;
      from = loc;
      placeMe();
    }
  }
  if (!from) {
    const c = map.getCenter();
    from = { lat: c.lat, lon: c.lng };
    usedCenter = true;
  }
  if (btn) btn.textContent = 'Routing…';
  const first = stops[0];
  let legs = null;
  try { legs = await connectStops([from, first]); }
  catch (e) { legs = null; }
  if (token !== startToken || !liveLayer) return;
  liveLayer.clearLayers();
  const leg = legs && legs[0];
  const drawn = !!(leg && leg.points && leg.points.length >= 2);
  if (drawn) addRouteLine(leg.points, liveLayer, leg.dashed);
  if (usedCenter && !drawn) {
    setStartNote(`Location is off, and there’s no legal ${vehWord()} road from the middle of the map to the first stop. Turn on location, or follow the pins.`);
  } else if (usedCenter) {
    setStartNote(leg.dashed
      ? 'Location is off. Turn it on to start from you. This short hop starts from the middle of the map.'
      : 'Location is off. Turn it on to start from you. This route starts from the middle of the map.');
  } else if (!drawn) {
    setStartNote(`No legal ${vehWord()} road from here to the first stop. The pins still mark each stop.`);
  } else if (leg.dashed) {
    setStartNote('A short hop from you to the first stop.');
  } else {
    setStartNote('Legal golf cart roads from you to the first stop.');
  }
  guided = true;
  stopIdx = 0;
  if (drawn) frameLatLngs(leg.points);
  else panIntoView(L.latLng(+first.lat, +first.lon), 15);
  updateNext();
  scheduleRoads();
  if (btn) {
    btn.disabled = false;
    btn.textContent = 'Start experience';
  }
}

function markActive(id) {
  panel.querySelectorAll('.xcard').forEach(el => {
    const on = el.dataset.ex === id;
    el.classList.toggle('active', on);
    el.setAttribute('aria-pressed', on ? 'true' : 'false');
    const go = el.querySelector('.xgo');
    if (go) go.textContent = on ? 'Stops on the map' : 'Show stops';
  });
}
function selectEx(id) {
  const ex = (unlocked && unlocked.experiences) || [];
  activeEx = ex.find(x => x.id === id) || null;
  stopIdx = 0;
  guided = false;
  startToken++;
  clearLiveRoute();
  markActive(id);
  const btn = document.getElementById('startEx');
  if (btn) {
    btn.disabled = false;
    btn.textContent = 'Start experience';
  }
  drawUnlocked();
}

async function unlockedView() {
  const shop = unlocked.shop;
  applyShop(shop, true);
  document.body.classList.add('is-open');
  ticker.hidden = true;
  confetti.hidden = reduceMotion();
  const ex = unlocked.experiences || [];
  const af = unlocked.affiliates || [];
  const code = unlocked.code || codeParam;
  panel.innerHTML = `
    <div class="dock-scroll" id="dockScroll">
      <div class="yay">
        <p class="yay-kicker">You’re in</p>
        <p>Code <b>${esc(code)}</b> unlocked ${esc(shop.name)}. Pick a ride, then start from where you are.</p>
      </div>
      <h2 class="sec">Experiences</h2>
      <p class="subsec">Tap one. Its stops light up on the map.</p>
      ${ex.map((e, i) => `<button class="xcard" type="button" data-ex="${esc(e.id)}" aria-pressed="false">
        <span class="xmeta"><span class="num">${String(i + 1).padStart(2, '0')}</span><span class="chip">${(e.stops || []).length} ${(e.stops || []).length === 1 ? 'stop' : 'stops'}</span></span>
        <span class="xtitle">${esc(e.title)}</span>
        ${e.description ? `<span class="xdesc">${esc(e.description)}</span>` : ''}
        <span class="xgo">Show stops</span>
      </button>`).join('') || '<p class="fine">No rides pinned yet. Ask the shop — partner offers may still be on the map.</p>'}
      <h2 class="sec">Partner offers</h2>
      ${af.map(a => `<button class="ocard" type="button" data-af="${esc(a.id)}">
        <span class="star" aria-hidden="true">★</span>
        <span><span class="xtitle">${esc(a.name)}</span><span class="xdesc">${esc(a.offer || 'Partner offer')}${a.coupon ? ` · coupon <code>${esc(a.coupon)}</code>` : ''}</span></span>
      </button>`).join('') || '<p class="fine">No partner offers yet.</p>'}
      <p class="legend">Green roads are legal for a ${esc(vehWord())}. Red roads are off limits. The blue line is your route.</p>
      <p class="legend muted" id="vehLegend">${esc(vehLegend())}</p>
      <p class="legend">Numbered pins are stops. Amber ★ pins are partner offers.</p>
      <p class="legend" id="routeNote" aria-live="polite"></p>
    </div>
    ${ex.length ? `<div class="dock-foot"><button class="start" id="startEx" type="button">Start experience</button><p class="fine" id="startNote" aria-live="polite"></p></div>` : ''}`;
  panel.querySelectorAll('.xcard').forEach(el => {
    el.onclick = () => selectEx(el.dataset.ex);
  });
  panel.querySelectorAll('.ocard').forEach(el => {
    el.onclick = () => {
      const hit = affMarks.find(a => a.id === el.dataset.af);
      if (hit && map) {
        panIntoView(hit.marker.getLatLng(), Math.max(map.getZoom(), 15));
        hit.marker.openPopup();
      }
    };
  });
  const startBtn = document.getElementById('startEx');
  if (startBtn) startBtn.onclick = () => { startExperience(); };
  if (ex[0]) {
    activeEx = ex[0];
    markActive(ex[0].id);
  }
  try {
    await loadLeaflet();
    ensureMap();
    await new Promise(r => requestAnimationFrame(r));
    map.invalidateSize();
    await drawUnlocked();
  } catch (e) {
    setRouteNote('Map couldn’t load. Your stops are still listed above.');
    mapCard.hidden = false;
  }
}

async function boot() {
  if (!slug) {
    setLockedChrome();
    titleEl.textContent = 'Missing shop';
    blurbEl.textContent = 'This link needs a shop name on the end.';
    panel.innerHTML = '<div class="msg err">Open a shop link like /p/your-shop.</div>';
    return;
  }
  try {
    await loadRegions();
  } catch (e) {
    panel.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
    return;
  }
  try {
    if (isGo && codeParam) {
      const r = await fetch(`/api/partner/public/${encodeURIComponent(slug)}/unlock?code=${encodeURIComponent(codeParam)}`);
      const j = await r.json();
      if (!r.ok) {
        renderLocked(j.shop ? { shop: j.shop } : null, j.error || 'Could not unlock');
        return;
      }
      unlocked = j;
      await unlockedView();
    } else {
      const r = await fetch(`/api/partner/public/${encodeURIComponent(slug)}`);
      const j = await r.json();
      if (!r.ok) {
        setLockedChrome();
        titleEl.textContent = 'Shop not found';
        blurbEl.textContent = 'That link doesn’t match a rental shop.';
        ticker.hidden = true;
        panel.innerHTML = `<div class="msg err">${esc(j.error || 'Shop not found')}</div>`;
        return;
      }
      renderLocked(j);
    }
  } catch (e) {
    panel.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

boot();
