/* Partner admin: problem reports from renters (cart number, what happened, note, contact,
   optional photo). Newest first; the shop marks each one fixed.
   Uses admin.js globals: api, esc, $. */
(function () {
  let info = { reports: [], photos: false, mail: { on: false } };
  let showFixed = false;
  let token = 0;

  function when(t) {
    try {
      return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(t * 1000));
    } catch (e) { return new Date(t * 1000).toLocaleString(); }
  }
  function phone(p) {
    const d = String(p || '');
    return d.length === 10 ? '(' + d.slice(0, 3) + ') ' + d.slice(3, 6) + '-' + d.slice(6) : d;
  }
  function photoCell(r) {
    if (r.photo && info.photos) {
      const src = '/api/partner/shop/reports/' + encodeURIComponent(r.id) + '/photo';
      return `<a href="${esc(src)}" target="_blank" rel="noopener"><img class="rp-thumb" src="${esc(src)}" alt="Photo from the renter"></a>`;
    }
    if (r.photo_status === 'off') return '<span class="muted">Photo not saved (photos off)</span>';
    if (r.photo_status === 'failed') return '<span class="muted">Photo could not be saved</span>';
    return '<span class="muted">No photo</span>';
  }
  function card() {
    return `<div class="card" id="reportsCard"><h2>Problem reports</h2>
      <p class="muted">Renters can tap "Report a problem" on your map to send a cart number, what happened, and an optional note, phone and photo. You get an email and the report shows here.</p>
      <p class="muted" id="rpState"></p>
      <label class="rp-fixed"><input type="checkbox" id="rpShowFixed"> Show fixed reports</label>
      <table id="rpTable"><thead><tr><th>Cart</th><th>What happened</th><th>Photo</th><th></th></tr></thead><tbody id="rpRows"><tr><td colspan="4" class="muted">Loading reports…</td></tr></tbody></table>
    </div>`;
  }
  function rowsHtml() {
    const list = (info.reports || []).filter(r => showFixed || r.status !== 'fixed');
    if (!list.length) return `<tr><td colspan="4" class="muted">${showFixed ? 'No reports yet.' : 'No open reports.'}</td></tr>`;
    return list.map(r => `<tr data-report="${esc(r.id)}" class="${r.status === 'fixed' ? 'rp-done' : ''}">
      <td><b>${r.cart ? 'Cart ' + esc(r.cart) : 'No cart number'}</b><div class="muted">${esc(when(r.created_at))}</div><div class="muted">Code <code>${esc(r.code)}</code></div></td>
      <td><b>${esc(r.kind_label)}</b>${r.note ? `<div class="rp-note">${esc(r.note)}</div>` : ''}
        ${r.contact_name || r.contact_phone ? `<div class="muted">${esc(r.contact_name)}${r.contact_name && r.contact_phone ? ' · ' : ''}${r.contact_phone ? `<a href="tel:+1${esc(r.contact_phone)}">${esc(phone(r.contact_phone))}</a>` : ''}</div>` : ''}
        <div><span class="pill" data-mail="${esc(r.mail)}">${r.mail === 'sent' ? 'Emailed to you' : r.mail === 'failed' ? 'Email failed' : 'Email off'}</span></div></td>
      <td>${photoCell(r)}</td>
      <td>${r.status === 'fixed'
        ? `<button class="btn alt" type="button" data-rp-open="${esc(r.id)}">Reopen</button>`
        : `<button class="btn" type="button" data-rp-fix="${esc(r.id)}">Mark fixed</button>`}</td>
    </tr>`).join('');
  }
  function paint() {
    const rows = $('#rpRows');
    if (rows) rows.innerHTML = rowsHtml();
    const st = $('#rpState');
    if (st) {
      const open = (info.reports || []).filter(r => r.status !== 'fixed').length;
      const bits = [open === 1 ? '1 open report.' : open + ' open reports.'];
      if (!info.photos) bits.push('Photos are off for now, so reports come in without photos.');
      if (!(info.mail && info.mail.on)) bits.push('Report emails are off for now; check this list.');
      st.textContent = bits.join(' ');
    }
    const set = async (id, fixed) => {
      try { await api('/shop/reports/' + encodeURIComponent(id) + '/fixed', { method: 'POST', body: JSON.stringify({ fixed }) }); await load(); }
      catch (e) { if (window.flash) flash(false, e.message); }
    };
    document.querySelectorAll('[data-rp-fix]').forEach(b => { b.onclick = () => set(b.dataset.rpFix, true); });
    document.querySelectorAll('[data-rp-open]').forEach(b => { b.onclick = () => set(b.dataset.rpOpen, false); });
  }
  async function load() {
    const my = ++token;
    try {
      const j = await api('/shop/reports');
      if (my !== token) return;
      info = j;
    } catch (e) {
      info = { reports: [], photos: false, mail: { on: false } };
    }
    paint();
  }
  function bind() {
    if (!$('#reportsCard')) return;
    const cb = $('#rpShowFixed');
    if (cb) cb.onchange = () => { showFixed = cb.checked; paint(); };
    load();
  }
  window.GCMReports = { card, bind };
})();
