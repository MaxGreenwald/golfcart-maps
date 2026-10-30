/* Partner admin SPA — super admin + shop admin. Talks to /api/partner/*.
   Place pickers: Photon (Komoot) + Nominatim fallback (same as the main map),
   plus manual pin-drop with a custom label. Lat/lon stored under the hood. */
// A super-admin editing a shop as its owner: every /shop call names that shop.
const scoped = path => (state && state.actingShop && /^\/shop(\/|$|\?)/.test(path))
  ? path + (path.includes('?') ? '&' : '?') + 'shop_id=' + encodeURIComponent(state.actingShop.id)
  : path;
const api = (path, opt = {}) => fetch('/api/partner' + scoped(path), {
  credentials: 'include',
  headers: { 'content-type': 'application/json', ...(opt.headers || {}) },
  ...opt,
}).then(async r => {
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.error || r.statusText), { status: r.status, body: j });
  return j;
});

const $ = (s, el = document) => el.querySelector(s);
const app = $('#app');
let me = null;
let regions = [];
let state = { view: 'home', shopBundle: null, shops: [], msg: '', err: '' };
const placeCache = new Map();
let searchSeq = 0;

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Brand accent when a shop leaves color unset. Matches --aqua / --brand on /p/<slug>. */
const DEFAULT_BRAND = '#14b8c4';

/** #rgb / #rrggbb → lowercase #rrggbb. Empty or anything else → ''. */
function hexColor(raw) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(raw ?? '').trim());
  if (!m) return '';
  let h = m[1].toLowerCase();
  if (h.length === 3) h = h.replace(/./g, c => c + c);
  return '#' + h;
}

function brandColorFields(stored) {
  const raw = String(stored ?? '').trim();
  const hex = hexColor(raw);
  const picker = hex || DEFAULT_BRAND;
  const hidden = hex || raw;
  const readout = hex ? hex : (raw ? raw : 'Default teal');
  const readoutClass = hex || raw ? 'hex-readout' : 'hex-readout is-default';
  return `<div>
      <label for="brandColorPick">Primary color (optional)</label>
      <div class="color-pick">
        <input type="color" id="brandColorPick" value="${esc(picker)}" aria-label="Primary color" aria-describedby="brandColorHint">
        <output class="${readoutClass}" id="brandColorHex" for="brandColorPick">${esc(readout)}</output>
        <button type="button" class="btn alt" id="brandColorClear"${hidden ? '' : ' disabled'}>Use default</button>
      </div>
      <input type="hidden" id="brandColor" value="${esc(hidden)}">
      <p class="muted" id="brandColorHint">Click the swatch to pick a color. Use default for the teal accent on your brand page.</p>
    </div>`;
}

function flash(ok, text) {
  state.msg = ok ? text : '';
  state.err = ok ? '' : text;
  render();
}

async function loadMe() {
  me = await api('/auth/me');
  regions = await fetch('/data/regions.json').then(r => r.json());
}

function regionById(id) {
  return regions.find(r => r.id === id) || regions.find(r => r.id === 'sd') || regions[0];
}

function activeRegion() {
  const sel = $('#brandRegion') || $('#shopRegion');
  const id = (sel && sel.value) || (state.shopBundle && state.shopBundle.shop && state.shopBundle.shop.region_id) || 'sd';
  return regionById(id);
}

function regionOptions(selected) {
  const list = regions.filter(r => !r.hidden).slice();
  list.sort((a, b) => (a.id === 'sd' ? -1 : 0) - (b.id === 'sd' ? -1 : 0) || (a.short || a.name || '').localeCompare(b.short || b.name || ''));
  return list.map(r => `<option value="${esc(r.id)}" ${r.id === selected ? 'selected' : ''}>${esc(r.short || r.name)} (${esc(r.id)})</option>`).join('');
}

/** Photon → Nominatim, biased to the shop city bbox. No API key. */
async function searchPlaces(q) {
  const query = String(q || '').trim();
  if (query.length < 2) return [];
  const reg = activeRegion();
  const key = (reg?.id || '') + '|' + query.toLowerCase();
  if (placeCache.has(key)) return placeCache.get(key);
  const b = reg?.bbox || [32.53, -117.46, 33.3, -116.95];
  const c = reg?.center || [32.85, -117.27];
  // bbox: [south, west, north, east]
  let res = [];
  try {
    const ac = new AbortController();
    const to = setTimeout(() => ac.abort(), 2500);
    const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=7&lat=${c[0]}&lon=${c[1]}&bbox=${b[1]},${b[0]},${b[3]},${b[2]}`;
    const r = await fetch(url, { signal: ac.signal, headers: { Accept: 'application/json' } });
    clearTimeout(to);
    const j = await r.json();
    res = (j.features || []).map(f => {
      const p = f.properties || {};
      const name = p.name || [p.housenumber, p.street].filter(Boolean).join(' ');
      const sub = [p.housenumber && p.name ? p.street : null, p.city || p.district || p.state, p.osm_value].filter(Boolean).join(' · ');
      return { name, sub, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] };
    }).filter(x => x.name);
  } catch (_) {
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=6&bounded=1&viewbox=${b[1]},${b[2]},${b[3]},${b[0]}&q=${encodeURIComponent(query)}`;
      const r = await fetch(url, { headers: { Accept: 'application/json', 'Accept-Language': 'en' } });
      const j = await r.json();
      res = (j || []).map(x => ({
        name: String(x.display_name || '').split(',')[0],
        sub: String(x.display_name || '').split(',').slice(1, 3).join(',').trim(),
        lat: +x.lat,
        lon: +x.lon,
      })).filter(x => x.name && Number.isFinite(x.lat));
    } catch (_) { res = []; }
  }
  placeCache.set(key, res);
  return res;
}

/** Blank inputs are unset. Number("") is 0, and Number.isFinite(0) is true — that parked the pin at 0,0 in the ocean. */
function numCoord(v) {
  const s = String(v ?? '').trim();
  if (!s) return NaN;
  const n = +s;
  return Number.isFinite(n) ? n : NaN;
}

function pickedLine(lat, lon, label) {
  if (Number.isFinite(numCoord(lat)) && Number.isFinite(numCoord(lon))) {
    return `<div class="picked ok" data-k="picked">✓ ${esc(label || 'Pinned')} · ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}</div>`;
  }
  return `<div class="picked miss" data-k="picked">Search a place or drop a pin on the map</div>`;
}

