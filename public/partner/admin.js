/* Partner admin SPA — super admin + shop admin. Talks to /api/partner/*.
   Place pickers: Google Places via the partner Worker proxy (key stays on the server),
   with Photon (Komoot) + Nominatim as fallback, plus manual pin-drop with a custom label.
   Lat/lon stored under the hood. */
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

async function uploadShopPhoto(file, kind) {
  if (!window.GCMPhoto) throw new Error('Photo upload did not load');
  const prepared = await GCMPhoto.prepare(file);
  const j = await api('/shop/media', { method: 'POST', body: JSON.stringify({ kind, data_base64: prepared.data_base64 }) });
  if (!j.url) throw new Error('Upload did not return a photo link');
  return j.url;
}

function flash(ok, text) {
  state.msg = ok ? text : '';
  state.err = ok ? '' : text;
  render();
}

async function loadMe() {
  me = await api('/auth/me');
  regions = await fetch('/data/regions.json', { cache: 'no-store' }).then(r => r.json());
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

function newPlacesSession() {
  try { if (crypto.randomUUID) return crypto.randomUUID(); } catch (_) {}
  return 's' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function placesSessionFor(input) {
  if (input && !input._placesSession) input._placesSession = newPlacesSession();
  return (input && input._placesSession) || newPlacesSession();
}

/** Photon, then Nominatim, biased to the shop city bbox. Used when Google Places is off or errors. */
async function searchOsm(query, reg) {
  const b = (reg && reg.bbox) || [32.53, -117.46, 33.3, -116.95];
  const c = (reg && reg.center) || [32.85, -117.27];
  try {
    const ac = new AbortController();
    const to = setTimeout(() => ac.abort(), 2500);
    const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=7&lat=${c[0]}&lon=${c[1]}&bbox=${b[1]},${b[0]},${b[3]},${b[2]}`;
    const r = await fetch(url, { signal: ac.signal, headers: { Accept: 'application/json' } });
    clearTimeout(to);
    const j = await r.json();
    return (j.features || []).map(f => {
      const p = f.properties || {};
      const name = p.name || [p.housenumber, p.street].filter(Boolean).join(' ');
      const sub = [p.housenumber && p.name ? p.street : null, p.city || p.district || p.state, p.osm_value].filter(Boolean).join(' · ');
      return { name, sub, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] };
    }).filter(x => x.name && Number.isFinite(x.lat));
  } catch (_) {
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=6&bounded=1&viewbox=${b[1]},${b[2]},${b[3]},${b[0]}&q=${encodeURIComponent(query)}`;
      const r = await fetch(url, { headers: { Accept: 'application/json', 'Accept-Language': 'en' } });
      const j = await r.json();
      return (j || []).map(x => ({
        name: String(x.display_name || '').split(',')[0],
        sub: String(x.display_name || '').split(',').slice(1, 3).join(',').trim(),
        lat: +x.lat,
        lon: +x.lon,
      })).filter(x => x.name && Number.isFinite(x.lat));
    } catch (_) { return []; }
  }
}

/** Google Places via /api/partner/places/*, then Photon / Nominatim. Biased to the shop city bbox. */
async function searchPlaces(q, sessionToken) {
  const query = String(q || '').trim();
  if (query.length < 2) return [];
  const reg = activeRegion();
  const key = (reg?.id || '') + '|' + query.toLowerCase();
  if (placeCache.has(key)) return placeCache.get(key);
  const b = reg?.bbox || [32.53, -117.46, 33.3, -116.95];
  try {
    const ac = new AbortController();
    const to = setTimeout(() => ac.abort(), 2500);
    const r = await fetch('/api/partner' + scoped('/places/autocomplete'), {
      method: 'POST',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ q: query, sessionToken, bbox: b, region_id: reg && reg.id }),
      signal: ac.signal,
    });
    clearTimeout(to);
    const j = await r.json().catch(() => ({}));
    if (r.ok && Array.isArray(j.suggestions) && j.suggestions.length) {
      const list = j.suggestions.map(x => ({
        name: x.name,
        sub: x.sub || '',
        place_id: x.place_id || '',
        lat: Number.isFinite(+x.lat) ? +x.lat : undefined,
        lon: Number.isFinite(+x.lon) ? +x.lon : undefined,
      })).filter(x => x.name && (x.place_id || (Number.isFinite(x.lat) && Number.isFinite(x.lon))));
      if (list.length) {
        placeCache.set(key, list);
        return list;
      }
    }
    if (r.ok && j && j.fallback === false && Array.isArray(j.suggestions)) {
      placeCache.set(key, []);
      return [];
    }
  } catch (_) { /* Google missing, rate limited, or down: use OpenStreetMap. */ }

  const res = await searchOsm(query, reg);
  placeCache.set(key, res);
  return res;
}

/** After a Google suggestion is picked, load lat/lon. Photon hits already have coordinates. */
async function resolvePickedPlace(x, input) {
  if (x && Number.isFinite(+x.lat) && Number.isFinite(+x.lon) && x.name) {
    return { name: x.name, sub: x.sub || '', lat: +x.lat, lon: +x.lon };
  }
  if (x && x.place_id) {
    try {
      const r = await fetch('/api/partner' + scoped('/places/details'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ placeId: x.place_id, sessionToken: input && input._placesSession }),
      });
      if (input) input._placesSession = newPlacesSession();
      const j = await r.json().catch(() => ({}));
      if (r.ok && Number.isFinite(+j.lat) && Number.isFinite(+j.lon)) {
        return { name: j.name || x.name, sub: j.address || x.sub || '', lat: +j.lat, lon: +j.lon };
      }
    } catch (_) { /* fall through */ }
    const osm = await searchOsm(x.name || '', activeRegion());
    if (osm[0]) return osm[0];
  }
  return null;
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

function parkFields(s) {
  const plat = Number.isFinite(+s.park_lat) ? s.park_lat : '';
  const plon = Number.isFinite(+s.park_lon) ? s.park_lon : '';
  const placed = plat !== '' && plon !== '';
  return `<label>Cart parking (optional)</label>
    <div class="mode-row">
      <button type="button" class="btn alt parkDrop">Drop parking pin</button>
      <button type="button" class="btn alt parkClear">Clear parking</button>
    </div>
    <div class="hidden" data-k="parkbox">
      <div data-k="parkmap"></div>
      <p class="muted">Navigation ends here instead of the address. Farther than about half a mile is ignored.</p>
    </div>
    <input type="hidden" data-k="park_lat" value="${esc(plat)}">
    <input type="hidden" data-k="park_lon" value="${esc(plon)}">
    <div class="picked${placed ? ' ok' : ''}" data-k="parkpicked">${placed ? `Park here ${(+plat).toFixed(5)}, ${(+plon).toFixed(5)}` : 'No parking pin. Navigation ends at the address.'}</div>`;
}

