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
const placeMarks = [];
const PLACE_UI = { restaurant: ['🍽️', 'Restaurant'], views: ['🌅', 'Views'], trivia: ['❓', 'Trivia'], fun_fact: ['💡', 'Fun fact'], other: ['📍', 'Other'] };
const placeUi = c => PLACE_UI[c] || PLACE_UI.other;

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

// Max (Oct 29 2026): partner and renter maps can't be cached; they must have the latest map.
// Every data request skips the HTTP cache. public/sw.js marks a copy it served offline with X-GCM-Offline.
let roadStamp = '';
function offlineNotice(on) {
  let el = document.getElementById('mapStale');
  if (!on) { if (el) el.hidden = true; return; }
  if (!el) {
    el = document.createElement('div');
    el.id = 'mapStale';
    el.setAttribute('role', 'status');
    el.style.cssText = 'position:fixed;left:12px;right:12px;top:12px;z-index:9999;padding:10px 14px;border-radius:12px;background:#7a2e00;color:#fff;font:600 14px/1.3 system-ui,sans-serif;text-align:center;box-shadow:0 4px 14px rgba(0,0,0,.25)';
    el.textContent = 'Offline, map may be outdated. Reconnect to load the latest roads.';
    document.body.appendChild(el);
  }
  el.hidden = false;
}
async function freshFetch(url) {
  let r;
  try { r = await fetch(url, { cache: 'no-store' }); }
  catch (e) { offlineNotice(true); throw e; }
  offlineNotice(r.headers.get('X-GCM-Offline') === '1');
  if (/\/index\.json$/.test(url) && r.ok) {
    try { const m = (await r.clone().json()).meta || {}; roadStamp = `${m.generated}|${m.segments}|${m.ways}`; } catch (e) { /* keep old stamp */ }
  }
  return r;
}
// Re-check the road index when the page is opened again (tab focus, phone unlocked). New data: reload roads and redraw.
async function recheckRoads() {
  if (!region) return;
  const before = roadStamp;
  try { await freshFetch('/data/' + region.id + '/index.json'); } catch (e) { return; }
  if (before && roadStamp && roadStamp !== before && roadApi) {
    roadApi = null; roadKey = '';
    try { await drawUnlocked(); } catch (e) { /* the next draw retries */ }
  }
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') recheckRoads(); });
addEventListener('focus', () => recheckRoads());
addEventListener('pageshow', e => { if (e.persisted) recheckRoads(); });
window.GCMPartnerFresh = { recheckRoads, stamp: () => roadStamp };

async function loadRegions() {
  if (regions.length) return regions;
  regions = await freshFetch('/data/regions.json').then(r => r.json());
  return regions;
}
async function loadRules() {
  if (rules) return rules;
  rules = await freshFetch('/data/rules.json').then(r => r.json());
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
  fullMap.hidden = !!open;
  const hb = document.getElementById('goTop');
  if (hb) hb.hidden = !open;
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
  return matchMedia('(min-width:900px),(min-width:600px) and (min-height:600px)').matches;
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
    follow = GCMFollow.controller({
      map,
      getRoute: () => navRoute,
      reroute: navReroute,
      say: t => say(t),
      onStart: () => { navSpoken = ''; say(document.getElementById('navText') ? document.getElementById('navText').textContent : ''); },
      onEnd: () => { if (window.speechSynthesis) speechSynthesis.cancel(); },
    });
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
    // Fold/unfold (iPhone Duo), rotation, split view: resize the map, keep route and live position.
    const refit = () => requestAnimationFrame(() => { try { map.invalidateSize({ pan: false }); } catch (_) {} });
    addEventListener('resize', refit); addEventListener('orientationchange', refit);
    if (window.visualViewport) visualViewport.addEventListener('resize', refit);
    map.on('click', e => { if (freeOn) pickDest({ name: 'Dropped pin', lat: e.latlng.lat, lon: e.latlng.lng }); });
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
function placeIcon(cat) {
  return L.divIcon({
    className: '',
    html: `<div class="pin-place" data-cat="${esc(cat)}">${placeUi(cat)[0]}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}
function placePopup(p) {
  const [ico, lab] = placeUi(p.category);
  return `<b>${ico} ${esc(p.name)}</b><br><span class="muted">${esc(lab)}</span>${p.note ? `<br>${esc(p.note)}` : ''}${/^https:\/\//i.test(p.link || '') ? `<br><a href="${esc(p.link)}" target="_blank" rel="noopener">More</a>` : ''}`;
}
function meIcon() {
  return L.divIcon({
    className: '',
    html: GCMFollow.DOT,
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
  if (follow) follow.paintHeading();
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
      roadApi = await GCMRouter.openRegion(region, rules, veh, freshFetch);
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
  placeMarks.length = 0;
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
  (unlocked.places || []).forEach(p => {
    if (!finite(p.lat, p.lon)) return;
    const m = L.marker([+p.lat, +p.lon], { icon: placeIcon(p.category), zIndexOffset: 500, title: p.name }).addTo(pins);
    m.bindPopup(placePopup(p));
    placeMarks.push({ id: p.id, marker: m });
    bounds.push([+p.lat, +p.lon]);
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
  if (navWatch != null || navRoute) routeToStop(stopIdx);
};


// ---- Turn-by-turn (public/nav.js). Live GPS moves the banner; off route reroutes on legal roads.
const ARROWS = { straight: '↑', 'slight right': '↗', right: '↱', 'sharp right': '↘', 'slight left': '↖', left: '↰', 'sharp left': '↙', arrive: '⚑' };
let navRoute = null, navState = null, navStop = -1, navWatch = null, navSpoken = '', navRerouting = false, navArrived = false;
let follow = null;
let navMuted = (() => { try { return localStorage.getItem('gcm_nav_mute') === '1'; } catch (e) { return false; } })();
function navEl() {
  let el = document.getElementById('navBanner');
  if (el) return el;
  el = document.createElement('section');
  el.id = 'navBanner';
  el.setAttribute('aria-live', 'polite');
  el.innerHTML = `<div class="nav-row"><span class="nav-arrow" id="navArrow" aria-hidden="true">↑</span>
    <div class="nav-main"><b id="navText">Starting…</b><span id="navSub"></span></div>
    <button type="button" id="navMute" class="nav-btn" aria-pressed="false"></button></div>
    <div class="nav-acts"><button type="button" id="navListBtn" class="nav-link" aria-expanded="false">All steps</button>
    <button type="button" id="navGo" class="nav-go" hidden></button></div>
    <ol id="navSteps" hidden></ol>`;
  document.body.appendChild(el);
  el.querySelector('#navMute').onclick = () => {
    navMuted = !navMuted;
    try { localStorage.setItem('gcm_nav_mute', navMuted ? '1' : '0'); } catch (e) {}
    if (navMuted && window.speechSynthesis) speechSynthesis.cancel();
    paintMute();
  };
  el.querySelector('#navListBtn').onclick = () => {
    const ol = el.querySelector('#navSteps'), b = el.querySelector('#navListBtn');
    ol.hidden = !ol.hidden;
    b.setAttribute('aria-expanded', ol.hidden ? 'false' : 'true');
    b.textContent = ol.hidden ? 'All steps' : 'Hide steps';
  };
  paintMute();
  return el;
}
function paintMute() {
  const b = document.getElementById('navMute');
  if (!b) return;
  b.textContent = navMuted ? '🔇' : '🔊';
  b.setAttribute('aria-pressed', navMuted ? 'true' : 'false');
  b.setAttribute('aria-label', navMuted ? 'Unmute voice directions' : 'Mute voice directions');
}
function say(text) {
  // Preview is silent; voice starts with Start.
  if (follow && !follow.state().navigating) return;
  if (navMuted || !text || text === navSpoken) return;
  navSpoken = text;
  window.__navSaid = (window.__navSaid || []).concat(text);
  try {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
    speechSynthesis.cancel();
    speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  } catch (e) {}
}
// Read-only hook for browser tests (route points + steps).
window.GCMNavDebug = () => navRoute && { pts: navRoute.pts, steps: navRoute.steps, stop: navStop };
function stopNav() {
  if (navWatch != null && navigator.geolocation) navigator.geolocation.clearWatch(navWatch);
  navWatch = null; navRoute = null; navState = null; navStop = -1; navArrived = false;
  const el = document.getElementById('navBanner');
  if (el) el.classList.remove('show');
  document.body.classList.remove('has-nav');
  if (follow) follow.preview(false);
}
function beginNav(leg, i, target) {
  const stops = activeEx && activeEx.stops;
  const stop = target || (stops && stops[i]);
  if (!stop || !leg || !leg.points || leg.points.length < 2) { stopNav(); return; }
  const runs = leg.runs && leg.runs.length ? leg.runs : [{ name: '', points: leg.points }];
  navRoute = GCMNav.buildSteps(runs, stop.label || `stop ${i + 1}`);
  navStop = target ? -1 : i; navState = null; navArrived = false; navSpoken = '';
  const el = navEl();
  el.classList.add('show');
  document.body.classList.add('has-nav');
  el.querySelector('#navGo').hidden = true;
  el.querySelector('#navSteps').innerHTML = navRoute.steps.map(st =>
    `<li data-i="${navRoute.steps.indexOf(st)}" tabindex="0"><span class="nav-arrow sm" aria-hidden="true">${ARROWS[st.mod] || '↑'}</span><span>${esc(st.text)}</span><span class="muted">${st.kind === 'arrive' ? '' : GCMNav.fmtDist(st.len).replace('Now', '<50 ft')}</span></li>`).join('');
  const first = navRoute.steps[0], second = navRoute.steps[1];
  paintNav(ARROWS[first.mod], first.text, second ? `Then ${second.text.charAt(0).toLowerCase() + second.text.slice(1)} in ${GCMNav.fmtDist(second.at)}` : '');
  // Tap a step to look at that maneuver. This pauses follow until Recenter.
  el.querySelectorAll('#navSteps li').forEach(li => {
    li.onclick = () => {
      const st = navRoute && navRoute.steps[+li.dataset.i];
      if (!st || !map) return;
      if (follow) follow.pause();
      map.setView(L.latLng(st.ll[0], st.ll[1]), 18, { animate: !reduceMotion() });
    };
  });
  if (follow) follow.preview(true);
  say(first.text);
  if (meLL) onNavFix({ lat: meLL.lat, lon: meLL.lon });
  if (navWatch == null && navigator.geolocation && navigator.geolocation.watchPosition) {
    navWatch = navigator.geolocation.watchPosition(
      p => onNavFix({ lat: p.coords.latitude, lon: p.coords.longitude, coords: p.coords }),
      () => {}, { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 });
  }
}
function paintNav(arrow, text, sub) {
  const el = navEl();
  el.querySelector('#navArrow').textContent = arrow || '↑';
  el.querySelector('#navText').textContent = text;
  el.querySelector('#navSub').textContent = sub || '';
}
async function onNavFix(ll) {
  if (!finite(ll.lat, ll.lon)) return;
  meLL = { lat: ll.lat, lon: ll.lon };
  placeMe();
  if (follow) follow.fix(ll.coords || { latitude: ll.lat, longitude: ll.lon });
  if (!navRoute || navArrived || navRerouting) return;
  const st = GCMNav.status(navRoute, [ll.lat, ll.lon], navState);
  navState = st;
  const stops = (activeEx && activeEx.stops) || [];
  if (st.arrived && navStop < 0) {
    navArrived = true;
    paintNav('⚑', `You’ve arrived at ${freeDest.label}`, 'Back to experiences any time.');
    navEl().querySelector('#navGo').hidden = true;
    say(`You’ve arrived at ${freeDest.label}.`);
    return;
  }
  if (st.arrived) {
    navArrived = true;
    const here = stops[navStop];
    const nxt = stops.findIndex((s, k) => k > navStop && finite(s.lat, s.lon));
    paintNav('⚑', `You’ve arrived at ${here.label || 'the stop'}`, nxt >= 0 ? `Next: stop ${nxt + 1}, ${stops[nxt].label || ''}` : 'That was the last stop. Nice ride!');
    const go = navEl().querySelector('#navGo');
    if (nxt >= 0) {
      go.hidden = false;
      go.textContent = `Go to stop ${nxt + 1}`;
      go.onclick = () => routeToStop(nxt);
    } else go.hidden = true;
    say(`You’ve arrived at ${here.label || 'the stop'}.` + (nxt >= 0 ? ` Next stop: ${stops[nxt].label || ''}.` : ''));
    return;
  }
  // Off route: GCMFollow waits ~5 s past 30 m, then calls navReroute (debounced).
  const after = navRoute.steps[st.idx + 1];
  paintNav(ARROWS[st.next.mod], st.text,
    (after ? `Then ${after.text.charAt(0).toLowerCase() + after.text.slice(1)} · ` : '') + `${GCMNav.fmtDist(st.remaining).replace('Now', 'under 50 ft')} to go`);
  // Speak once per maneuver when it is near (≈400 ft), and again at the turn.
  if (st.toNext < 120) say(st.toNext < 25 ? st.next.text : st.text);
}
// Off route for a while during navigation: new legal route from here to the same stop or place.
async function navReroute() {
  navRerouting = true;
  paintNav('↻', 'Rerouting on legal roads…', '');
  try { if (navStop < 0) await routeFree(freeDest, true); else await routeToStop(navStop, true); } finally { navRerouting = false; }
}
// Route from the current position to stop i on legal roads, draw it, and guide.
async function routeToStop(i, quiet) {
  const stops = activeEx && activeEx.stops;
  const stop = stops && stops[i];
  if (!stop || !finite(stop.lat, stop.lon)) return;
  stopIdx = i;
  updateNext();
  const from = meLL || (map && { lat: map.getCenter().lat, lon: map.getCenter().lng });
  let legs = null;
  try { legs = await connectStops([from, stop]); } catch (e) { legs = null; }
  const leg = legs && legs[0];
  if (liveLayer) liveLayer.clearLayers();
  if (leg && leg.points && leg.points.length >= 2) {
    addRouteLine(leg.points, liveLayer, leg.dashed);
    if (!quiet) frameLatLngs(leg.points);
    beginNav(leg, i);
  } else {
    paintNav('⚠', 'No legal golf cart road from here', `Follow the pin to stop ${i + 1}.`);
    navRoute = null;
  }
}

// ---- Navigate somewhere else: normal search / drop pin / Legal only vs Risky, inside the renter page.
let freeDest = null, freeRisky = false, freeMark = null, freeOn = false, freeTimer = 0, poiList = null;
async function loadPois() {
  if (poiList) return poiList;
  try { poiList = await freshFetch(`/data/${region.id}/pois.json`).then(r => r.json()); } catch (e) { poiList = []; }
  return poiList;
}
async function searchPlaces(q) {
  const n = q.toLowerCase().trim();
  if (n.length < 2) return [];
  const out = [];
  (await loadPois()).forEach(p => {
    const pn = String(p[0]).toLowerCase();
    if (pn.includes(n)) out.push({ name: p[0], sub: String(p[1] || 'place').replace('_', ' '), lat: p[3], lon: p[2], score: pn.startsWith(n) ? 0 : 1 });
  });
  if (roadApi) out.push(...roadApi.streets(n, 4));
  out.sort((a, b) => a.score - b.score);
  if (out.length < 3 && region && region.bbox) {
    try {
      const b = region.bbox, c = map.getCenter();
      const ac = new AbortController(), to = setTimeout(() => ac.abort(), 2500);
      const j = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=5&lat=${c.lat}&lon=${c.lng}&bbox=${b[1]},${b[0]},${b[3]},${b[2]}`, { signal: ac.signal }).then(r => r.json());
      clearTimeout(to);
      j.features.forEach(f => { const p = f.properties; const nm = p.name || [p.housenumber, p.street].filter(Boolean).join(' ');
        if (nm) out.push({ name: nm, sub: [p.city || p.district, p.osm_value].filter(Boolean).join(' · '), lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] }); });
    } catch (e) {}
  }
  return out.slice(0, 6);
}
function freeMode(on) {
  freeOn = !!on;
  document.body.classList.toggle('free-nav', freeOn);
  const pane = document.getElementById('goPane');
  if (pane) pane.hidden = !freeOn;
  if (freeOn) {
    guided = false;
    startToken++;
    stopNav();
    drawToken++;
    [liveLayer, routeLayer, pins].forEach(l => l && l.clearLayers());
    updateNext();
    const inp = document.getElementById('goQ');
    if (inp) inp.focus({ preventScroll: true });
    if (!meLL) locateMe().then(l => { if (l) { meLL = l; placeMe(); } });
  } else {
    stopNav();
    freeDest = null;
    if (freeMark && map) { map.removeLayer(freeMark); freeMark = null; }
    if (liveLayer) liveLayer.clearLayers();
    drawUnlocked();
  }
}
function setGoNote(t) { const el = document.getElementById('goNote'); if (el) el.textContent = t; }
async function pickDest(d) {
  freeDest = { label: d.name || 'Dropped pin', lat: +d.lat, lon: +d.lon };
  const sg = document.getElementById('goSugg'); if (sg) sg.innerHTML = '';
  const inp = document.getElementById('goQ'); if (inp) inp.value = freeDest.label;
  if (freeMark) map.removeLayer(freeMark);
  freeMark = L.marker([freeDest.lat, freeDest.lon], { icon: stopIcon('★'), zIndexOffset: 800 }).addTo(map);
  await routeFree(freeDest);
}
async function routeFree(dest, quiet) {
  if (!dest) return;
  if (!meLL) { const l = await locateMe(); if (l) { meLL = l; placeMe(); } }
  const from = meLL || { lat: map.getCenter().lat, lon: map.getCenter().lng };
  setGoNote('Finding a cart-friendly route…');
  let leg = null;
  try {
    await connectStops([]);
    leg = await withRoads(() => roadApi.trip(from, dest, { risky: freeRisky }));
  } catch (e) { leg = null; }
  if (!freeOn) return;
  if (liveLayer) liveLayer.clearLayers();
  if (!leg || !leg.points || leg.points.length < 2) {
    stopNav();
    setGoNote(freeRisky ? 'No way through, even with risky stretches.' : 'No legal route there. Try ⚠️ Risky to see short-stretch options.');
    return;
  }
  addRouteLine(leg.points, liveLayer, leg.dashed);
  const risky = (leg.runs || []).filter(r => r.risky);
  risky.forEach(r => L.polyline(r.points, { renderer: routeR, pane: 'route', color: '#e5484d', weight: 6, dashArray: '8 8', interactive: false }).addTo(liveLayer));
  const mi = (navRouteLen(leg.points) / 1609.34).toFixed(1);
  setGoNote(risky.length ? `${mi} mi · ⚠️ ${risky.length} risky stretch${risky.length > 1 ? 'es' : ''} (red dashes). Use caution.` : `${mi} mi on legal golf cart roads.`);
  if (!quiet) frameLatLngs(leg.points.concat([[from.lat, from.lon]]));
  beginNav(leg, -1, dest);
}
function navRouteLen(pts) { let m = 0; for (let i = 1; i < pts.length; i++) m += GCMNav.hav(pts[i - 1], pts[i]); return m; }
function wireFree() {
  const inp = document.getElementById('goQ'), sg = document.getElementById('goSugg');
  if (!inp) return;
  inp.oninput = () => {
    clearTimeout(freeTimer);
    freeTimer = setTimeout(async () => {
      const q = inp.value;
      const list = await searchPlaces(q);
      if (inp.value !== q) return;
      sg.innerHTML = list.map((x, k) => `<button type="button" class="sugg" data-k="${k}"><b>${esc(x.name)}</b><span>${esc(x.sub || '')}</span></button>`).join('');
      sg.querySelectorAll('.sugg').forEach(b => { b.onclick = () => pickDest(list[+b.dataset.k]); });
    }, 200);
  };
  document.querySelectorAll('#goMode button').forEach(b => {
    b.onclick = () => {
      freeRisky = b.dataset.mode === 'risky';
      document.querySelectorAll('#goMode button').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
      if (freeDest) routeFree(freeDest);
    };
  });
  document.getElementById('goBack').onclick = () => freeMode(false);
  document.querySelectorAll('.go-open').forEach(b => { b.onclick = () => freeMode(true); });
}

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
  stopNav();
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
  if (drawn) { beginNav(leg, ((activeEx && activeEx.stops) || []).indexOf(first)); if (follow) follow.start(); }
  focusEx(true);
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
// Focus: once a renter picks a ride, the other rides fold away until "All experiences".
function focusEx(on) {
  document.body.classList.toggle('focus-ex', !!on && !!activeEx);
  const b = document.getElementById('allEx');
  if (b) b.hidden = !(on && activeEx);
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
      <div id="goPane" hidden>
        <button class="allex" id="goBack" type="button">‹ Back to experiences</button>
        <h2 class="sec">Navigate somewhere else</h2>
        <input id="goQ" class="goq" type="search" placeholder="Search a place or street" autocomplete="off" aria-label="Where to?">
        <div id="goSugg" class="gosugg"></div>
        <p class="fine">Or tap the map to drop a pin.</p>
        <div class="gomode" id="goMode" role="group" aria-label="Route mode"><button type="button" data-mode="legal" aria-pressed="true">✅ Legal only</button><button type="button" data-mode="risky" aria-pressed="false">⚠️ Risky</button></div>
        <p class="legend" id="goNote" aria-live="polite"></p>
      </div>
      <button class="go-open goopen" type="button">🧭 Navigate somewhere else</button>
      <button class="allex" id="allEx" type="button" hidden>‹ All experiences</button>
      <h2 class="sec">Experiences</h2>
      <p class="subsec">Tap one. Its stops light up on the map.</p>
      ${ex.map((e, i) => `<button class="xcard" type="button" data-ex="${esc(e.id)}" aria-pressed="false">
        <span class="xmeta"><span class="num">${String(i + 1).padStart(2, '0')}</span><span class="chip">${(e.stops || []).length} ${(e.stops || []).length === 1 ? 'stop' : 'stops'}</span></span>
        <span class="xtitle">${esc(e.title)}</span>
        ${e.description ? `<span class="xdesc">${esc(e.description)}</span>` : ''}
        <span class="xgo">Show stops</span>
      </button>`).join('') || '<p class="fine">No rides pinned yet. Ask the shop — partner offers may still be on the map.</p>'}
      <div class="offers"><h2 class="sec">Partner offers</h2>
      ${af.map(a => `<button class="ocard" type="button" data-af="${esc(a.id)}">
        <span class="star" aria-hidden="true">★</span>
        <span><span class="xtitle">${esc(a.name)}</span><span class="xdesc">${esc(a.offer || 'Partner offer')}${a.coupon ? ` · coupon <code>${esc(a.coupon)}</code>` : ''}</span></span>
      </button>`).join('') || '<p class="fine">No partner offers yet.</p>'}
      ${(unlocked.places || []).length ? `<h2 class="sec">Places to see</h2>
      ${(unlocked.places || []).map(p => `<button class="ocard pcard" type="button" data-place="${esc(p.id)}">
        <span class="star" aria-hidden="true">${placeUi(p.category)[0]}</span>
        <span><span class="xtitle">${esc(p.name)}</span><span class="xdesc">${esc(placeUi(p.category)[1])}${p.note ? ` · ${esc(p.note)}` : ''}</span></span>
      </button>`).join('')}` : ''}</div>
      <p class="legend">Green roads are legal for a ${esc(vehWord())}. Red roads are off limits. The blue line is your route.</p>
      <p class="legend muted" id="vehLegend">${esc(vehLegend())}</p>
      <p class="legend">Numbered pins are stops. Amber ★ pins are partner offers.${(unlocked.places || []).length ? ' Icon pins (🍽️ 🌅 ❓ 💡 📍) are places to see. Tap one to read about it.' : ''}</p>
      <p class="legend" id="routeNote" aria-live="polite"></p>
    </div>
    ${ex.length ? `<div class="dock-foot"><button class="start" id="startEx" type="button">Start experience</button><p class="fine" id="startNote" aria-live="polite"></p></div>` : ''}`;
  panel.querySelectorAll('.xcard').forEach(el => {
    el.onclick = () => { selectEx(el.dataset.ex); focusEx(true); };
  });
  wireFree();
  const allBtn = document.getElementById('allEx');
  if (allBtn) allBtn.onclick = () => focusEx(false);
  panel.querySelectorAll('.ocard').forEach(el => {
    el.onclick = () => {
      const hit = el.dataset.place ? placeMarks.find(a => a.id === el.dataset.place) : affMarks.find(a => a.id === el.dataset.af);
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