function stopRowHtml(s = {}, i = 0) {
  const has = Number.isFinite(numCoord(s.lat)) && Number.isFinite(numCoord(s.lon));
  return `<div class="stop" data-i="${i}">
    <div>
      <label>Stop name</label>
      <input data-k="name" placeholder="Name renters see" value="${esc(s.label || '')}">
      <div class="mode-row">
        <button type="button" class="btn alt modeSearch on">Search place</button>
        <button type="button" class="btn alt modePin">Drop pin</button>
      </div>
      <div class="place-search">
        <div class="place-wrap">
          <input data-k="q" placeholder="Search place (e.g. seals La Jolla)" value="${esc(has ? (s.label || '') : '')}" autocomplete="off">
          <div class="sugg" data-k="sugg"></div>
        </div>
      </div>
      <div class="place-pin hidden">
        <label>Custom name</label>
        <input data-k="custom" placeholder="Name this spot" value="${esc(s.label || '')}">
        <div class="pinmap" data-k="pinmap"></div>
        <p class="muted">Click the map to place the pin. Drag to adjust.</p>
      </div>
      <input type="hidden" data-k="label" value="${esc(s.label || '')}">
      <input type="hidden" data-k="lat" value="${esc(s.lat ?? '')}">
      <input type="hidden" data-k="lon" value="${esc(s.lon ?? '')}">
      ${pickedLine(s.lat, s.lon, s.label)}
      <label>Note (optional)</label>
      <input data-k="note" placeholder="What to do here" value="${esc(s.note || '')}">
    </div>
    <div class="stop-actions">
      <button type="button" class="btn alt moveUp">Move up</button>
      <button type="button" class="btn alt moveDown">Move down</button>
      <button class="btn alt remStop" type="button" aria-label="Remove stop">✕</button>
    </div>
  </div>`;
}

function stopEditor(stops) {
  const rows = (stops && stops.length ? stops : [{}]).map((s, i) => stopRowHtml(s, i)).join('');
  return `<div class="stops" id="stopList">${rows}</div>
    <p class="muted">Places via Photon / OpenStreetMap. Or drop a pin and type your own name for unofficial spots.</p>
    <p class="muted">Move up and Move down set the order. Save to keep it.</p>
    <p><button class="btn alt" id="addStop" type="button">Add stop</button>
      ${placeOptions() ? `<select id="addPlaceStop" aria-label="Add one of your places as a stop"><option value="">+ Add one of your places…</option>${placeOptions()}</select>` : ''}</p>`;
}

