/* Sales mode page at /s/<shop>?at=<lat>,<lon>&home=<label>: the legal roads a cart can reach from
   a home, the shop's places in reach, and a "buy from this shop" card. Roads and rules come from the
   shared router (public/router.js reachable()) and road rule (public/roadrule.js), same as the map. */
(function () {
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const API = window.GCMAppLink ? GCMAppLink.apiBase(window) : '/api/partner';
  const page = GCMSales.parse(location.pathname, location.search);
  let info = null, region = null, rules = null, api = null, home = page.home, reachMi = 0, map = null, layer = null, token = 0;
  const fresh = u => fetch(u, { cache: 'no-store' });

  function prettyPhone(p) {
    const d = String(p || '').replace(/\D/g, '').replace(/^1(?=\d{10}$)/, '');
    return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : p;
  }
  function vehWord(v) { return v === 'lsv' ? 'street-legal LSV' : 'golf cart'; }
  function fail(text) {
    $('reachCard').innerHTML = `<div class="msg" role="alert">${esc(text)}</div>`;
    $('mapNote').textContent = '';
  }
  function paintBuy() {
    const s = info.sales, sh = info.shop;
    const tel = GCMSales.telHref(s.phone);
    const box = $('buyCard');
    box.innerHTML = `${sh.logo_url ? `<img class="logo" src="${esc(sh.logo_url)}" alt="">` : ''}
      <h2>${esc(s.headline || ('Get a ' + vehWord(sh.vehicle) + ' from ' + sh.name))}</h2>
      <p>${esc(s.blurb || `${sh.name} sells carts for this area. Ask about the one that fits these roads.`)}</p>
      ${s.url ? `<a class="cta" id="buyLink" href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.cta)}</a>` : ''}
      ${tel ? `<a class="${s.url ? 'alt' : 'cta'}" id="buyCall" href="${esc(tel)}">Call ${esc(prettyPhone(s.phone))}</a>` : ''}
      <p class="fine">From ${esc(sh.name)}. Golf Cart Maps shows the roads; the shop handles the sale.</p>`;
    box.hidden = false;
  }
  function paintReachBtns() {
    $('reachBtns').innerHTML = GCMSales.REACH.map(n => `<button type="button" data-mi="${n}" aria-pressed="${n === reachMi}">${n} mi</button>`).join('');
    $('reachBtns').querySelectorAll('button').forEach(b => { b.onclick = () => { reachMi = +b.dataset.mi; paintReachBtns(); draw(); }; });
  }
  async function draw() {
    const my = ++token;
    if (!home) { $('mapNote').textContent = 'Search an address to see what you can reach.'; return; }
    $('homeLine').innerHTML = `<b>From ${esc(home.label || 'this home')}</b>`;
    $('mapNote').textContent = `Tracing legal ${vehWord(info.shop.vehicle)} roads…`;
    let r = null;
    try { r = await api.reachable(home, reachMi); } catch (e) { r = null; }
    if (my !== token) return;
    layer.clearLayers();
    const homeIcon = L.divIcon({ className: '', html: '<div style="width:30px;height:30px;border-radius:50%;background:#0b3c50;color:#fff;display:flex;align-items:center;justify-content:center;font-size:16px;border:3px solid #fff;box-shadow:0 2px 6px #0006">🏠</div>', iconSize: [30, 30], iconAnchor: [15, 15] });
    L.marker([home.lat, home.lon], { icon: homeIcon, zIndexOffset: 900, title: home.label || 'Home' }).addTo(layer);
    if (!r || !r.ok) {
      $('stats').hidden = true;
      $('places').innerHTML = '';
      $('mapNote').textContent = r && r.reason === 'far'
        ? 'This address is not near a road on our map. Try the street address instead.'
        : 'Roads did not load. Check the connection and try again.';
      map.setView([home.lat, home.lon], 14);
      return;
    }
    const renderer = L.canvas({ padding: 0.3 });
    for (const s of r.segs) L.polyline(s, { renderer, color: '#12a150', weight: 4, opacity: 0.9, interactive: false }).addTo(layer);
    const all = r.segs.flat();
    const places = (info.places || []).map(p => ({ ...p, mi: r.at(p.lat, p.lon) }));
    for (const p of places) {
      const ok = p.mi != null;
      L.circleMarker([p.lat, p.lon], { radius: 8, color: '#fff', weight: 2, fillColor: ok ? '#12a150' : '#b42318', fillOpacity: 1 })
        .bindPopup(`<b>${esc(p.name)}</b><br>${ok ? `${p.mi} mi by cart` : 'Not on legal cart roads from here'}`).addTo(layer);
    }
    places.sort((a, b) => (a.mi == null) - (b.mi == null) || (a.mi || 0) - (b.mi || 0));
    $('places').innerHTML = places.map(p => `<li><span>${esc(p.name)}</span>${p.mi != null ? `<span class="yes">${p.mi} mi</span>` : `<span class="no">Not in reach</span>`}</li>`).join('');
    $('roadMi').textContent = String(Math.round(r.roadMiles));
    $('placeN').textContent = String(places.filter(p => p.mi != null).length);
    $('stats').hidden = false;
    $('ruleLine').textContent = `Green roads are legal for a ${vehWord(info.shop.vehicle)} (${GCMRule.switchName(api.rule)}) and within ${reachMi} miles of road from home, one way. That is about ${reachMi * 2} miles there and back.`;
    $('mapNote').textContent = all.length ? 'Green: roads you can drive from this home. Tap a dot for a place.' : 'No legal cart roads from this address.';
    if (all.length) map.fitBounds(all.concat([[home.lat, home.lon]]), { padding: [20, 20], maxZoom: 16 });
    else map.setView([home.lat, home.lon], 15);
    if (my === token) history.replaceState(null, '', GCMSales.link('', page.slug, home));
  }
  function wireSearch() {
    const inp = $('addr'), sg = $('sugg');
    let t = 0, ac = null;
    inp.oninput = () => {
      clearTimeout(t);
      t = setTimeout(async () => {
        const q = inp.value.trim();
        if (q.length < 3) { sg.innerHTML = ''; return; }
        if (ac) ac.abort();
        ac = new AbortController();
        const c = region && region.center;
        const bias = home || (Array.isArray(c) ? { lat: +c[0], lon: +c[1] } : null);
        let list = [];
        try { list = await GCMGeo.remote(q, bias, (u, sig) => fetch(u, { signal: sig }).then(x => x.json()), ac.signal); } catch (e) { list = []; }
        if (inp.value.trim() !== q) return;
        sg.innerHTML = list.slice(0, 5).map((x, k) => `<button type="button" data-k="${k}"><b>${esc(x.name)}</b><span>${esc(x.sub || '')}</span></button>`).join('');
        sg.querySelectorAll('button').forEach(b => { b.onclick = () => {
          const x = list[+b.dataset.k];
          home = { lat: +x.lat, lon: +x.lon, label: x.name };
          sg.innerHTML = ''; inp.value = x.name;
          draw();
        }; });
      }, 250);
    };
  }
  async function boot() {
    if (!page.slug) { fail('This link needs a shop name, like /s/your-shop.'); return; }
    let j;
    try { const r = await fresh(`${API}/public/${encodeURIComponent(page.slug)}/sales`); j = await r.json(); if (!r.ok) { fail(j.error || 'This shop has no sales page.'); return; } }
    catch (e) { fail('Could not load this page. Check the connection.'); return; }
    info = j;
    const sh = info.shop;
    document.title = `What can you reach by cart? · ${sh.name}`;
    $('shopName').textContent = sh.name;
    if (sh.logo_url) { $('shopLogo').src = sh.logo_url; $('shopLogo').hidden = false; }
    if (/^#[0-9a-f]{6}$/i.test(sh.color || '')) document.documentElement.style.setProperty('--brand', sh.color);
    $('headline').textContent = `Where can a ${vehWord(sh.vehicle)} take you from ${home && home.label ? home.label : 'here'}?`;
    reachMi = GCMSales.REACH.includes(+info.sales.reach_mi) ? +info.sales.reach_mi : 5;
    paintBuy();
    paintReachBtns();
    wireSearch();
    const [regs, rl] = await Promise.all([fresh('/data/regions.json').then(r => r.json()), fresh('/data/rules.json').then(r => r.json())]);
    rules = rl;
    region = regs.find(r => r.id === sh.region_id) || regs.find(r => r.id === 'sd') || regs[0];
    map = L.map('map', { zoomControl: true });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map);
    layer = L.layerGroup().addTo(map);
    const c = region && region.center;
    map.setView(home ? [home.lat, home.lon] : (Array.isArray(c) ? [+c[0], +c[1]] : [32.8, -117.25]), 14);
    api = await GCMRouter.openRegion(region, rules, sh.vehicle === 'lsv' ? 'lsv' : 'golf_cart', fresh);
    await draw();
  }
  boot();
})();