function stopRowHtml(s = {}, i = 0, opts = {}) {
  const withPhoto = !!(opts && opts.photo);
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
      ${opts.parking ? parkFields(s) : ''}
      ${withPhoto ? `<label>Photo (optional)</label>
      <input type="file" data-k="photoFile" accept="image/jpeg,image/png,image/webp">
      <input type="hidden" data-k="photo" value="${esc(s.photo || '')}">
      <img data-k="photoPreview" alt="" ${/^https?:\/\//i.test(s.photo || '') ? `src="${esc(s.photo)}"` : 'hidden'}>
      <p class="muted" data-k="photoNote">JPEG, PNG, or WebP, up to 1.5 MB. Saved when you save the experience.</p>` : ''}
    </div>
    <div class="stop-actions">
      <button type="button" class="btn alt moveUp">Move up</button>
      <button type="button" class="btn alt moveDown">Move down</button>
      <button class="btn alt remStop" type="button" aria-label="Remove stop">✕</button>
    </div>
  </div>`;
}

function stopEditor(stops) {
  const rows = (stops && stops.length ? stops : [{}]).map((s, i) => stopRowHtml(s, i, { parking: true, photo: true })).join('');
  return `<div class="stops" id="stopList">${rows}</div>
    <p class="muted">Search uses Google Places when it is set up, or OpenStreetMap. Or drop a pin and type your own name for unofficial spots.</p>
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

function dashCard() {
  return `<div class="card" id="shopDash">
    <h2>Shop activity</h2>
    <p class="muted" id="dashHint">How renters use your map, week by week: opens, routes started, and which rides and stops they look at. Golf Cart Maps' own phones do not count. Test installs are left out.</p>
    <div class="mode-row" id="dashRange">
      <button type="button" class="btn alt" data-dash-days="7">7 days</button>
      <button type="button" class="btn alt on" data-dash-days="30">30 days</button>
      <button type="button" class="btn alt" data-dash-days="84">12 weeks</button>
    </div>
    <div id="dashBody"><p class="muted">Loading activity…</p></div>
  </div>`;
}

function dashNum(v) { const n = Number(v); return Number.isFinite(n) ? n : 0; }

function dashHtml(j, bundle) {
  if (!j || j.ready !== true) {
    const why = j && j.reason === 'not_configured'
      ? 'Activity shows here after the analytics connection is set.'
      : 'Activity could not be loaded. Try again in a moment.';
    return `<p class="muted" id="dashEmpty">${esc(why)}</p>`;
  }
  const codes = (bundle && bundle.codes) || [];
  const ex = (bundle && bundle.experiences) || [];
  const af = (bundle && bundle.affiliates) || [];
  const codeName = c => {
    const hit = codes.find(x => String(x.code || '').toLowerCase() === String(c || '').toLowerCase());
    if (hit) return hit.code;
    return c ? String(c).toUpperCase() : 'Unknown code';
  };
  const rideName = id => {
    const hit = ex.find(x => String(x.id).toLowerCase() === String(id || '').toLowerCase());
    return hit ? hit.title : (id || 'Unknown ride');
  };
  const t = j.totals || {};
  const codeRows = (j.codes || []).map(c => `<tr><td><code>${esc(codeName(c.code))}</code></td><td>${dashNum(c.unlocks)}</td></tr>`).join('')
    || '<tr><td colspan="2" class="muted">No unlocks in this window.</td></tr>';
  const dayRows = (j.daily || []).map(d => `<tr><td>${esc(d.day)}</td><td>${dashNum(d.unlocks)}</td><td>${dashNum(d.started)}</td><td>${dashNum(d.finished)}</td><td>${dashNum(d.affiliate_taps)}</td></tr>`).join('')
    || '<tr><td colspan="5" class="muted">No activity in this window.</td></tr>';
  const rideRows = (j.rides || []).map(r => `<tr><td>${esc(rideName(r.ride))}</td><td>${dashNum(r.opened)}</td><td>${dashNum(r.started)}</td><td>${dashNum(r.finished)}</td></tr>`).join('')
    || '<tr><td colspan="4" class="muted">No rides in this window.</td></tr>';
  const pl = (bundle && bundle.places) || [];
  const partnerName = id => {
    const k = String(id || '').toLowerCase();
    const a = af.find(x => String(x.id).toLowerCase() === k);
    if (a) return { name: a.name, kind: 'Offer' + (a.coupon ? ' (coupon ' + a.coupon + ')' : '') };
    const p = pl.find(x => String(x.id).toLowerCase() === k);
    if (p) return { name: p.name, kind: 'Place to see' };
    return { name: id || 'Removed stop', kind: '' };
  };
  // Older stats Workers only send pins (offer taps); show those with no navigation count.
  const partnerList = j.partner_stops || (j.pins || []).map(p => ({ pin: p.pin, opens: p.taps, navs: null }));
  const pinRows = partnerList.map(p => {
    const n = partnerName(p.pin);
    return `<tr><td>${esc(n.name)}${n.kind ? `<div class="muted">${esc(n.kind)}</div>` : ''}</td><td>${dashNum(p.opens)}</td><td>${p.navs == null ? '' : dashNum(p.navs)}</td></tr>`;
  }).join('') || '<tr><td colspan="3" class="muted">No partner stop opens in this window.</td></tr>';
  const weekLabel = w => {
    const d = new Date(String(w) + 'T12:00:00Z');
    return Number.isNaN(d.getTime()) ? String(w || '') : 'Week of ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  };
  const weekRows = (j.weekly || []).map(w => `<tr><td>${esc(weekLabel(w.week))}</td><td>${dashNum(w.opens)}</td><td>${dashNum(w.routes)}</td><td>${dashNum(w.experience_opens)}</td><td>${dashNum(w.stop_opens)}</td></tr>`).join('')
    || '<tr><td colspan="5" class="muted">No renter activity in this window.</td></tr>';
  const stopName = (ride, pin) => {
    const hit = ex.find(x => String(x.id).toLowerCase() === String(ride || '').toLowerCase());
    const n = Number(pin);
    const st = hit && Number.isInteger(n) && hit.stops && hit.stops[n - 1];
    return (hit ? hit.title : 'Ride') + ': stop ' + (Number.isInteger(n) ? n : '?') + (st && st.label ? ' (' + st.label + ')' : '');
  };
  const stopRows = (j.stops || []).map(x => `<tr><td>${esc(stopName(x.ride, x.pin))}</td><td>${dashNum(x.opens)}</td></tr>`).join('')
    || '<tr><td colspan="2" class="muted">No stop opens in this window.</td></tr>';
  return `<div class="stats" id="dashTotals">
      <div class="stat"><b>${dashNum(t.opens)}</b><span>Renter opens</span></div>
      <div class="stat"><b>${dashNum(t.routes)}</b><span>Routes started</span></div>
      <div class="stat"><b>${dashNum(t.experience_opens)}</b><span>Ride opens</span></div>
      <div class="stat"><b>${dashNum(t.stop_opens)}</b><span>Stop opens</span></div>
    </div>
    <div class="stats" id="dashTotals2">
      <div class="stat"><b>${dashNum(t.unlocks)}</b><span>Unlocks</span></div>
      <div class="stat"><b>${dashNum(t.started)}</b><span>Rides started</span></div>
      <div class="stat"><b>${dashNum(t.finished)}</b><span>Rides finished</span></div>
      <div class="stat"><b>${dashNum(t.affiliate_taps)}</b><span>Offer taps</span></div>
      <div class="stat"><b>${dashNum(t.partner_navs)}</b><span>Partner navigations</span></div>
    </div>
    <h3 class="dash-h">By week</h3>
    <table id="dashWeeks"><thead><tr><th>Week</th><th>Renter opens</th><th>Routes started</th><th>Ride opens</th><th>Stop opens</th></tr></thead><tbody>${weekRows}</tbody></table>
    <h3 class="dash-h">Unlocks by code</h3>
    <table id="dashCodes"><thead><tr><th>Code</th><th>Unlocks</th></tr></thead><tbody>${codeRows}</tbody></table>
    <h3 class="dash-h">By day</h3>
    <table id="dashDays"><thead><tr><th>Day</th><th>Unlocks</th><th>Started</th><th>Finished</th><th>Offer taps</th></tr></thead><tbody>${dayRows}</tbody></table>
    <h3 class="dash-h">Rides</h3>
    <table id="dashRides"><thead><tr><th>Ride</th><th>Opened</th><th>Started</th><th>Finished</th></tr></thead><tbody>${rideRows}</tbody></table>
    <h3 class="dash-h">Stops</h3>
    <table id="dashStops"><thead><tr><th>Stop</th><th>Opens</th></tr></thead><tbody>${stopRows}</tbody></table>
    <h3 class="dash-h">Partner stops</h3>
    <p class="muted">Opens: a renter tapped the offer or place. Take me there: a renter asked for a route to it. Share these with your partners.</p>
    <table id="dashPins"><thead><tr><th>Partner stop</th><th>Opens</th><th>Take me there</th></tr></thead><tbody>${pinRows}</tbody></table>`;
}

let dashDays = 30, dashToken = 0;
async function loadDash() {
  const body = $('#dashBody');
  if (!body) return;
  const token = ++dashToken;
  body.innerHTML = '<p class="muted">Loading activity…</p>';
  try {
    const j = await api('/shop/stats?days=' + dashDays);
    if (token !== dashToken) return;
    const host = $('#dashBody');
    if (host) host.innerHTML = dashHtml(j, state.shopBundle || {});
  } catch (e) {
    if (token !== dashToken) return;
    const host = $('#dashBody');
    if (host) host.innerHTML = `<p class="muted" id="dashEmpty">${esc(e.message || 'Activity could not be loaded.')}</p>`;
  }
}
function wireDash() {
  const box = $('#shopDash');
  if (!box) return;
  box.querySelectorAll('[data-dash-days]').forEach(b => {
    b.classList.toggle('on', Number(b.dataset.dashDays) === dashDays);
    b.onclick = () => {
      dashDays = Number(b.dataset.dashDays) || 30;
      box.querySelectorAll('[data-dash-days]').forEach(x => x.classList.toggle('on', x === b));
      loadDash();
    };
  });
  loadDash();
}

function copyCard() {
  const locs = state.locations || [];
  const here = state.shopBundle && state.shopBundle.shop;
  if (!here) return '';
  if (!locs.length) {
    return `<div class="card" id="copyCard"><h2>Other locations</h2>
      <p class="muted">This account has one location. A second shop on the same owner can receive a copy of a ride or this whole page.</p></div>`;
  }
  const opts = locs.map(s => `<option value="${esc(s.id)}">${esc(s.name)} (${esc(s.region_id)})</option>`).join('');
  const switcher = `<label for="locPick">Location</label>
    <select id="locPick">${[`<option value="${esc(here.id)}" selected>${esc(here.name)} (${esc(here.region_id)})</option>`, opts].join('')}</select>`;
  return `<div class="card" id="copyCard"><h2>Other locations</h2>
    <p class="muted">Copy this page, or one ride, to another shop you own. Pins come along when the town matches. A different town gets the ride names, and you drop new pins.</p>
    ${switcher}
    <label for="pageDest">Copy this page to</label>
    <select id="pageDest">${opts}</select>
    <label class="ns-row"><input type="checkbox" id="pageSync" checked> Update other locations when you edit</label>
    <p><button class="btn" id="copyPage" type="button">Copy page</button></p>
    <div id="copyExBox" class="hidden">
      <p class="muted" id="copyExLabel"></p>
      <label for="exDest">Copy this ride to</label>
      <select id="exDest">${opts}</select>
      <label class="ns-row"><input type="checkbox" id="exSync" checked> Update other locations when you edit this ride</label>
      <p><button class="btn" id="copyExGo" type="button">Copy ride</button></p>
    </div>
  </div>`;
}

function starterBlock() {
  return `<div id="starterCard">
    <p class="muted" id="starterHint">Loading ready-made rides…</p>
    <div id="starterList"></div>
  </div>`;
}

let starterToken = 0;
async function loadStarters() {
  const hint = $('#starterHint');
  const list = $('#starterList');
  if (!hint || !list) return;
  const token = ++starterToken;
  const region = activeRegion();
  const veh = ($('#brandVehicle') && $('#brandVehicle').value) || 'golf_cart';
  const who = veh === 'lsv' ? 'a street-legal LSV' : 'a golf cart';
  const town = (region && (region.short || region.name)) || 'this town';
  hint.textContent = 'Loading ready-made rides…';
  list.innerHTML = '';
  let data = null;
  try {
    const r = await fetch('/data/' + encodeURIComponent(region.id) + '/starters.json', { cache: 'no-store' });
    if (r.ok) data = await r.json();
  } catch (e) { data = null; }
  if (token !== starterToken) return;
  const rides = (data && data.vehicles && data.vehicles[veh]) || [];
  if (!rides.length) {
    hint.textContent = 'No ready-made rides for ' + who + ' in ' + town + '. Add your own stops below.';
    return;
  }
  hint.textContent = rides.length + ' ready-made ride' + (rides.length === 1 ? '' : 's') + ' for ' + who + ' in ' + town + '. Add one, then edit the stops.';
  list.innerHTML = rides.map((ride, i) => `<div class="starter-ride">
      <b>${esc(ride.title)}</b>
      <div class="muted">${esc((ride.stops || []).map(s => s.label).filter(Boolean).join(' · '))}${Number.isFinite(+ride.miles) ? ' · about ' + esc(ride.miles) + ' mi' : ''}</div>
      <p style="margin:8px 0 0"><button type="button" class="btn alt" data-starter="${i}">Add this ride</button></p>
    </div>`).join('');
  list.querySelectorAll('[data-starter]').forEach(btn => {
    btn.onclick = () => addStarter(rides[+btn.dataset.starter], btn);
  });
}

async function addStarter(ride, btn) {
  if (!ride || !ride.title || !(ride.stops || []).length) return;
  if (btn) btn.disabled = true;
  try {
    const made = await api('/shop/experiences', { method: 'POST', body: JSON.stringify({
      title: ride.title,
      description: ride.description || '',
      stops: ride.stops,
      nearest_start: true,
    }) });
    state.msg = ride.title + ' added. Edit the stops, then save.';
    state.err = '';
    const id = made.experience && made.experience.id;
    await refreshShop();
    const ex = ((state.shopBundle && state.shopBundle.experiences) || []).find(e => e.id === id);
    if (ex) loadExperience(ex);
  } catch (e) {
    if (btn) btn.disabled = false;
    flash(false, e.message);
  }
}

function shopView() {
  const b = state.shopBundle;
  if (!b || !b.shop) return `<div class="card"><p class="msg err">No shop linked to this account yet. Accept an invite from Max.</p></div>`;
  const s = b.shop;
  const actingBanner = state.actingShop ? `<div class="card super-banner" id="superBanner" role="status"><b>Editing ${esc(s.name)} as super-admin.</b>
    Changes go live on the shop's page. <button class="btn alt" id="backToShops" type="button">Back to all shops</button></div>` : '';
  const exRows = (b.experiences || []).map(e => `<tr>
    <td><b>${esc(e.title)}</b><div class="muted">${esc(e.description || '')}</div>
      <div class="muted ex-stops">${stopsLine(e.stops)}</div>
      <div class="muted ex-order">${e.nearest_start === false ? 'Riders follow your exact order' : 'Riders start at their nearest stop'}</div>
      ${e.template_id ? '<div class="muted">Linked to your other locations</div>' : ''}</td>
    <td><div class="ex-actions">
      <button class="btn alt" data-edit-ex="${esc(e.id)}" type="button">Edit</button>
      <button class="btn alt" data-copy-ex="${esc(e.id)}" type="button">Copy</button>
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
    <td><code>${esc(c.code)}</code>${c.cart_label ? `<div class="muted code-cart">Cart ${esc(c.cart_label)}</div>` : ''}</td>
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
  ${dashCard()}
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
    <label for="brandPhone">Shop phone for renter help</label>
    <input id="brandPhone" inputmode="tel" placeholder="858-555-0100" value="${esc(s.phone || '')}">
    <p class="muted">Renters who unlocked your page can call or text this number. A text includes their location. Nothing is stored here.</p>
    <div class="row">
      <div><label>Logo URL (optional)</label><input id="brandLogo" value="${esc(s.logo_url || '')}" placeholder="https://…">
        <label for="brandLogoFile">Or upload a logo</label>
        <input type="file" id="brandLogoFile" accept="image/jpeg,image/png,image/webp">
        <p class="muted" id="logoFileNote">JPEG, PNG, or WebP, up to 1.5 MB. Then click Save brand.</p>
        <img id="logoPreview" alt="" ${/^https?:\/\//i.test(s.logo_url || '') ? `src="${esc(s.logo_url)}"` : 'hidden'}>
      </div>
      ${brandColorFields(s.color)}
    </div>
    ${s.page_template_id ? '<label class="ns-row"><input type="checkbox" id="brandPush" checked> Update the brand at your other locations</label>' : ''}
    <p style="margin-top:12px"><button class="btn" id="saveBrand" type="button">Save brand</button></p>
  </div>
  <div class="card" id="rentalForm"><h2>Rental info</h2>
    <p class="muted">Renters see this after they unlock. Leave a line blank to hide it.</p>
    <label for="rentalPickup">Pickup spot</label><input id="rentalPickup" maxlength="200" value="${esc((s.rental && s.rental.pickup) || '')}" placeholder="Meet at the blue umbrellas">
    <label for="rentalReturn">Return spot</label><input id="rentalReturn" maxlength="200" value="${esc((s.rental && s.rental.return_spot) || '')}" placeholder="Same spot, or the side lot">
    <div class="row">
      <div><label for="rentalBy">Return by</label><input id="rentalBy" maxlength="80" value="${esc((s.rental && s.rental.return_by) || '')}" placeholder="5:00 pm"></div>
      <div><label for="rentalPhone">Shop phone</label><input id="rentalPhone" maxlength="40" inputmode="tel" value="${esc((s.rental && s.rental.phone) || '')}" placeholder="Shop number renters can call"></div>
    </div>
    <label for="rentalRules">Cart rules</label><textarea id="rentalRules" maxlength="800" placeholder="Age to drive, seat belts, kids, where to charge">${esc((s.rental && s.rental.rules) || '')}</textarea>
    <label for="rentalDies">If the cart dies</label><textarea id="rentalDies" maxlength="800" placeholder="Call the shop. Stay with the cart.">${esc((s.rental && s.rental.if_cart_dies) || '')}</textarea>
    <p style="margin-top:12px"><button class="btn" id="saveRental" type="button">Save rental info</button></p>
  </div>
  ${window.GCMBookings ? GCMBookings.card() : ''}
  ${rentalCard(s)}
  ${window.GCMReports ? GCMReports.card() : ''}
  <div class="card"><h2>Experiences</h2>
    <p class="muted">Ordered joyride stops. Search a place or drop a pin and name it yourself. Edit an experience to change a stop or its order.</p>
    ${starterBlock()}
    <p class="muted hidden" id="exEditing">Editing this experience. Save changes keeps the stops and their order.</p>
    <input type="hidden" id="exId" value="">
    <label>Title</label><input id="exTitle" placeholder="La Jolla seals joyride">
    <label>Description</label><textarea id="exDesc" placeholder="A 45-minute coastal loop"></textarea>
    <label>Stops</label>${stopEditor([{}])}
    <div id="routeCheck" class="route-check" aria-live="polite"></div>
    <label class="ns-row" style="margin-top:10px"><input type="checkbox" id="exNearest" checked> Start riders at their nearest stop</label>
    <div class="muted" id="exNearestHelp">Off: riders follow your exact order</div>
    <label class="ns-row hidden" id="exPushRow"><input type="checkbox" id="exPush" checked> Update copies at your other locations</label>
    <p>
      <button class="btn" id="addEx" type="button">Add experience</button>
      <button class="btn alt hidden" id="cancelEx" type="button">Cancel</button>
    </p>
    <table><thead><tr><th>Experience</th><th></th></tr></thead><tbody>${exRows}</tbody></table>
  </div>
  ${copyCard()}
  ${window.GCMSalesAdmin ? GCMSalesAdmin.card() : ''}
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
  ${window.GCMQuizAdmin ? GCMQuizAdmin.card(s) : ''}
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
    ${qrKitBlock(s, b.codes)}
    ${fleetBlock(b.codes)}
  </div>`;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error('QR kit did not load'));
    document.body.appendChild(s);
  });
}
let qrKitLoad = null;
function loadQrKit() {
  if (window.GCMQrKit) return Promise.resolve();
  if (!qrKitLoad) qrKitLoad = loadScript('/qrkit.js');
  return qrKitLoad;
}