const PLACE_CATS = [['restaurant', 'Restaurant', '🍽️'], ['views', 'Views', '🌅'], ['trivia', 'Trivia', '❓'], ['fun_fact', 'Fun fact', '💡'], ['other', 'Other', '📍']];
const placeCat = c => PLACE_CATS.find(x => x[0] === c) || PLACE_CATS[4];
function shopPlaces() { return (state.shopBundle && state.shopBundle.places) || []; }
function placeOptions() {
  return shopPlaces().map(p => `<option value="${esc(p.id)}">${placeCat(p.category)[2]} ${esc(p.name)}</option>`).join('');
}
function placesCard() {
  const rows = shopPlaces().map(p => `<tr>
    <td><b>${placeCat(p.category)[2]} ${esc(p.name)}</b> <span class="pill">${esc(placeCat(p.category)[1])}</span>
      <div class="muted">${esc(p.note || '')}</div>
      <div class="muted">${(+p.lat).toFixed(5)}, ${(+p.lon).toFixed(5)}${p.link ? ` · <a href="${esc(p.link)}" target="_blank" rel="noopener">link</a>` : ''}</div></td>
    <td><div class="ex-actions">
      <button class="btn alt" data-edit-place="${esc(p.id)}" type="button">Edit</button>
      <button class="btn warn" data-del-place="${esc(p.id)}" type="button">Delete</button>
    </div></td>
  </tr>`).join('') || '<tr><td colspan="2" class="muted">No places yet.</td></tr>';
  return `<div class="card" id="placesCard"><h2>Places of interest</h2>
    <p class="muted">Spots to point out: food, views, trivia, fun facts. No discount code. They show on your renter map, and you can add them to an experience as a stop.</p>
    <p class="muted hidden" id="placeEditing">Editing this place.</p>
    <input type="hidden" id="placeId" value="">
    <label for="placeCat">Category</label>
    <select id="placeCat">${PLACE_CATS.map(c => `<option value="${c[0]}">${c[2]} ${c[1]}</option>`).join('')}</select>
    <div id="placeRow">${stopRowHtml({}, 0)}</div>
    <label for="placeLink">Link (optional)</label><input id="placeLink" placeholder="https://…">
    <p><button class="btn" id="savePlace" type="button">Add place</button>
      <button class="btn alt hidden" id="cancelPlace" type="button">Cancel</button></p>
    <table><thead><tr><th>Place</th><th></th></tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

function loginView() {
  const invite = new URLSearchParams(location.search).get('invite') || '';
  const dev = me && me.dev_auth;
  return `<div id="login" class="card">
    <h2>Sign in</h2>
    <p class="muted">Shop owners use Google (Gmail). Super admin: Max’s allowlisted emails.</p>
    ${me && me.google ? `<p><a class="btn" href="/api/partner/auth/google">Continue with Google</a></p>` : ''}
    ${dev ? `<div>
      <p class="msg">Mock login is on (DEV_AUTH_EMAIL). Google OAuth secrets are not set on this preview.</p>
      <label>Email</label>
      <input id="devEmail" value="${esc(me.dev_auth && !invite ? 'maxgreenwald.assistant@gmail.com' : '')}" placeholder="you@gmail.com">
      ${invite ? `<input type="hidden" id="inviteTok" value="${esc(invite)}"><p class="muted">Invite token present — use the invited email.</p>` : ''}
      <p style="margin-top:12px"><button class="btn" id="devLogin" type="button">Sign in (mock)</button></p>
    </div>` : (!me || !me.google) ? `<p class="msg err">Neither Google OAuth nor DEV_AUTH_EMAIL is available. Set worker secrets — see research/partner_portal_mvp.md.</p>` : ''}
    ${invite ? `<p class="muted">After sign-in you’ll accept invite <code>${esc(invite.slice(0, 8))}…</code></p>` : ''}
  </div>`;
}

function superView() {
  const rows = (state.shops || []).map(s => `<tr>
    <td><b>${esc(s.name)}</b><div class="muted">/${esc(s.slug)} · ${esc(s.region_id)}</div></td>
    <td>${esc(s.owner_email || '—')}</td>
    <td><span class="pill ${s.disabled ? 'off' : ''}">${s.disabled ? 'disabled' : 'active'}</span></td>
    <td>
      <button class="btn" data-open-shop="${esc(s.id)}" data-shop-name="${esc(s.name)}" type="button">Edit shop</button>
      <button class="btn alt" data-invite="${esc(s.id)}" type="button">Invite</button>
      <button class="btn warn" data-toggle="${esc(s.id)}" data-off="${s.disabled ? 0 : 1}" type="button">${s.disabled ? 'Enable' : 'Disable'}</button>
      <a class="btn alt" href="/p/${esc(s.slug)}" target="_blank" rel="noopener">Brand page</a>
    </td>
  </tr>`).join('') || '<tr><td colspan="4" class="muted">No shops yet.</td></tr>';
  return `
  <div class="card"><h2>Super admin</h2>
    <p class="muted">Create a rental shop, invite the owner, they brand the page and add experiences + affiliate offers.</p>
    ${state.msg ? `<div class="msg ok">${esc(state.msg)}</div>` : ''}
    ${state.err ? `<div class="msg err">${esc(state.err)}</div>` : ''}
  </div>
  <div class="card"><h2>New shop</h2>
    <div class="row">
      <div><label>Display name</label><input id="shopName" placeholder="La Jolla Cart Co"></div>
      <div><label>URL slug</label><input id="shopSlug" placeholder="lajollacartco"><div class="muted">Brand page: /p/&lt;slug&gt;</div></div>
    </div>
    <label>City / region</label>
    <select id="shopRegion">${regionOptions('sd')}</select>
    <p style="margin-top:12px"><button class="btn" id="createShop" type="button">Create shop</button></p>
  </div>
  <div class="card"><h2>Shops</h2>
    <table><thead><tr><th>Shop</th><th>Owner</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

function shopView() {
  const b = state.shopBundle;
  if (!b || !b.shop) return `<div class="card"><p class="msg err">No shop linked to this account yet. Accept an invite from Max.</p></div>`;
  const s = b.shop;
  const actingBanner = state.actingShop ? `<div class="card super-banner" id="superBanner" role="status"><b>Editing ${esc(s.name)} as super-admin.</b>
    Changes go live on the shop's page. <button class="btn alt" id="backToShops" type="button">Back to all shops</button></div>` : '';
  const exRows = (b.experiences || []).map(e => `<tr>
    <td><b>${esc(e.title)}</b><div class="muted">${esc(e.description || '')}</div>
      <div class="muted ex-stops">${stopsLine(e.stops)}</div></td>
    <td><div class="ex-actions">
      <button class="btn alt" data-edit-ex="${esc(e.id)}" type="button">Edit</button>
      <button class="btn warn" data-del-ex="${esc(e.id)}" type="button">Delete</button>
    </div></td>
  </tr>`).join('') || '<tr><td colspan="2" class="muted">No experiences yet.</td></tr>';
  const afRows = (b.affiliates || []).map(a => `<tr>
    <td><b>${esc(a.name)}</b><div class="muted">${esc(a.offer || '')}</div>
      <div class="muted">${Number.isFinite(a.lat) ? a.lat.toFixed(5) + ', ' + a.lon.toFixed(5) : ''}${a.coupon ? ` · coupon <code>${esc(a.coupon)}</code>` : ''}</div></td>
    <td><div class="ex-actions">
      <button class="btn alt" data-edit-af="${esc(a.id)}" type="button">Edit</button>
      <button class="btn warn" data-del-af="${esc(a.id)}" type="button">Delete</button>
    </div></td>
  </tr>`).join('') || '<tr><td colspan="2" class="muted">No affiliate offers yet.</td></tr>';
  const codeRows = (b.codes || []).map(c => `<tr>
    <td><code>${esc(c.code)}</code></td>
    <td class="muted">uses ${c.uses}${c.max_uses ? '/' + c.max_uses : ''} · ${c.multi_use ? 'multi' : 'single'}
      <div class="code-exp">${c.expires_at ? (c.expires_at * 1000 < Date.now() ? 'Expired ' : 'Expires ') + esc(new Date(c.expires_at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })) : 'Never expires'}</div></td>
    <td><a href="/p/${esc(s.slug)}/go?code=${esc(c.code)}" target="_blank" rel="noopener">Open renter link</a></td>
  </tr>`).join('') || '<tr><td colspan="3" class="muted">No codes yet.</td></tr>';
  return `${actingBanner}
  <div class="card"><h2>${esc(s.name)}</h2>
    <p>Brand page: <a href="/p/${esc(s.slug)}" target="_blank">/p/${esc(s.slug)}</a>
      · City: <span class="pill">${esc(s.region_id)}</span></p>
    ${state.msg ? `<div class="msg ok">${esc(state.msg)}</div>` : ''}
    ${state.err ? `<div class="msg err">${esc(state.err)}</div>` : ''}
  </div>
  <div class="card"><h2>Brand</h2>
    <label>Display name</label><input id="brandName" value="${esc(s.name)}">
    <label>City / region</label><select id="brandRegion">${regionOptions(s.region_id || 'sd')}</select>
    <label for="brandVehicle">Your rental vehicles</label>
    <select id="brandVehicle" aria-describedby="brandVehicleHint">
      <option value="lsv"${s.vehicle === 'lsv' ? ' selected' : ''}>Street-legal LSV (roads up to 35 mph)</option>
      <option value="golf_cart"${s.vehicle !== 'lsv' ? ' selected' : ''}>Golf cart (roads up to 25 mph)</option>
    </select>
    <p class="muted" id="brandVehicleHint">Sets which roads show green and how routes run on your renter page.</p>
    <label>Short blurb</label><textarea id="brandBlurb">${esc(s.blurb || '')}</textarea>
    <div class="row">
      <div><label>Logo URL (optional)</label><input id="brandLogo" value="${esc(s.logo_url || '')}" placeholder="https://…"></div>
      ${brandColorFields(s.color)}
    </div>
    <p style="margin-top:12px"><button class="btn" id="saveBrand" type="button">Save brand</button></p>
  </div>
  <div class="card"><h2>Experiences</h2>
    <p class="muted">Ordered joyride stops. Search a place or drop a pin and name it yourself. Edit an experience to change a stop or its order.</p>
    <p class="muted hidden" id="exEditing">Editing this experience. Save changes keeps the stops and their order.</p>
    <input type="hidden" id="exId" value="">
    <label>Title</label><input id="exTitle" placeholder="La Jolla seals joyride">
    <label>Description</label><textarea id="exDesc" placeholder="A 45-minute coastal loop"></textarea>
    <label>Stops</label>${stopEditor([{}])}
    <p>
      <button class="btn" id="addEx" type="button">Add experience</button>
      <button class="btn alt hidden" id="cancelEx" type="button">Cancel</button>
    </p>
    <table><thead><tr><th>Experience</th><th></th></tr></thead><tbody>${exRows}</tbody></table>
  </div>
  ${placesCard()}
  <div class="card af-place"><h2>Affiliate offers</h2>
    <p class="muted">Restaurants and deals for your renters. Larger ★ pins on the map.</p>
    <p class="muted hidden" id="afEditing">Editing this offer. Search or drop a pin to move it.</p>
    <input type="hidden" id="afId" value="">
    <label>Offer text</label><input id="afOffer" placeholder="25% off a beer">
    <div class="mode-row" id="afModes">
      <button type="button" class="btn alt modeSearch on" data-af-mode="search">Search place</button>
      <button type="button" class="btn alt modePin" data-af-mode="pin">Drop pin</button>
    </div>
    <div id="afSearch">
      <div class="place-wrap">
        <label>Place</label>
        <input id="afQ" placeholder="Search place (e.g. Sunset Cliffs bar)" autocomplete="off">
        <div class="sugg" id="afSugg"></div>
      </div>
    </div>
    <div id="afPin" class="hidden">
      <label>Custom name</label>
      <input id="afCustom" placeholder="Name this spot">
      <div class="pinmap" id="afPinMap"></div>
      <p class="muted">Click the map to place the pin. Drag to adjust.</p>
    </div>
    <input type="hidden" id="afName" value="">
    <input type="hidden" id="afLat" value="">
    <input type="hidden" id="afLon" value="">
    <div class="picked miss" id="afPicked">Search a place or drop a pin on the map</div>
    <div id="afEditFields" class="hidden">
      <label for="afNameEdit">Place name</label><input id="afNameEdit">
      <label for="afCouponText">Coupon code</label><input id="afCouponText" placeholder="Leave empty for no coupon">
    </div>
    <label style="margin-top:10px" id="afCouponRow"><input type="checkbox" id="afCoupon" checked> Generate coupon code</label>
    <p><button class="btn" id="addAf" type="button">Add affiliate</button>
      <button class="btn alt hidden" id="cancelAf" type="button">Cancel</button></p>
    <table><thead><tr><th>Affiliate</th><th></th></tr></thead><tbody>${afRows}</tbody></table>
  </div>
  <div class="card"><h2>Renter access codes</h2>
    <p class="muted">Give this link after they pay the extra $5–10 in your own checkout. Multi-use.</p>
    <label for="codeDays">Code lasts</label>
    <div class="mode-row" id="codeChips">
      ${[1, 3, 7, 14, 30].map(d => `<button type="button" class="btn alt${d === 30 ? ' on' : ''}" data-days="${d}">${d} day${d > 1 ? 's' : ''}</button>`).join('')}
      <button type="button" class="btn alt" data-days="never">No expiry</button>
    </div>
    <div class="row"><div><input id="codeDays" type="number" min="1" max="30" step="1" value="30" aria-describedby="codeDaysHint">
      <div class="muted" id="codeDaysHint">1 to 30 days, or No expiry.</div></div></div>
    <p><button class="btn" id="genCode" type="button">Generate access code</button></p>
    <table><thead><tr><th>Code</th><th>Usage</th><th>Link</th></tr></thead><tbody>${codeRows}</tbody></table>
  </div>`;
}

function setPicked(root, lat, lon, label) {
  const latEl = root.querySelector ? $('[data-k=lat]', root) : null;
  const lonEl = root.querySelector ? $('[data-k=lon]', root) : null;
  const labEl = root.querySelector ? $('[data-k=label]', root) : null;
  const picked = root.querySelector ? $('[data-k=picked]', root) : null;
  if (latEl) latEl.value = lat;
  if (lonEl) lonEl.value = lon;
  if (labEl) labEl.value = label || '';
  if (picked) {
    picked.className = 'picked ok';
    picked.textContent = `✓ ${label || 'Pinned'} · ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}`;
  }
}

function wireSearchInput(input, sugg, onPick) {
  let tmr = null;
  const hide = () => { sugg.style.display = 'none'; sugg.innerHTML = ''; };
  input.addEventListener('input', () => {
    clearTimeout(tmr);
    const v = input.value.trim();
    if (v.length < 2) { hide(); return; }
    const my = ++searchSeq;
    tmr = setTimeout(async () => {
      const list = await searchPlaces(v);
      if (my !== searchSeq) return;
      sugg.innerHTML = '';
      if (!list.length) {
        sugg.innerHTML = '<div><b>No places found</b><small>Try Drop pin for a custom spot</small></div>';
        sugg.style.display = 'block';
        return;
      }
      list.forEach(x => {
        const d = document.createElement('div');
        d.innerHTML = `<b>${esc(x.name)}</b><small>${esc(x.sub || '')}</small>`;
        d.onmousedown = e => { e.preventDefault(); onPick(x); hide(); };
        sugg.appendChild(d);
      });
      sugg.style.display = 'block';
    }, 280);
  });
  input.addEventListener('blur', () => setTimeout(hide, 180));
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const first = sugg.querySelector('div');
      if (first) first.dispatchEvent(new Event('mousedown'));
    }
  });
}

