// Renter "Report a problem": cart number, what happened, an optional note, name, phone and photo.
// Sent to the shop (email plus the admin list). The photo field shows only when the shop's
// photo storage is on; the report works without it.
(function (root) {
  const KINDS = [
    ['damage', 'Damage'], ['flat', 'Flat tire'], ['wont_start', 'Won\u2019t start'],
    ['battery', 'Battery low'], ['accident', 'Accident'], ['other', 'Something else'],
  ];
  const MAX_SIDE = 1600;
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  // Shrink a camera photo to a JPEG under the 1.5 MB limit, as base64 without the data: prefix.
  async function photoB64(file) {
    if (!file) return '';
    const url = URL.createObjectURL(file);
    try {
      const img = await new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = url; });
      const k = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth || 1, img.naturalHeight || 1));
      const c = document.createElement('canvas');
      c.width = Math.max(1, Math.round(img.naturalWidth * k));
      c.height = Math.max(1, Math.round(img.naturalHeight * k));
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      for (const q of [0.82, 0.7, 0.55]) {
        const d = c.toDataURL('image/jpeg', q);
        const b64 = d.slice(d.indexOf(',') + 1);
        if (b64.length * 3 / 4 < 1.4 * 1024 * 1024) return b64;
      }
      return '';
    } finally { URL.revokeObjectURL(url); }
  }
  function mount(slot, o) {
    if (!slot || !o || !o.slug || !o.code) return;
    const api = o.api || '/api/partner';
    slot.innerHTML = `<section class="rental rp" id="reportCard">
      <button type="button" class="rp-open" id="rpOpen" aria-expanded="false">\u{1F6E0}\uFE0F Report a problem with your cart</button>
      <form id="rpForm" hidden novalidate>
        <h2 class="sec">Report a problem</h2>
        <p class="fine">${esc(o.shopName || 'The shop')} gets this right away.</p>
        <label class="rp-l" for="rpCart">Cart number</label>
        <input class="goq" id="rpCart" maxlength="12" autocomplete="off" value="${esc(o.cart || '')}" placeholder="On the cart, e.g. 7">
        <label class="rp-l" for="rpKind">What happened</label>
        <select class="goq" id="rpKind"><option value="">Pick one</option>${KINDS.map(k => `<option value="${k[0]}">${esc(k[1])}</option>`).join('')}</select>
        <label class="rp-l" for="rpNote">Details (optional)</label>
        <textarea class="goq" id="rpNote" maxlength="1000" rows="3" placeholder="Where it happened, what you see"></textarea>
        <div id="rpPhotoRow" hidden><label class="rp-l" for="rpPhoto">Photo (optional)</label><input id="rpPhoto" type="file" accept="image/*" capture="environment"></div>
        <label class="rp-l" for="rpName">Your name (optional)</label>
        <input class="goq" id="rpName" maxlength="80" autocomplete="name">
        <label class="rp-l" for="rpPhone">Your phone (optional)</label>
        <input class="goq" id="rpPhone" inputmode="tel" autocomplete="tel" placeholder="So the shop can call you">
        <p><button type="submit" class="rp-send" id="rpSend">Send to the shop</button></p>
        <p class="msg" id="rpMsg" hidden role="status"></p>
      </form>
    </section>`;
    const $ = id => slot.querySelector('#' + id);
    const say = (ok, t) => { const m = $('rpMsg'); m.hidden = false; m.className = 'msg' + (ok ? '' : ' err'); m.textContent = t; };
    $('rpOpen').onclick = () => {
      const f = $('rpForm');
      f.hidden = !f.hidden;
      $('rpOpen').setAttribute('aria-expanded', String(!f.hidden));
      if (!f.hidden) (o.cart ? $('rpKind') : $('rpCart')).focus({ preventScroll: true });
    };
    fetch(api + '/public/' + encodeURIComponent(o.slug) + '/report-info')
      .then(r => r.ok ? r.json() : {}).then(j => { if (j && j.photos) $('rpPhotoRow').hidden = false; }).catch(() => {});
    $('rpForm').onsubmit = async e => {
      e.preventDefault();
      const kind = $('rpKind').value;
      if (!kind) { say(false, 'Pick what happened.'); return; }
      $('rpSend').disabled = true;
      try {
        const file = $('rpPhoto').files && $('rpPhoto').files[0];
        const photo = !$('rpPhotoRow').hidden && file ? await photoB64(file) : '';
        const body = {
          code: o.code, cart: $('rpCart').value, kind, note: $('rpNote').value,
          contact_name: $('rpName').value, contact_phone: $('rpPhone').value,
          tz: (Intl.DateTimeFormat().resolvedOptions() || {}).timeZone || '',
        };
        if (photo) body.photo_base64 = photo;
        const r = await fetch(api + '/public/' + encodeURIComponent(o.slug) + '/report', {
          method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) { say(false, j.error || 'Could not send. Call the shop.'); return; }
        const call = o.phone ? ' If you need help now, call ' + o.phone + '.' : '';
        say(true, 'Sent. ' + (o.shopName || 'The shop') + ' has your report' + (j.report && j.report.cart ? ' for cart ' + j.report.cart : '') + '.' + (j.photo === 'failed' ? ' The photo could not be saved.' : '') + call);
        ['rpNote', 'rpPhoto'].forEach(id => { $(id).value = ''; });
        if (typeof o.onSent === 'function') o.onSent(j);
      } catch (err) {
        say(false, 'Could not send. Check your connection or call the shop.');
      } finally { $('rpSend').disabled = false; }
    };
  }
  root.GCMReport = { mount, KINDS };
})(typeof self !== 'undefined' ? self : this);