function qrKitBlock(shop, codes) {
  // Desk codes first; cart codes (fleet stickers) after, labeled with the cart.
  const list = [...(codes || [])].sort((a, b) => (a.cart_label ? 1 : 0) - (b.cart_label ? 1 : 0));
  const opts = list.map(c => `<option value="${esc(c.code)}">${esc(c.code)}${c.cart_label ? ' (cart ' + esc(c.cart_label) + ')' : ''}</option>`).join('');
  const disabled = list.length ? '' : ' disabled';
  return `<div id="qrKit">
    <h3>QR sticker and counter card</h3>
    <p class="muted">One print page: a cart sticker and a counter card with your logo and color. The QR opens /p/${esc(shop.slug)} with the code filled in. Save a PDF from the print dialog.</p>
    <label for="qrCode">Access code on the QR</label>
    <select id="qrCode"${disabled}>${opts || '<option value="">Generate an access code first</option>'}</select>
    <p><button class="btn" id="printQr" type="button"${disabled}>Print QR kit</button></p>
  </div>`;
}

// Fleet stickers: the newest live code for each cart number, in cart order.
function fleetCodes(codes) {
  const nowSec = Date.now() / 1000;
  const seen = new Set();
  const out = [];
  for (const c of codes || []) {
    const cart = String(c.cart_label || '').trim();
    if (!cart || seen.has(cart.toLowerCase())) continue;
    if (c.expires_at && c.expires_at < nowSec) continue;
    seen.add(cart.toLowerCase());
    out.push({ cart, code: c.code });
  }
  return out.sort((a, b) => a.cart.localeCompare(b.cart, 'en', { numeric: true, sensitivity: 'base' }));
}