function regionCenter(reg) {
  const c = reg && reg.center;
  if (Array.isArray(c) && Number.isFinite(+c[0]) && Number.isFinite(+c[1])) return [+c[0], +c[1]];
  return [32.8565, -117.2555];
}

/** Zoom for dropping a stop: close when a point is known, otherwise the city view clamped to 14–16. */
function placeZoom(reg, close) {
  if (close) return 16;
  const z = reg && Number.isFinite(+reg.zoom) ? +reg.zoom : 15;
  return Math.max(14, Math.min(16, z));
}

/** Earlier stop in this experience that already has a pin. Affiliate maps are not inside .stop. */
function priorStopLatLng(el) {
  const row = el && el.closest ? el.closest('.stop') : null;
  if (!row) return null;
  let prev = row.previousElementSibling;
  while (prev) {
    if (prev.classList && prev.classList.contains('stop')) {
      const lat = numCoord($('[data-k=lat]', prev) && $('[data-k=lat]', prev).value);
      const lon = numCoord($('[data-k=lon]', prev) && $('[data-k=lon]', prev).value);
      if (Number.isFinite(lat) && Number.isFinite(lon)) return [lat, lon];
    }
    prev = prev.previousElementSibling;
  }
  return null;
}

/** ~250m north-east, so a suggested view is not stacked on the previous stop. */
const PIN_OFFSET = 0.0022;
/** Lat/lon pad (~2.5 km) around that suggestion. Street zoom on the last pin hid the neighborhood. */
const PIN_AREA_PAD = 0.025;
const PIN_AREA_MAX_ZOOM = 14;

