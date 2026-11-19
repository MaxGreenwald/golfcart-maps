/* Partner admin: off-limits zones. The shop draws an area (tap corners) or a road segment (tap
   along the road), names it, and saves. Renters see it shaded on their map, routes go around it
   when there is a legal way, and riders hear a warning when they get close.
   Uses admin.js globals: api, esc, $, flash, refreshShop, state, activeRegion, regionCenter. */
(function () {
  let mode = '', pts = [], map = null, drawLayer = null, savedLayer = null;
  const RED = '#b42318';
  function zones() { return (state.shopBundle && state.shopBundle.offlimits) || []; }
  function card() {
    const rows = zones().map(z => `<tr data-zone="${esc(z.id)}">
      <td><b>${z.kind === 'area' ? '⛔ Area' : '⛔ Road'}: ${esc(z.name)}</b>${z.note ? `<div class="muted">${esc(z.note)}</div>` : ''}
        <div class="muted">${z.points.length} points</div></td>
      <td><div class="ex-actions"><button class="btn alt" type="button" data-zone-show="${esc(z.id)}">Show</button>
        <button class="btn warn" type="button" data-zone-del="${esc(z.id)}">Delete</button></div></td></tr>`).join('');
    return `<div class="card" id="offCard"><h2>Off-limits areas</h2>
      <p class="muted">Mark places renters must not drive: a boardwalk, a private lot, a beach access road. Renters see them shaded red on their map. Routes go around them when there is another legal way. If there isn't, the renter is warned before the ride, and the voice warns them when they get close.</p>
      <div class="off-tools">
        <button class="btn alt" type="button" id="offArea" aria-pressed="false">Draw an area</button>
        <button class="btn alt" type="button" id="offLine" aria-pressed="false">Draw a road segment</button>
        <button class="btn alt" type="button" id="offUndo" disabled>Undo point</button>
        <button class="btn alt" type="button" id="offClear" disabled>Clear</button>
      </div>
      <p class="muted" id="offHint">Pick what to draw, then tap the map.</p>
      <div class="pinmap offmap" id="offMap"></div>
      <label for="offName">Name renters see</label><input id="offName" maxlength="60" placeholder="Boardwalk">
      <label for="offNote">Note (optional)</label><input id="offNote" maxlength="200" placeholder="Walkers and bikes only. Park at the lot on Grand Ave.">
      <p style="margin-top:12px"><button class="btn" type="button" id="offSave" disabled>Save off-limits zone</button></p>
      <table><thead><tr><th>Off limits</th><th></th></tr></thead><tbody>${rows || '<tr><td colspan="2" class="muted">None yet.</td></tr>'}</tbody></table>
    </div>`;
  }
  function need() { return mode === 'area' ? 3 : 2; }
  function paintDraft() {
    if (!drawLayer) return;
    drawLayer.clearLayers();
    if (pts.length) {
      if (mode === 'area' && pts.length >= 3) L.polygon(pts, { color: RED, weight: 2, fillColor: '#e5484d', fillOpacity: 0.25 }).addTo(drawLayer);
      else L.polyline(pts, { color: RED, weight: mode === 'line' ? 7 : 2, opacity: 0.8 }).addTo(drawLayer);
      pts.forEach(p => L.circleMarker(p, { radius: 5, color: RED, fillColor: '#fff', fillOpacity: 1, weight: 2 }).addTo(drawLayer));
    }
    const n = pts.length, left = Math.max(0, need() - n);
    $('#offUndo').disabled = !n;
    $('#offClear').disabled = !n;
    $('#offSave').disabled = !mode || left > 0;
    $('#offHint').textContent = !mode ? 'Pick what to draw, then tap the map.'
      : mode === 'area' ? (left ? `Tap the map to add the corners of the area (${left} more to go).` : `${n} corners. Tap to add more, or name it and save.`)
        : (left ? `Tap along the road, start to end (${left} more to go).` : `${n} points along the road. Tap to add more, or name it and save.`);
    for (const [id, m] of [['#offArea', 'area'], ['#offLine', 'line']]) $(id).setAttribute('aria-pressed', mode === m ? 'true' : 'false');
  }
  function paintSaved() {
    if (!savedLayer) return;
    savedLayer.clearLayers();
    for (const z of zones()) {
      const sh = z.kind === 'area'
        ? L.polygon(z.points, { color: RED, weight: 2, dashArray: '6 4', fillColor: '#e5484d', fillOpacity: 0.15 })
        : L.polyline(z.points, { color: RED, weight: 8, opacity: 0.55, dashArray: '2 10', lineCap: 'round' });
      sh.bindPopup(`<b>${esc(z.name)}</b>${z.note ? '<br>' + esc(z.note) : ''}`).addTo(savedLayer);
      sh._zoneId = z.id;
    }
  }
  function setMode(m) { mode = m; pts = []; paintDraft(); }
  function bind() {
    const el = $('#offMap');
    if (!el || !window.L) return;
    const reg = activeRegion();
    const c = regionCenter(reg);
    map = L.map(el, { zoomControl: true }).setView(c, 15);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map);
    savedLayer = L.layerGroup().addTo(map);
    drawLayer = L.layerGroup().addTo(map);
    paintSaved();
    const all = zones().flatMap(z => z.points);
    if (all.length) map.fitBounds(all, { padding: [24, 24], maxZoom: 17 });
    map.on('click', e => {
      if (!mode) return;
      pts.push([+e.latlng.lat.toFixed(6), +e.latlng.lng.toFixed(6)]);
      paintDraft();
    });
    $('#offArea').onclick = () => setMode(mode === 'area' ? '' : 'area');
    $('#offLine').onclick = () => setMode(mode === 'line' ? '' : 'line');
    $('#offUndo').onclick = () => { pts.pop(); paintDraft(); };
    $('#offClear').onclick = () => { pts = []; paintDraft(); };
    $('#offSave').onclick = async () => {
      try {
        const body = { kind: mode, name: $('#offName').value, note: $('#offNote').value, points: pts };
        if (window.GCMOffLimits) { const c = GCMOffLimits.clean(body); if (c.error) throw new Error(c.error); }
        await api('/shop/offlimits', { method: 'POST', body: JSON.stringify(body) });
        mode = ''; pts = [];
        await refreshShop();
        flash(true, 'Off-limits zone saved. Renters see it on their map.');
      } catch (e) { flash(false, e.message); }
    };
    document.querySelectorAll('[data-zone-del]').forEach(b => {
      b.onclick = async () => {
        const z = zones().find(x => x.id === b.dataset.zoneDel);
        if (!confirm(`Delete the off-limits zone "${z ? z.name : ''}"? Renters will be able to route through it again.`)) return;
        try { await api('/shop/offlimits/' + b.dataset.zoneDel, { method: 'DELETE' }); await refreshShop(); flash(true, 'Off-limits zone deleted'); }
        catch (e) { flash(false, e.message); }
      };
    });
    document.querySelectorAll('[data-zone-show]').forEach(b => {
      b.onclick = () => {
        const z = zones().find(x => x.id === b.dataset.zoneShow);
        if (z && map) { map.fitBounds(z.points, { padding: [30, 30], maxZoom: 18 }); el.scrollIntoView({ block: 'center' }); }
      };
    });
    paintDraft();
    setTimeout(() => map && map.invalidateSize(), 50);
  }
  window.GCMOffAdmin = { card, bind, map: () => map };
})();