function fleetBlock(codes) {
  const fleet = fleetCodes(codes);
  const n = fleet.length;
  return `<div id="fleetKit">
    <h3>Fleet stickers</h3>
    <p class="muted">One code per cart, printed on a sticker for that cart. Scanning it opens your page with the code filled in, so renters skip typing. Six stickers per letter page. Save as PDF, or save each page as a PNG.</p>
    <label for="fleetCarts">Cart numbers</label>
    <input id="fleetCarts" placeholder="1-12, or A1, A2, B7" autocomplete="off" aria-describedby="fleetHint">
    <div class="muted" id="fleetHint">Ranges and lists both work. A cart that already has a code keeps it.</div>
    <label class="ns-row"><input type="checkbox" id="fleetExpire"> Cart codes stop working after 30 days</label>
    <p><button class="btn" id="makeFleet" type="button">Make cart codes and print</button>
      <button class="btn alt" id="printFleet" type="button"${n ? '' : ' disabled'}>Print all cart stickers</button></p>
    <p class="muted" id="fleetNote" aria-live="polite">${n ? `${n} cart${n === 1 ? ' has a code' : 's have codes'}: ${esc(fleet.slice(0, 12).map(f => f.cart).join(', '))}${n > 12 ? ', and more' : ''}.` : 'No cart codes yet.'}</p>
  </div>`;
}