function pinView(el, lat, lon) {
  const reg = activeRegion();
  // This stop already has a pin: show that pin. Do not borrow the previous stop.
  if (Number.isFinite(lat) && Number.isFinite(lon)) return { lat, lon, zoom: 16, placed: true, area: false };
  const prior = priorStopLatLng(el);
  if (prior) {
    return {
      lat: prior[0] + PIN_OFFSET,
      lon: prior[1] + PIN_OFFSET,
      zoom: PIN_AREA_MAX_ZOOM,
      placed: false,
      area: true,
    };
  }
  const c = regionCenter(reg);
  return { lat: c[0], lon: c[1], zoom: placeZoom(reg, false), placed: false, area: false };
}

function pinAreaBounds(lat, lon) {
  return [
    [lat - PIN_AREA_PAD, lon - PIN_AREA_PAD],
    [lat + PIN_AREA_PAD, lon + PIN_AREA_PAD],
  ];
}

/** Frame the map. A stop with no pin gets no marker until click or drag, and is not written into the form. */
function framePinMap(map, view) {
  if (!map) return;
  if (view.placed) map.setView([view.lat, view.lon], view.zoom);
  else if (view.area) map.fitBounds(pinAreaBounds(view.lat, view.lon), { animate: false, maxZoom: PIN_AREA_MAX_ZOOM });
  else map.setView([view.lat, view.lon], view.zoom);
}

function settlePinMap(el, map, view) {
  const generation = (el._gcmFrameGen = (el._gcmFrameGen || 0) + 1);
  const sized = () => el.offsetWidth > 0 && el.offsetHeight > 0;
  if (map.invalidateSize) map.invalidateSize();
  const hadSize = sized();
  framePinMap(map, view);
  const fix = () => {
    if (!map) return;
    if (map.invalidateSize) map.invalidateSize();
    // A click or drag bumps the generation so this does not yank the view back.
    // Refit only when the first frame ran before the panel had a size.
    if (el._gcmFrameGen === generation && !hadSize) framePinMap(map, view);
  };
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(fix);
  setTimeout(fix, 60);
}

function ensurePinMap(el, latRaw, lonRaw, onMove) {
  if (!window.L || !el) return null;
  const lat = numCoord(latRaw);
  const lon = numCoord(lonRaw);
  const view = pinView(el, lat, lon);

  const putMarker = ll => {
    if (!el._gcmMap) return null;
    if (!el._gcmMarker) {
      const marker = L.marker(ll, { draggable: true }).addTo(el._gcmMap);
      marker.on('dragend', () => {
        el._gcmFrameGen = (el._gcmFrameGen || 0) + 1;
        const pos = marker.getLatLng();
        onMove(pos.lat, pos.lng);
      });
      el._gcmMarker = marker;
    } else {
      el._gcmMarker.setLatLng(ll);
    }
    return el._gcmMarker;
  };

  if (!el._gcmMap) {
    const map = L.map(el, { zoomControl: true }).setView([view.lat, view.lon], view.zoom);
    // Same tiles as the main map (public/app.js). Subdomain {s}.tile hosts are not required.
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    }).addTo(map);
    map.on('click', e => {
      el._gcmFrameGen = (el._gcmFrameGen || 0) + 1;
      putMarker(e.latlng);
      onMove(e.latlng.lat, e.latlng.lng);
    });
    el._gcmMap = map;
  }

  // A new stop must not open with a marker (or saved coords) on the previous stop.
  // Click or drag is what writes lat/lon. A stop that already has its own pin shows that pin.
  if (view.placed) putMarker([lat, lon]);
  settlePinMap(el, el._gcmMap, view);
  return el._gcmMap;
}

/** Copy a typed stop name into the hidden label and the search box. Assigning the search value does not fire input, so a rename does not start a place lookup. */
function mirrorStopName(row, text, source) {
  const shown = String(text ?? '');
  const trimmed = shown.trim();
  const label = $('[data-k=label]', row);
  const nameEl = $('[data-k=name]', row);
  const custom = $('[data-k=custom]', row);
  const q = $('[data-k=q]', row);
  if (label) label.value = trimmed;
  if (source !== 'name' && nameEl && document.activeElement !== nameEl) nameEl.value = shown;
  if (source !== 'custom' && custom && document.activeElement !== custom) custom.value = shown;
  // Setting the value does not fire input, so the search box can mirror the name without a lookup.
  if (q && (source === 'pick' || document.activeElement !== q)) q.value = trimmed;
  return trimmed;
}

function refreshMoveButtons() {
  const rows = [...document.querySelectorAll('#stopList .stop')];
  rows.forEach((row, i) => {
    const up = $('.moveUp', row);
    const down = $('.moveDown', row);
    if (up) up.disabled = i === 0;
    if (down) down.disabled = i === rows.length - 1;
    row.dataset.i = String(i);
  });
}

function moveStop(row, dir) {
  const list = row.parentElement;
  if (!list) return;
  if (dir < 0) {
    const prev = row.previousElementSibling;
    if (!prev) return;
    list.insertBefore(row, prev);
  } else {
    const next = row.nextElementSibling;
    if (!next) return;
    list.insertBefore(next, row);
  }
  refreshMoveButtons();
  const mapEl = $('[data-k=pinmap]', row);
  if (mapEl && mapEl._gcmMap && mapEl._gcmMap.invalidateSize) mapEl._gcmMap.invalidateSize();
}

