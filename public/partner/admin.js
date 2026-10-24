/* Partner admin SPA — super admin + shop admin. Talks to /api/partner/*. */
const api = (path, opt = {}) => fetch('/api/partner' + path, {
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

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
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

function regionOptions(selected) {
  const list = regions.filter(r => !r.hidden).slice().sort((a, b) => (a.short || a.name).localeCompare(b.short || b.name));
  // San Diego first as default
  list.sort((a, b) => (a.id === 'sd' ? -1 : 0) - (b.id === 'sd' ? -1 : 0) || (a.short || '').localeCompare(b.short || ''));
  return list.map(r => `<option value="${esc(r.id)}" ${r.id === selected ? 'selected' : ''}>${esc(r.short || r.name)} (${esc(r.id)})</option>`).join('');
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

function stopEditor(stops) {
  const rows = (stops && stops.length ? stops : [{ label: '', lat: '', lon: '', note: '' }]).map((s, i) => `
    <div class="stop" data-i="${i}">
      <input data-k="label" placeholder="Label (Seals in La Jolla)" value="${esc(s.label || '')}">
      <input data-k="lat" placeholder="Lat" value="${esc(s.lat ?? '')}">
      <input data-k="lon" placeholder="Lon" value="${esc(s.lon ?? '')}">
      <button class="btn alt remStop" type="button">✕</button>
      <input data-k="note" placeholder="Note (optional)" value="${esc(s.note || '')}" style="grid-column:1/-1">
    </div>`).join('');
  return `<div class="stops" id="stopList">${rows}</div>
    <p><button class="btn alt" id="addStop" type="button">Add stop</button></p>`;
}

function shopView() {
  const b = state.shopBundle;
  if (!b || !b.shop) return `<div class="card"><p class="msg err">No shop linked to this account yet. Accept an invite from Max.</p></div>`;
  const s = b.shop;
  const exRows = (b.experiences || []).map(e => `<tr>
    <td><b>${esc(e.title)}</b><div class="muted">${esc(e.description || '')}</div>
      <div class="muted">${(e.stops || []).map((x, i) => `${i + 1}. ${esc(x.label)}`).join(' · ') || 'No stops'}</div></td>
    <td><button class="btn warn" data-del-ex="${esc(e.id)}" type="button">Delete</button></td>
  </tr>`).join('') || '<tr><td colspan="2" class="muted">No experiences yet.</td></tr>';
  const afRows = (b.affiliates || []).map(a => `<tr>
    <td><b>${esc(a.name)}</b><div class="muted">${esc(a.offer || '')}</div>
      <div class="muted">${a.lat.toFixed(5)}, ${a.lon.toFixed(5)}${a.coupon ? ` · coupon <code>${esc(a.coupon)}</code>` : ''}</div></td>
    <td><button class="btn warn" data-del-af="${esc(a.id)}" type="button">Delete</button></td>
  </tr>`).join('') || '<tr><td colspan="2" class="muted">No affiliate offers yet.</td></tr>';
  const codeRows = (b.codes || []).map(c => `<tr>
    <td><code>${esc(c.code)}</code></td>
    <td class="muted">uses ${c.uses}${c.max_uses ? '/' + c.max_uses : ''} · ${c.multi_use ? 'multi' : 'single'}</td>
    <td><a href="/p/${esc(s.slug)}/go?code=${esc(c.code)}" target="_blank" rel="noopener">Open renter link</a></td>
  </tr>`).join('') || '<tr><td colspan="3" class="muted">No codes yet.</td></tr>';
  return `
  <div class="card"><h2>${esc(s.name)}</h2>
    <p>Brand page: <a href="/p/${esc(s.slug)}" target="_blank">/p/${esc(s.slug)}</a>
      · City: <span class="pill">${esc(s.region_id)}</span></p>
    ${state.msg ? `<div class="msg ok">${esc(state.msg)}</div>` : ''}
    ${state.err ? `<div class="msg err">${esc(state.err)}</div>` : ''}
  </div>
  <div class="card"><h2>Brand</h2>
    <label>Display name</label><input id="brandName" value="${esc(s.name)}">
    <label>City / region</label><select id="brandRegion">${regionOptions(s.region_id || 'sd')}</select>
    <label>Short blurb</label><textarea id="brandBlurb">${esc(s.blurb || '')}</textarea>
    <div class="row">
      <div><label>Logo URL (optional)</label><input id="brandLogo" value="${esc(s.logo_url || '')}" placeholder="https://…"></div>
      <div><label>Primary color (optional)</label><input id="brandColor" value="${esc(s.color || '')}" placeholder="#14b8c4"></div>
    </div>
    <p style="margin-top:12px"><button class="btn" id="saveBrand" type="button">Save brand</button></p>
  </div>
  <div class="card"><h2>Experiences</h2>
    <p class="muted">Ordered joyride stops on the map (e.g. seals in La Jolla → cove → lunch).</p>
    <label>Title</label><input id="exTitle" placeholder="La Jolla seals joyride">
    <label>Description</label><textarea id="exDesc" placeholder="A 45-minute coastal loop"></textarea>
    <label>Stops</label>${stopEditor([{ label: 'La Jolla seals', lat: 32.847, lon: -117.278, note: 'Watch from the sidewalk' }, { label: 'La Jolla Cove', lat: 32.850, lon: -117.272, note: '' }])}
    <p><button class="btn" id="addEx" type="button">Add experience</button></p>
    <table><thead><tr><th>Experience</th><th></th></tr></thead><tbody>${exRows}</tbody></table>
  </div>
  <div class="card"><h2>Affiliate offers</h2>
    <p class="muted">Restaurants and deals for your renters. They show as slightly larger pins on the map.</p>
    <div class="row">
      <div><label>Place name</label><input id="afName" placeholder="Sunset Bar"></div>
      <div><label>Offer</label><input id="afOffer" placeholder="25% off a beer"></div>
    </div>
    <div class="row">
      <div><label>Lat</label><input id="afLat" placeholder="32.849"></div>
      <div><label>Lon</label><input id="afLon" placeholder="-117.274"></div>
    </div>
    <label><input type="checkbox" id="afCoupon" checked> Generate coupon code</label>
    <p><button class="btn" id="addAf" type="button">Add affiliate</button></p>
    <table><thead><tr><th>Affiliate</th><th></th></tr></thead><tbody>${afRows}</tbody></table>
  </div>
  <div class="card"><h2>Renter access codes</h2>
    <p class="muted">Give this link after they pay the extra $5–10 in your own checkout. Multi-use, 30-day expiry by default.</p>
    <p><button class="btn" id="genCode" type="button">Generate access code</button></p>
    <table><thead><tr><th>Code</th><th>Usage</th><th>Link</th></tr></thead><tbody>${codeRows}</tbody></table>
  </div>`;
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

function readStops() {
  return [...document.querySelectorAll('#stopList .stop')].map(row => ({
    label: $('[data-k=label]', row).value.trim(),
    lat: +$('[data-k=lat]', row).value,
    lon: +$('[data-k=lon]', row).value,
    note: $('[data-k=note]', row).value.trim(),
  })).filter(s => s.label && Number.isFinite(s.lat) && Number.isFinite(s.lon));
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
      await api('/admin/shops', { method: 'POST', body: JSON.stringify({ name, slug, region_id }) });
      flash(true, 'Shop created');
      await refreshSuper();
    } catch (e) { flash(false, e.message); }
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

  const saveBrand = $('#saveBrand');
  if (saveBrand) saveBrand.onclick = async () => {
    try {
      await api('/shop', { method: 'PATCH', body: JSON.stringify({
        name: $('#brandName').value.trim(),
        region_id: $('#brandRegion').value,
        blurb: $('#brandBlurb').value,
        logo_url: $('#brandLogo').value.trim(),
        color: $('#brandColor').value.trim(),
      }) });
      flash(true, 'Brand saved');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  const addStop = $('#addStop');
  if (addStop) addStop.onclick = () => {
    const list = $('#stopList');
    const div = document.createElement('div');
    div.className = 'stop';
    div.innerHTML = `<input data-k="label" placeholder="Label"><input data-k="lat" placeholder="Lat"><input data-k="lon" placeholder="Lon"><button class="btn alt remStop" type="button">✕</button><input data-k="note" placeholder="Note" style="grid-column:1/-1">`;
    list.appendChild(div);
    div.querySelector('.remStop').onclick = () => div.remove();
  };
  document.querySelectorAll('.remStop').forEach(b => b.onclick = () => b.closest('.stop').remove());
  const addEx = $('#addEx');
  if (addEx) addEx.onclick = async () => {
    try {
      await api('/shop/experiences', { method: 'POST', body: JSON.stringify({
        title: $('#exTitle').value.trim(),
        description: $('#exDesc').value,
        stops: readStops(),
      }) });
      flash(true, 'Experience added');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-del-ex]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this experience?')) return;
    try { await api('/shop/experiences/' + b.dataset.delEx, { method: 'DELETE' }); await refreshShop(); }
    catch (e) { flash(false, e.message); }
  });
  const addAf = $('#addAf');
  if (addAf) addAf.onclick = async () => {
    try {
      await api('/shop/affiliates', { method: 'POST', body: JSON.stringify({
        name: $('#afName').value.trim(),
        offer: $('#afOffer').value.trim(),
        lat: +$('#afLat').value,
        lon: +$('#afLon').value,
        generate_coupon: $('#afCoupon').checked,
      }) });
      flash(true, 'Affiliate added');
      await refreshShop();
    } catch (e) { flash(false, e.message); }
  };
  document.querySelectorAll('[data-del-af]').forEach(b => b.onclick = async () => {
    if (!confirm('Delete this affiliate?')) return;
    try { await api('/shop/affiliates/' + b.dataset.delAf, { method: 'DELETE' }); await refreshShop(); }
    catch (e) { flash(false, e.message); }
  });
  const genCode = $('#genCode');
  if (genCode) genCode.onclick = async () => {
    try {
      const j = await api('/shop/codes', { method: 'POST', body: JSON.stringify({ multi_use: true, expires_days: 30 }) });
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
  if (me.user.super) await refreshSuper();
  else {
    try { await refreshShop(); }
    catch (e) { state.err = e.message; state.shopBundle = null; state.view = 'shop'; render(); }
  }
}

boot().catch(e => { app.innerHTML = `<div class="card msg err">${esc(e.message)}</div>`; });
