/* Brand + renter view at /p/<slug>[/go?code=]. Locked city map + experiences + larger affiliate pins. */
const panel = document.getElementById('panel');
const titleEl = document.getElementById('title');
const blurbEl = document.getElementById('blurb');
const fullMap = document.getElementById('fullMap');
const nextBar = document.getElementById('nextBar');
const nextLabel = document.getElementById('nextLabel');
const nextBtn = document.getElementById('nextBtn');

function slugFromPath() {
  const parts = location.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
  // /p/<slug> or /p/<slug>/go
  if (parts[0] === 'p' && parts[1]) return parts[1].toLowerCase();
  return '';
}

const slug = slugFromPath();
const params = new URLSearchParams(location.search);
const codeParam = (params.get('code') || '').trim().toUpperCase();
const isGo = /\/go\/?$/.test(location.pathname) || !!codeParam;

let map, regions = [], region = null, layers = L.layerGroup();
let unlocked = null;
let activeEx = null;
let stopIdx = 0;

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function loadRegions() {
  regions = await fetch('/data/regions.json').then(r => r.json());
}

function setRegion(id) {
  region = regions.find(r => r.id === id) || regions.find(r => r.id === 'sd') || regions[0];
  const citySlug = region.slug || 'sandiego';
  fullMap.href = `/map/${citySlug}?r=${encodeURIComponent(region.id)}&partner=${encodeURIComponent(slug)}${unlocked ? '&code=' + encodeURIComponent(unlocked.code || codeParam) : ''}`;
  if (!map) {
    map = L.map('map', { zoomControl: true }).setView(region.center, region.zoom || 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(map);
    layers.addTo(map);
  } else {
    map.setView(region.center, region.zoom || 13);
  }
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
    html: `<div class="pin-aff">★</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

function drawUnlocked() {
  layers.clearLayers();
  const bounds = [];
  (unlocked.affiliates || []).forEach(a => {
    const m = L.marker([a.lat, a.lon], { icon: affIcon(), zIndexOffset: 600 }).addTo(layers);
    m.bindPopup(`<b>${esc(a.name)}</b><br>${esc(a.offer || '')}${a.coupon ? `<br>Coupon: <code>${esc(a.coupon)}</code>` : ''}<br><span class="muted">Partner offer</span>`);
    bounds.push([a.lat, a.lon]);
  });
  if (activeEx) {
    (activeEx.stops || []).forEach((s, i) => {
      const m = L.marker([s.lat, s.lon], { icon: stopIcon(i + 1), zIndexOffset: 700 }).addTo(layers);
      m.bindPopup(`<b>${i + 1}. ${esc(s.label)}</b>${s.note ? `<br>${esc(s.note)}` : ''}`);
      bounds.push([s.lat, s.lon]);
    });
    if (activeEx.stops && activeEx.stops.length > 1) {
      L.polyline(activeEx.stops.map(s => [s.lat, s.lon]), { color: getComputedStyle(document.documentElement).getPropertyValue('--brand').trim() || '#14b8c4', weight: 4, opacity: 0.85 }).addTo(layers);
    }
  }
  if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
  updateNext();
}

function updateNext() {
  if (!activeEx || !activeEx.stops || !activeEx.stops.length) {
    nextBar.classList.remove('show');
    return;
  }
  nextBar.classList.add('show');
  const s = activeEx.stops[stopIdx];
  nextLabel.textContent = `Stop ${stopIdx + 1}/${activeEx.stops.length}: ${s.label}`;
  map.panTo([s.lat, s.lon]);
}

nextBtn.onclick = () => {
  if (!activeEx || !activeEx.stops.length) return;
  stopIdx = (stopIdx + 1) % activeEx.stops.length;
  updateNext();
};

function teaserView(data) {
  titleEl.textContent = data.shop.name;
  blurbEl.textContent = data.shop.blurb || 'Guided golf cart experiences with Golf Cart Maps.';
  if (data.shop.color) document.documentElement.style.setProperty('--brand', data.shop.color);
  setRegion(data.shop.region_id || 'sd');
  panel.innerHTML = `
    <div class="msg">Ask your rental shop for access. Experiences unlock after you pay the add-on at checkout.</div>
    <div class="row">
      <input id="codeIn" placeholder="Access code" value="${esc(codeParam)}">
      <button class="btn" id="unlockBtn" type="button">Unlock</button>
    </div>
    <p class="muted">${data.experience_count || 0} experiences · ${data.affiliate_count || 0} partner offers when unlocked.</p>
    <p class="legend">Brand page for renters of <b>${esc(data.shop.name)}</b>. City map: ${esc(region.short || region.name)}.</p>`;
  document.getElementById('unlockBtn').onclick = () => {
    const c = document.getElementById('codeIn').value.trim();
    if (!c) return;
    location.href = `/p/${slug}/go?code=${encodeURIComponent(c)}`;
  };
}

function unlockedView() {
  const shop = unlocked.shop;
  titleEl.textContent = shop.name;
  blurbEl.textContent = shop.blurb || 'Your guided experiences and partner offers.';
  if (shop.color) document.documentElement.style.setProperty('--brand', shop.color);
  setRegion(shop.region_id || 'sd');
  const ex = unlocked.experiences || [];
  const af = unlocked.affiliates || [];
  panel.innerHTML = `
    <div class="msg">Unlocked with code <code>${esc(unlocked.code || codeParam)}</code>. Full legal roads: use “Full city map”.</div>
    <h2 style="margin:8px 0 4px;font-size:15px;color:var(--deep)">Experiences</h2>
    ${ex.map(e => `<div class="card" data-ex="${esc(e.id)}"><h3>${esc(e.title)}</h3><p>${esc(e.description || '')} · ${(e.stops || []).length} stops</p></div>`).join('') || '<p class="muted">No experiences yet.</p>'}
    <h2 style="margin:12px 0 4px;font-size:15px;color:var(--deep)">Partner offers</h2>
    ${af.map(a => `<div class="card" style="cursor:default"><h3>★ ${esc(a.name)}</h3><p>${esc(a.offer || '')}${a.coupon ? ` · coupon <code>${esc(a.coupon)}</code>` : ''}</p></div>`).join('') || '<p class="muted">No offers yet.</p>'}
    <p class="legend">★ Larger amber pins = affiliate offers · Numbered pins = experience stops</p>`;
  panel.querySelectorAll('[data-ex]').forEach(el => {
    el.onclick = () => {
      panel.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      activeEx = ex.find(x => x.id === el.dataset.ex);
      stopIdx = 0;
      drawUnlocked();
    };
  });
  if (ex[0]) {
    activeEx = ex[0];
    const first = panel.querySelector('[data-ex]');
    if (first) first.classList.add('active');
  }
  drawUnlocked();
}

async function boot() {
  if (!slug) {
    panel.innerHTML = `<div class="msg err">Missing shop slug. Open /p/&lt;shop-slug&gt;.</div>`;
    return;
  }
  await loadRegions();
  try {
    if (isGo && codeParam) {
      const r = await fetch(`/api/partner/public/${encodeURIComponent(slug)}/unlock?code=${encodeURIComponent(codeParam)}`);
      const j = await r.json();
      if (!r.ok) {
        setRegion((j.shop && j.shop.region_id) || 'sd');
        panel.innerHTML = `<div class="msg err">${esc(j.error || 'Could not unlock')}</div>
          <p><a class="btn alt" href="/p/${esc(slug)}">Back to brand page</a></p>`;
        if (j.shop) { titleEl.textContent = j.shop.name; blurbEl.textContent = j.shop.blurb || ''; }
        return;
      }
      unlocked = j;
      unlockedView();
    } else {
      const r = await fetch(`/api/partner/public/${encodeURIComponent(slug)}`);
      const j = await r.json();
      if (!r.ok) {
        panel.innerHTML = `<div class="msg err">${esc(j.error || 'Shop not found')}</div>`;
        return;
      }
      teaserView(j);
    }
  } catch (e) {
    panel.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
}

boot();