function wireStop(row) {
  const searchBox = $('.place-search', row);
  const pinBox = $('.place-pin', row);
  const btnSearch = $('.modeSearch', row);
  const btnPin = $('.modePin', row);
  const q = $('[data-k=q]', row);
  const sugg = $('[data-k=sugg]', row);
  const custom = $('[data-k=custom]', row);
  const nameEl = $('[data-k=name]', row);
  const pinmap = $('[data-k=pinmap]', row);
  const show = mode => {
    const pin = mode === 'pin';
    searchBox.classList.toggle('hidden', pin);
    pinBox.classList.toggle('hidden', !pin);
    btnSearch.classList.toggle('on', !pin);
    btnPin.classList.toggle('on', pin);
    if (pin) {
      ensurePinMap(pinmap, $('[data-k=lat]', row).value, $('[data-k=lon]', row).value, (lat, lon) => {
        const typed = (custom.value || (nameEl && nameEl.value) || '').trim();
        const name = (typed || $('[data-k=label]', row).value || 'Custom stop').trim();
        setPicked(row, lat, lon, name);
        if (typed) mirrorStopName(row, typed, 'pin');
      });
    }
  };
  btnSearch.onclick = () => show('search');
  btnPin.onclick = () => show('pin');
  wireSearchInput(q, sugg, x => {
    mirrorStopName(row, x.name, 'pick');
    setPicked(row, x.lat, x.lon, x.name);
  });
  if (nameEl) nameEl.addEventListener('input', () => {
    const text = nameEl.value.trim();
    mirrorStopName(row, nameEl.value, 'name');
    const lat = numCoord($('[data-k=lat]', row).value);
    const lon = numCoord($('[data-k=lon]', row).value);
    if (Number.isFinite(lat) && Number.isFinite(lon) && text) setPicked(row, lat, lon, text);
  });
  custom.addEventListener('input', () => {
    const text = custom.value.trim();
    const lat = numCoord($('[data-k=lat]', row).value);
    const lon = numCoord($('[data-k=lon]', row).value);
    if (Number.isFinite(lat) && Number.isFinite(lon)) setPicked(row, lat, lon, text || 'Custom stop');
    mirrorStopName(row, custom.value, 'custom');
  });
  $('.remStop', row).onclick = () => { row.remove(); refreshMoveButtons(); };
  const up = $('.moveUp', row);
  const down = $('.moveDown', row);
  if (up) up.onclick = () => moveStop(row, -1);
  if (down) down.onclick = () => moveStop(row, 1);
  refreshMoveButtons();
}

function wirePlaces() {
  const row = $('#placeRow .stop');
  if (!row) return;
  wireStop(row);
  $('label', row).textContent = 'Place name';
  [...row.querySelectorAll('label')].find(l => /Note/.test(l.textContent)).textContent = 'Note renters read (trivia, fun fact, what to look for)';
  $('[data-k=note]', row).placeholder = 'e.g. This pier was built in 1925';
  const sel = $('#addPlaceStop');
  if (sel) sel.onchange = () => {
    const p = shopPlaces().find(x => x.id === sel.value);
    sel.value = '';
    if (!p) return;
    const list = $('#stopList');
    // Fill an empty first row, else append.
    const blank = [...list.querySelectorAll('.stop')].find(r => !$('[data-k=lat]', r).value);
    const wrap = document.createElement('div');
    wrap.innerHTML = stopRowHtml({ label: p.name, lat: p.lat, lon: p.lon, note: p.note }, list.children.length);
    const nr = wrap.firstElementChild;
    if (blank) list.replaceChild(nr, blank); else list.appendChild(nr);
    wireStop(nr);
    refreshMoveButtons();
  };
  const fill = p => {
    $('#placeId').value = p ? p.id : '';
    $('#placeCat').value = p ? p.category : 'restaurant';
    $('#placeLink').value = p ? (p.link || '') : '';
    const wrap = document.createElement('div');
    wrap.innerHTML = stopRowHtml(p ? { label: p.name, lat: p.lat, lon: p.lon, note: p.note } : {}, 0);
    $('#placeRow').replaceChildren(wrap.firstElementChild);
    $('#placeEditing').classList.toggle('hidden', !p);
    $('#cancelPlace').classList.toggle('hidden', !p);
    $('#savePlace').textContent = p ? 'Save place' : 'Add place';
    wirePlaces();
  };
  document.querySelectorAll('[data-edit-place]').forEach(b => b.onclick = () => {
    fill(shopPlaces().find(x => x.id === b.dataset.editPlace));
    $('#placesCard').scrollIntoView({ block: 'start' });
  });
  $('#cancelPlace').onclick = () => fill(null);
  $('#savePlace').onclick = async () => {
    try {
      const r = $('#placeRow .stop');
      const name = (($('[data-k=name]', r).value || $('[data-k=label]', r).value) || '').trim();
      const lat = numCoord($('[data-k=lat]', r).value), lon = numCoord($('[data-k=lon]', r).value);
      if (!name) throw new Error('Name the place');
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('Pick a place (search or drop a pin)');
      const body = { name, category: $('#placeCat').value, lat, lon, note: $('[data-k=note]', r).value.trim(), link: $('#placeLink').value.trim() };
      const pid = $('#placeId').value;
      if (pid) await api('/shop/places/' + pid, { method: 'PATCH', body: JSON.stringify(body) });
      else await api('/shop/places', { method: 'POST', body: JSON.stringify(body) });
      flash(true, pid ? 'Place saved' : 'Place added');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-del-place]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this place?')) return;
    try { await api('/shop/places/' + b.dataset.delPlace, { method: 'DELETE' }); await refreshShop(); }
    catch (e) { flash(false, e.message); }
  });
}

function wireAffiliatePicker() {
  const searchBox = $('#afSearch');
  const pinBox = $('#afPin');
  if (!searchBox) return;
  const setAf = (lat, lon, name) => {
    $('#afLat').value = lat;
    $('#afLon').value = lon;
    $('#afName').value = name || '';
    if ($('#afId') && $('#afId').value && name) $('#afNameEdit').value = name;
    const p = $('#afPicked');
    p.className = 'picked ok';
    p.textContent = `✓ ${name || 'Pinned'} · ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}`;
  };
  $('#afModes').querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      const pin = b.dataset.afMode === 'pin';
      searchBox.classList.toggle('hidden', pin);
      pinBox.classList.toggle('hidden', !pin);
      $('#afModes').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
      if (pin) {
        ensurePinMap($('#afPinMap'), $('#afLat').value, $('#afLon').value, (lat, lon) => {
          setAf(lat, lon, ($('#afCustom').value || $('#afName').value || 'Custom place').trim());
        });
      }
    };
  });
  wireSearchInput($('#afQ'), $('#afSugg'), x => {
    $('#afQ').value = x.name;
    setAf(x.lat, x.lon, x.name);
  });
  $('#afCustom').addEventListener('input', () => {
    const lat = numCoord($('#afLat').value), lon = numCoord($('#afLon').value);
    if (Number.isFinite(lat) && Number.isFinite(lon)) setAf(lat, lon, $('#afCustom').value.trim() || 'Custom place');
  });
}

function render() {
  const who = $('#who');
  const logout = $('#logoutBtn');
  if (!me || !me.user) {
    who.textContent = '';
    logout.classList.add('hidden');
    app.innerHTML = loginView();
    bindLogin();
    return;
  }
  who.textContent = me.user.email + (me.user.super ? ' · super admin' : ' · shop admin');
  logout.classList.remove('hidden');
  if (me.user.super && state.view !== 'shop') app.innerHTML = superView();
  else app.innerHTML = shopView();
  bindApp();
}

function stopsLine(stops) {
  const parts = (stops || []).map((x, i) => {
    const note = x.note ? ` (${esc(x.note)})` : '';
    return `${i + 1}. ${esc(x.label || 'Stop')}${note}`;
  });
  return parts.join(' · ') || 'No stops';
}