async function openFleetSheet(w, fleet) {
  await loadQrKit();
  if (!window.GCMQrKit) throw new Error('QR kit did not load');
  const s = state.shopBundle.shop;
  const html = GCMQrKit.fleetHtml({ name: s.name, slug: s.slug, color: s.color, logoUrl: s.logo_url, origin: location.origin, fleet });
  w.document.open();
  w.document.write(html);
  w.document.close();
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
    placesSessionFor(input);
    const my = ++searchSeq;
    tmr = setTimeout(async () => {
      const list = await searchPlaces(v, input._placesSession);
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
        d.onmousedown = e => {
          e.preventDefault();
          hide();
          Promise.resolve(onPick(x, input)).catch(() => {});
        };
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
  wireSearchInput(q, sugg, async (x, input) => {
    const place = await resolvePickedPlace(x, input);
    if (!place) return;
    mirrorStopName(row, place.name, 'pick');
    setPicked(row, place.lat, place.lon, place.name);
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
  const parkDrop = $('.parkDrop', row);
  const parkClear = $('.parkClear', row);
  const parkBox = $('[data-k=parkbox]', row);
  const paintPark = () => {
    const el = $('[data-k=parkpicked]', row);
    if (!el) return;
    const plat = numCoord($('[data-k=park_lat]', row).value);
    const plon = numCoord($('[data-k=park_lon]', row).value);
    if (Number.isFinite(plat) && Number.isFinite(plon)) {
      el.className = 'picked ok';
      el.textContent = `Park here ${plat.toFixed(5)}, ${plon.toFixed(5)}`;
    } else {
      el.className = 'picked';
      el.textContent = 'No parking pin. Navigation ends at the address.';
    }
  };
  if (parkDrop && parkBox) parkDrop.onclick = () => {
    parkBox.classList.remove('hidden');
    const mapEl = $('[data-k=parkmap]', row);
    mapEl.classList.add('pinmap');
    ensurePinMap(mapEl, $('[data-k=park_lat]', row).value || $('[data-k=lat]', row).value, $('[data-k=park_lon]', row).value || $('[data-k=lon]', row).value, (lat, lon) => {
      $('[data-k=park_lat]', row).value = lat;
      $('[data-k=park_lon]', row).value = lon;
      paintPark();
    });
  };
  if (parkClear) parkClear.onclick = () => {
    const lat = $('[data-k=park_lat]', row), lon = $('[data-k=park_lon]', row);
    if (lat) lat.value = '';
    if (lon) lon.value = '';
    const mapEl = $('[data-k=parkmap]', row);
    if (mapEl && mapEl._gcmMarker && mapEl._gcmMap) { mapEl._gcmMap.removeLayer(mapEl._gcmMarker); mapEl._gcmMarker = null; }
    paintPark();
  };
  $('.remStop', row).onclick = () => { row.remove(); refreshMoveButtons(); };
  const photoFile = $('[data-k=photoFile]', row);
  if (photoFile) photoFile.onchange = async () => {
    const file = photoFile.files && photoFile.files[0];
    photoFile.value = '';
    const note = $('[data-k=photoNote]', row);
    if (!file) return;
    try {
      if (note) note.textContent = 'Uploading photo...';
      const url = await uploadShopPhoto(file, 'stop');
      const hidden = $('[data-k=photo]', row);
      if (hidden) hidden.value = url;
      const img = $('[data-k=photoPreview]', row);
      if (img) { img.hidden = false; img.src = url; }
      if (note) note.textContent = 'Photo ready. Save the experience to keep it.';
    } catch (e) { if (note) note.textContent = e.message; }
  };
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
    wrap.innerHTML = stopRowHtml({ label: p.name, lat: p.lat, lon: p.lon, note: p.note }, list.children.length, { parking: true, photo: true });
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
      await refreshShop();
      flash(true, pid ? 'Place saved' : 'Place added');
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
  wireSearchInput($('#afQ'), $('#afSugg'), async (x, input) => {
    const place = await resolvePickedPlace(x, input);
    if (!place) return;
    $('#afQ').value = place.name;
    setAf(place.lat, place.lon, place.name);
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

function rentalCard(s) {
  const lat = Number.isFinite(+s.return_lat) ? String(s.return_lat) : '';
  const lon = Number.isFinite(+s.return_lon) ? String(s.return_lon) : '';
  const placed = lat !== '' && lon !== '';
  return `<div class="card" id="rentalCard"><h2>Return reminders</h2>
    <p class="muted">Renters get a nudge before this time, and a warning when the legal ride back is close to the cart range.</p>
    <label for="rentReturnBy">Return by</label>
    <input id="rentReturnBy" type="time" value="${esc(s.return_by || '')}">
    <label for="rentRemindMin">Nudge renters this long before return</label>
    <select id="rentRemindMin">${[10, 15, 20, 30, 45, 60].map(n => `<option value="${n}"${(+s.remind_min || 15) === n ? ' selected' : ''}>${n} minutes</option>`).join('')}</select>
    <p class="muted">Booked renters (Renters today) are nudged before their own return time, in the map and by email. Everyone else uses Return by.</p>
    <label for="rentRange">Cart range when full (miles)</label>
    <input id="rentRange" inputmode="decimal" placeholder="25" value="${s.range_mi ? esc(String(s.range_mi)) : ''}">
    <label>Where the cart goes back</label>
    <div class="pinmap" id="rentPinMap"></div>
    <p class="muted">Click the map to set the return spot. With no spot, the nudge uses the clock only.</p>
    <input type="hidden" id="rentReturnLat" value="${esc(lat)}">
    <input type="hidden" id="rentReturnLon" value="${esc(lon)}">
    <p id="rentSpot" class="picked${placed ? ' ok' : ''}">${placed ? `Return spot ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}` : 'No return spot yet.'}</p>
    <p><button class="btn" id="saveReminders" type="button">Save reminders</button>
      <button class="btn alt" id="clearReturn" type="button">Clear return spot</button></p>
  </div>`;
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
    const lat = +$('[data-k=lat]', row).value;
    const lon = +$('[data-k=lon]', row).value;
    const stop = {
      label: named || hidden,
      note: $('[data-k=note]', row).value.trim(),
    };
    if (Number.isFinite(lat) && Number.isFinite(lon)) { stop.lat = lat; stop.lon = lon; }
    const plat = $('[data-k=park_lat]', row) ? numCoord($('[data-k=park_lat]', row).value) : NaN;
    const plon = $('[data-k=park_lon]', row) ? numCoord($('[data-k=park_lon]', row).value) : NaN;
    if (Number.isFinite(plat) && Number.isFinite(plon)) { stop.park_lat = plat; stop.park_lon = plon; }
    const photo = ($('[data-k=photo]', row) && $('[data-k=photo]', row).value.trim()) || '';
    if (/^https?:\/\//i.test(photo)) stop.photo = photo;
    return stop;
  }).filter(s => s.label);
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
  list.innerHTML = rows.map((s, i) => stopRowHtml(s, i, { parking: true, photo: true })).join('');
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
  if ($('#exNearest')) $('#exNearest').checked = ex.nearest_start !== false;
  const pushRow = $('#exPushRow');
  if (pushRow) pushRow.classList.toggle('hidden', !ex.template_id);
  if ($('#exPush')) $('#exPush').checked = !!ex.template_id;
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
  if ($('#exNearest')) $('#exNearest').checked = true;
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

let routeSeq = 0;
let routeCache = { geo: '', summary: null };

function relabelRoute(summary, stops) {
  const flags = (summary.flags || []).map(f => ({
    ...f,
    label: (stops[f.index] && stops[f.index].label) || f.label,
  }));
  return { ...summary, flags, stops: stops.length };
}

function wireRouteCheck() {
  const box = $('#routeCheck');
  const list = $('#stopList');
  if (!box || !list || !window.GCMRouteCheck) return;
  let tmr = null;
  const schedule = () => { clearTimeout(tmr); tmr = setTimeout(runRouteCheck, 280); };
  list.addEventListener('input', schedule);
  list.addEventListener('click', schedule);
  const add = $('#addStop');
  if (add) add.addEventListener('click', schedule);
  const place = $('#addPlaceStop');
  if (place) place.addEventListener('change', schedule);
  const veh = $('#brandVehicle');
  if (veh) veh.addEventListener('change', () => { routeCache = { geo: '', summary: null }; schedule(); });
  const reg = $('#brandRegion');
  if (reg) reg.addEventListener('change', () => { routeCache = { geo: '', summary: null }; schedule(); });
  schedule();
}

async function runRouteCheck() {
  const box = $('#routeCheck');
  if (!box || !window.GCMRouteCheck) return;
  const stops = readStops();
  const vehicle = ($('#brandVehicle') && $('#brandVehicle').value) || ((state.shopBundle && state.shopBundle.shop && state.shopBundle.shop.vehicle) || 'golf_cart');
  const regionId = ($('#brandRegion') && $('#brandRegion').value) || ((state.shopBundle && state.shopBundle.shop && state.shopBundle.shop.region_id) || 'sd');
  const geo = vehicle + '|' + regionId + '|' + stops.map(s => (+s.lat).toFixed(5) + ',' + (+s.lon).toFixed(5)).join(';');
  if (routeCache.geo === geo && routeCache.summary) {
    box.innerHTML = GCMRouteCheck.html(relabelRoute(routeCache.summary, stops));
    return;
  }
  const my = ++routeSeq;
  if (stops.length < 2) {
    routeCache = { geo, summary: GCMRouteCheck.summarize(stops, [], vehicle) };
    box.innerHTML = GCMRouteCheck.html(routeCache.summary);
    return;
  }
  box.innerHTML = '<p class="muted">Checking legal roads...</p>';
  try {
    const summary = await GCMRouteCheck.check({ regionId, vehicle, stops });
    if (my !== routeSeq) return;
    routeCache = { geo, summary };
    box.innerHTML = GCMRouteCheck.html(summary);
  } catch (e) {
    if (my !== routeSeq) return;
    routeCache = { geo: '', summary: null };
    box.innerHTML = '<p class="err">Could not check this route. Stops still save.</p>';
  }
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
  const logoFile = $('#brandLogoFile');
  if (logoFile) logoFile.onchange = async () => {
    const file = logoFile.files && logoFile.files[0];
    logoFile.value = '';
    const note = $('#logoFileNote');
    if (!file) return;
    try {
      if (note) note.textContent = 'Uploading logo...';
      const url = await uploadShopPhoto(file, 'logo');
      $('#brandLogo').value = url;
      const img = $('#logoPreview');
      if (img) { img.hidden = false; img.src = url; }
      if (note) note.textContent = 'Logo ready. Click Save brand to keep it.';
    } catch (e) { if (note) note.textContent = e.message; }
  };

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
        phone: $('#brandPhone') ? $('#brandPhone').value.trim() : '',
        push_page: !!($('#brandPush') && $('#brandPush').checked),
      }) });
      await refreshShop();
      flash(true, 'Brand saved');
    } catch (e) { flash(false, e.message); }
  };
  const saveRental = $('#saveRental');
  if (saveRental) saveRental.onclick = async () => {
    try {
      await api('/shop', { method: 'PATCH', body: JSON.stringify({ rental: {
        pickup: $('#rentalPickup').value,
        return_spot: $('#rentalReturn').value,
        return_by: $('#rentalBy').value,
        phone: $('#rentalPhone').value,
        rules: $('#rentalRules').value,
        if_cart_dies: $('#rentalDies').value,
      } }) });
      await refreshShop();
      flash(true, 'Rental info saved');
    } catch (e) { flash(false, e.message); }
  };

  const pin = $('#rentPinMap');
  if (pin) {
    try { ensurePinMap(pin, $('#rentReturnLat').value, $('#rentReturnLon').value, (lat, lon) => {
      $('#rentReturnLat').value = lat;
      $('#rentReturnLon').value = lon;
      const p = $('#rentSpot');
      p.className = 'picked ok';
      p.textContent = `Return spot ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}`;
    }); } catch (e) { /* map tiles are optional; the fields still save */ }
  }
  const clearReturn = $('#clearReturn');
  if (clearReturn) clearReturn.onclick = () => {
    $('#rentReturnLat').value = '';
    $('#rentReturnLon').value = '';
    const p = $('#rentSpot');
    if (p) { p.className = 'picked'; p.textContent = 'No return spot yet.'; }
    if (pin && pin._gcmMarker && pin._gcmMap) { pin._gcmMap.removeLayer(pin._gcmMarker); pin._gcmMarker = null; }
  };
  const saveRemind = $('#saveReminders');
  if (saveRemind) saveRemind.onclick = async () => {
    try {
      await api('/shop', { method: 'PATCH', body: JSON.stringify({
        return_by: $('#rentReturnBy').value,
        remind_min: $('#rentRemindMin') ? $('#rentRemindMin').value : undefined,
        range_mi: $('#rentRange').value,
        return_lat: $('#rentReturnLat').value,
        return_lon: $('#rentReturnLon').value,
      }) });
      await refreshShop();
      flash(true, 'Reminders saved');
    } catch (e) { flash(false, e.message); }
  };

  document.querySelectorAll('#stopList .stop').forEach(wireStop);
  wireRouteCheck();
  const addStop = $('#addStop');
  if (addStop) addStop.onclick = () => {
    const list = $('#stopList');
    const wrap = document.createElement('div');
    wrap.innerHTML = stopRowHtml({}, list.children.length, { parking: true, photo: true });
    const row = wrap.firstElementChild;
    list.appendChild(row);
    wireStop(row);
  };

  wireAffiliatePicker();
  wirePlaces();
  if (window.GCMSalesAdmin) GCMSalesAdmin.bind();

  const addEx = $('#addEx');
  if (addEx) addEx.onclick = async () => {
    try {
      const stops = readStops();
      if (!stops.length) throw new Error('Add at least one stop (search a place or drop a pin)');
      const body = {
        title: $('#exTitle').value.trim(),
        description: $('#exDesc').value,
        stops,
        nearest_start: !$('#exNearest') || $('#exNearest').checked,
        push: !!($('#exPushRow') && !$('#exPushRow').classList.contains('hidden') && $('#exPush') && $('#exPush').checked),
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
        await refreshShop();
        flash(true, 'Affiliate saved');
        return;
      }
      await api('/shop/affiliates', { method: 'POST', body: JSON.stringify({
        name,
        offer: $('#afOffer').value.trim(),
        lat,
        lon,
        generate_coupon: $('#afCoupon').checked,
      }) });
      await refreshShop();
      flash(true, 'Affiliate added');
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
  wireDash();
  if (window.GCMBookings) GCMBookings.bind();
  if (window.GCMReports) GCMReports.bind();
  const regionSel = $('#brandRegion');
  if (regionSel) regionSel.addEventListener('change', () => loadStarters());
  const vehSel = $('#brandVehicle');
  if (vehSel) vehSel.addEventListener('change', () => loadStarters());
  if (window.GCMQuizAdmin) GCMQuizAdmin.bind();
  loadStarters();
  const genCode = $('#genCode');
  const locPick = $('#locPick');
  if (locPick) locPick.onchange = async () => {
    const id = locPick.value;
    const here = state.shopBundle && state.shopBundle.shop;
    if (!here || id === here.id) return;
    const hit = (state.locations || []).find(s => s.id === id);
    if (!hit) return;
    state.actingShop = { id: hit.id, name: hit.name };
    state.msg = ''; state.err = '';
    try { await refreshShop(); } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-copy-ex]').forEach(b => b.onclick = () => {
    const box = $('#copyExBox');
    const ex = ((state.shopBundle && state.shopBundle.experiences) || []).find(e => e.id === b.dataset.copyEx);
    if (!box || !ex) return;
    box.classList.remove('hidden');
    box.dataset.ex = ex.id;
    const label = $('#copyExLabel');
    if (label) label.textContent = 'Copy "' + ex.title + '" to another location.';
    box.scrollIntoView({ block: 'nearest' });
  });
  const copyExGo = $('#copyExGo');
  if (copyExGo) copyExGo.onclick = async () => {
    const box = $('#copyExBox');
    try {
      const j = await api('/shop/copy-experience', { method: 'POST', body: JSON.stringify({
        experience_id: box && box.dataset.ex, dest_shop_id: $('#exDest').value, sync: $('#exSync').checked,
      }) });
      const extra = j.keep_pins ? '' : ' This town is different, so drop new pins on the copy.';
      flash(true, 'Ride copied.' + extra);
    } catch (e) { flash(false, e.message); }
  };
  const copyPage = $('#copyPage');
  if (copyPage) copyPage.onclick = async () => {
    try {
      const j = await api('/shop/copy-page', { method: 'POST', body: JSON.stringify({
        dest_shop_id: $('#pageDest').value, sync: $('#pageSync').checked,
      }) });
      const n = j.copied || {};
      const extra = j.keep_pins ? '' : ' Pins stay in the original town. Drop new pins on the rides.';
      flash(true, 'Page copied (' + (n.experiences || 0) + ' rides).' + extra);
    } catch (e) { flash(false, e.message); }
  };
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
  const makeFleet = $('#makeFleet');
  if (makeFleet) makeFleet.onclick = async () => {
    const carts = ($('#fleetCarts') && $('#fleetCarts').value || '').trim();
    if (!carts) { flash(false, 'Type your cart numbers, like 1-12'); return; }
    const w = window.open('', 'gcm-fleet');
    if (!w) { flash(false, 'Allow pop-ups to print the fleet stickers.'); return; }
    try {
      const j = await api('/shop/fleet', { method: 'POST', body: JSON.stringify({ carts, expires_days: $('#fleetExpire').checked ? 30 : null }) });
      await openFleetSheet(w, j.fleet || []);
      await refreshShop();
      flash(true, `Cart codes ready: ${j.created} new, ${j.reused} kept.`);
    } catch (e) { w.close(); flash(false, e.message); }
  };
  const printFleet = $('#printFleet');
  if (printFleet) printFleet.onclick = async () => {
    const fleet = fleetCodes(state.shopBundle && state.shopBundle.codes);
    if (!fleet.length) { flash(false, 'Make cart codes first'); return; }
    const w = window.open('', 'gcm-fleet');
    if (!w) { flash(false, 'Allow pop-ups to print the fleet stickers.'); return; }
    try { await openFleetSheet(w, fleet); } catch (e) { w.close(); flash(false, e.message); }
  };
  const printQr = $('#printQr');
  if (printQr) printQr.onclick = async () => {
    const code = ($('#qrCode') && $('#qrCode').value) || '';
    if (!code) { flash(false, 'Generate an access code first'); return; }
    const w = window.open('', 'gcm-qr-kit');
    if (!w) { flash(false, 'Allow pop-ups to print the QR kit.'); return; }
    try {
      await loadQrKit();
      if (!window.GCMQrKit) throw new Error('QR kit did not load');
      const s = state.shopBundle.shop;
      const html = GCMQrKit.printHtml({
        name: s.name, slug: s.slug, color: s.color, logoUrl: s.logo_url, code, origin: location.origin,
      });
      w.document.open();
      w.document.write(html);
      w.document.close();
    } catch (e) { w.close(); flash(false, e.message); }
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
  try { state.locations = (await api('/shop/locations')).locations || []; }
  catch (e) { state.locations = state.locations || []; }
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