function readStops() {
  return [...document.querySelectorAll('#stopList .stop')].map(row => {
    const named = ($('[data-k=name]', row) && $('[data-k=name]', row).value.trim()) || '';
    const hidden = ($('[data-k=label]', row) && $('[data-k=label]', row).value.trim()) || '';
    return {
      label: named || hidden,
      lat: +$('[data-k=lat]', row).value,
      lon: +$('[data-k=lon]', row).value,
      note: $('[data-k=note]', row).value.trim(),
    };
  }).filter(s => s.label && Number.isFinite(s.lat) && Number.isFinite(s.lon));
}

function setExperienceMode(editing) {
  const btn = $('#addEx');
  const cancel = $('#cancelEx');
  const note = $('#exEditing');
  if (btn) btn.textContent = editing ? 'Save changes' : 'Add experience';
  if (cancel) cancel.classList.toggle('hidden', !editing);
  if (note) note.classList.toggle('hidden', !editing);
}

function fillStopList(stops) {
  const list = $('#stopList');
  if (!list) return;
  const rows = (stops && stops.length ? stops : [{}]);
  list.innerHTML = rows.map((s, i) => stopRowHtml(s, i)).join('');
  list.querySelectorAll('.stop').forEach(wireStop);
  refreshMoveButtons();
}

function loadExperience(ex) {
  const idEl = $('#exId');
  if (!idEl || !ex) return;
  idEl.value = ex.id || '';
  $('#exTitle').value = ex.title || '';
  $('#exDesc').value = ex.description || '';
  fillStopList(ex.stops || []);
  setExperienceMode(true);
  const title = $('#exTitle');
  if (title && title.scrollIntoView) title.scrollIntoView({ block: 'start' });
}

function resetExperienceForm() {
  const idEl = $('#exId');
  if (idEl) idEl.value = '';
  if ($('#exTitle')) $('#exTitle').value = '';
  if ($('#exDesc')) $('#exDesc').value = '';
  fillStopList([{}]);
  setExperienceMode(false);
}

function syncBrandColorReadout() {
  const hidden = $('#brandColor');
  const pick = $('#brandColorPick');
  const readout = $('#brandColorHex');
  const clearBtn = $('#brandColorClear');
  if (!hidden || !readout) return;
  const raw = hidden.value.trim();
  const hex = hexColor(raw);
  if (hex) {
    readout.textContent = hex;
    readout.className = 'hex-readout';
    if (pick) pick.value = hex;
  } else if (!raw) {
    readout.textContent = 'Default teal';
    readout.className = 'hex-readout is-default';
    if (pick) pick.value = DEFAULT_BRAND;
  } else {
    readout.textContent = raw;
    readout.className = 'hex-readout';
    if (pick) pick.value = DEFAULT_BRAND;
  }
  if (clearBtn) clearBtn.disabled = !raw;
}

function wireBrandColor() {
  const pick = $('#brandColorPick');
  const hidden = $('#brandColor');
  const clearBtn = $('#brandColorClear');
  if (!pick || !hidden) return;
  const apply = value => {
    hidden.value = value;
    syncBrandColorReadout();
  };
  pick.addEventListener('input', () => apply(hexColor(pick.value) || pick.value));
  pick.addEventListener('change', () => apply(hexColor(pick.value) || pick.value));
  if (clearBtn) clearBtn.addEventListener('click', () => apply(''));
}

function bindLogin() {
  const btn = $('#devLogin');
  if (!btn) return;
  btn.onclick = async () => {
    try {
      const email = $('#devEmail').value.trim();
      const invite = $('#inviteTok') && $('#inviteTok').value;
      await api('/auth/dev', { method: 'POST', body: JSON.stringify({ email, invite, expect: email }) });
      await boot();
    } catch (e) { flash(false, e.message); }
  };
}

function bindApp() {
  const create = $('#createShop');
  if (create) create.onclick = async () => {
    try {
      const name = $('#shopName').value.trim();
      const slug = $('#shopSlug').value.trim();
      const region_id = $('#shopRegion').value;
      const made = await api('/admin/shops', { method: 'POST', body: JSON.stringify({ name, slug, region_id }) });
      if (made && made.shop) {
        // Straight into the owner editor so the super-admin can set the shop up.
        state.actingShop = { id: made.shop.id, name: made.shop.name };
        state.msg = 'Shop created. Add experiences, brand and codes below.'; state.err = '';
        await refreshShop();
        return;
      }
      flash(true, 'Shop created');
      await refreshSuper();
    } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-open-shop]').forEach(b => b.onclick = async () => {
    state.actingShop = { id: b.dataset.openShop, name: b.dataset.shopName };
    state.msg = ''; state.err = '';
    try { await refreshShop(); } catch (e) { state.actingShop = null; flash(false, e.message); }
  });
  const back = $('#backToShops');
  if (back) back.onclick = async () => {
    state.actingShop = null; state.msg = ''; state.err = '';
    await refreshSuper();
  };
  document.querySelectorAll('[data-invite]').forEach(b => b.onclick = async () => {
    const email = prompt('Owner email (Gmail)');
    if (!email) return;
    try {
      const j = await api('/admin/shops/' + b.dataset.invite + '/invite', { method: 'POST', body: JSON.stringify({ email }) });
      const link = location.origin + j.path;
      flash(true, 'Invite link (copy to owner — email send not wired): ' + link);
      try { await navigator.clipboard.writeText(link); } catch (_) {}
    } catch (e) { flash(false, e.message); }
  });
  document.querySelectorAll('[data-toggle]').forEach(b => b.onclick = async () => {
    try {
      await api('/admin/shops/' + b.dataset.toggle, { method: 'PATCH', body: JSON.stringify({ disabled: b.dataset.off === '1' }) });
      await refreshSuper();
    } catch (e) { flash(false, e.message); }
  });

  wireBrandColor();

  const saveBrand = $('#saveBrand');
  if (saveBrand) saveBrand.onclick = async () => {
    try {
      await api('/shop', { method: 'PATCH', body: JSON.stringify({
        name: $('#brandName').value.trim(),
        region_id: $('#brandRegion').value,
        blurb: $('#brandBlurb').value,
        logo_url: $('#brandLogo').value.trim(),
        color: $('#brandColor').value.trim(),
        vehicle: $('#brandVehicle').value,
      }) });
      flash(true, 'Brand saved');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };

  document.querySelectorAll('#stopList .stop').forEach(wireStop);
  const addStop = $('#addStop');
  if (addStop) addStop.onclick = () => {
    const list = $('#stopList');
    const wrap = document.createElement('div');
    wrap.innerHTML = stopRowHtml({}, list.children.length);
    const row = wrap.firstElementChild;
    list.appendChild(row);
    wireStop(row);
  };

  wireAffiliatePicker();
  wirePlaces();

  const addEx = $('#addEx');
  if (addEx) addEx.onclick = async () => {
    try {
      const stops = readStops();
      if (!stops.length) throw new Error('Add at least one stop (search a place or drop a pin)');
      const body = {
        title: $('#exTitle').value.trim(),
        description: $('#exDesc').value,
        stops,
      };
      const eid = ($('#exId') && $('#exId').value) || '';
      if (eid) {
        await api('/shop/experiences/' + eid, { method: 'PATCH', body: JSON.stringify(body) });
        flash(true, 'Experience saved');
      } else {
        await api('/shop/experiences', { method: 'POST', body: JSON.stringify(body) });
        flash(true, 'Experience added');
      }
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  const cancelEx = $('#cancelEx');
  if (cancelEx) cancelEx.onclick = () => resetExperienceForm();
  document.querySelectorAll('[data-edit-ex]').forEach(b => b.onclick = () => {
    const ex = ((state.shopBundle && state.shopBundle.experiences) || []).find(e => e.id === b.dataset.editEx);
    if (ex) loadExperience(ex);
  });
  document.querySelectorAll('[data-del-ex]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this experience?')) return;
    try { await api('/shop/experiences/' + b.dataset.delEx, { method: 'DELETE' }); await refreshShop(); }
    catch (e) { flash(false, e.message); }
  });
  const addAf = $('#addAf');
  if (addAf) addAf.onclick = async () => {
    try {
      const afId = $('#afId').value;
      const name = (afId ? $('#afNameEdit').value : $('#afName').value).trim();
      const lat = +$('#afLat').value, lon = +$('#afLon').value;
      if (!name || !Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error('Pick a place (search or drop a pin) before adding');
      if (afId) {
        await api('/shop/affiliates/' + afId, { method: 'PATCH', body: JSON.stringify({
          name, offer: $('#afOffer').value.trim(), lat, lon, coupon: $('#afCouponText').value.trim(),
        }) });
        flash(true, 'Affiliate saved');
        await refreshShop();
        return;
      }
      await api('/shop/affiliates', { method: 'POST', body: JSON.stringify({
        name,
        offer: $('#afOffer').value.trim(),
        lat,
        lon,
        generate_coupon: $('#afCoupon').checked,
      }) });
      flash(true, 'Affiliate added');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-edit-af]').forEach(b => b.onclick = () => {
    const a = ((state.shopBundle && state.shopBundle.affiliates) || []).find(x => x.id === b.dataset.editAf);
    if (!a) return;
    $('#afId').value = a.id;
    $('#afOffer').value = a.offer || '';
    $('#afName').value = a.name; $('#afLat').value = a.lat; $('#afLon').value = a.lon;
    $('#afNameEdit').value = a.name;
    $('#afCouponText').value = a.coupon || '';
    const p = $('#afPicked');
    p.className = 'picked ok';
    p.textContent = `✓ ${a.name} · ${(+a.lat).toFixed(5)}, ${(+a.lon).toFixed(5)}`;
    $('#afEditFields').classList.remove('hidden');
    $('#afEditing').classList.remove('hidden');
    $('#afCouponRow').classList.add('hidden');
    $('#cancelAf').classList.remove('hidden');
    $('#addAf').textContent = 'Save offer';
    $('#afOffer').scrollIntoView({ block: 'center' });
  });
  const cancelAf = $('#cancelAf');
  if (cancelAf) cancelAf.onclick = () => render();
  document.querySelectorAll('[data-del-af]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this affiliate?')) return;
    try { await api('/shop/affiliates/' + b.dataset.delAf, { method: 'DELETE' }); await refreshShop(); }
    catch (e) { flash(false, e.message); }
  });
  const chips = document.querySelectorAll('#codeChips [data-days]');
  const daysIn = $('#codeDays');
  chips.forEach(c => c.onclick = () => {
    chips.forEach(x => x.classList.toggle('on', x === c));
    const never = c.dataset.days === 'never';
    daysIn.disabled = never;
    if (!never) daysIn.value = c.dataset.days;
  });
  if (daysIn) daysIn.oninput = () => chips.forEach(x => x.classList.toggle('on', x.dataset.days === daysIn.value));
  const genCode = $('#genCode');
  if (genCode) genCode.onclick = async () => {
    try {
      const never = !!$('#codeChips [data-days=never].on');
      const days = never ? null : Number($('#codeDays').value);
      if (!never && !(Number.isInteger(days) && days >= 1 && days <= 30)) throw new Error('Pick 1 to 30 days, or No expiry');
      const j = await api('/shop/codes', { method: 'POST', body: JSON.stringify({ multi_use: true, expires_days: days }) });
      flash(true, 'Code ' + j.code.code + ' — renter link copied when possible');
      const link = location.origin + '/p/' + state.shopBundle.shop.slug + '/go?code=' + j.code.code;
      try { await navigator.clipboard.writeText(link); } catch (_) {}
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
}

async function refreshSuper() {
  const j = await api('/admin/shops');
  state.shops = j.shops || [];
  state.actingShop = null;
  state.view = 'super';
  render();
}
async function refreshShop() {
  state.shopBundle = await api('/shop');
  state.view = 'shop';
  render();
}

$('#logoutBtn').onclick = async () => {
  await api('/auth/logout', { method: 'POST', body: '{}' });
  me = { user: null, dev_auth: me && me.dev_auth, google: me && me.google };
  state = { view: 'home', shopBundle: null, shops: [], msg: '', err: '' };
  render();
};

async function boot() {
  await loadMe();
  const invite = new URLSearchParams(location.search).get('invite');
  if (me.user && invite) {
    try {
      await api('/invite/accept', { method: 'POST', body: JSON.stringify({ token: invite }) });
      history.replaceState({}, '', '/partner');
      flash(true, 'Invite accepted');
    } catch (e) { state.err = e.message; }
  }
  if (!me.user) { render(); return; }
  if (me.user.super) {
    // Super can also open shop view via ?shop=1 after owning nothing — default list.
    // For click-through of shop tools, mock-login as shop owner.
    await refreshSuper();
  } else {
    try { await refreshShop(); }
    catch (e) { state.err = e.message; state.shopBundle = null; state.view = 'shop'; render(); }
  }
}

boot().catch(e => { app.innerHTML = `<div class="card msg err">${esc(e.message)}</div>`; });
