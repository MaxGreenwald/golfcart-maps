/* Partner admin: rental-day bookings. A shop adds a renter (name, email, optional phone, return time)
   and the renter gets the map link, the local cart rules, and the return time by email.
   Uses admin.js globals: api, esc, $, state, flash. */
(function () {
  const STATUS = {
    sent: ['ok', 'Welcome emailed'],
    off: ['', 'Email off: share the link'],
    failed: ['off', 'Email failed'],
    pending: ['', 'Sending'],
  };
  let info = { bookings: [], mail: { on: false }, sms: { on: false } };
  let token = 0;

  function pad(n) { return String(n).padStart(2, '0'); }
  function localInput(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }
  /** Today at the shop's return-by time when it is still ahead, else three hours from now. */
  function defaultReturn(shop, now) {
    const t = new Date(now.getTime());
    const m = /^(\d{2}):(\d{2})$/.exec((shop && shop.return_by) || '');
    if (m) {
      t.setHours(+m[1], +m[2], 0, 0);
      if (t > now) return localInput(t);
    }
    const later = new Date(now.getTime() + 3 * 3600e3);
    later.setMinutes(later.getMinutes() < 30 ? 0 : 30, 0, 0);
    return localInput(later);
  }
  function whenLabel(b) {
    try {
      return new Intl.DateTimeFormat('en-US', { timeZone: b.tz, hour: 'numeric', minute: '2-digit', weekday: 'short', month: 'short', day: 'numeric' }).format(new Date(b.return_at * 1000));
    } catch (e) { return new Date(b.return_at * 1000).toLocaleString(); }
  }
  // "Head back soon" email status for one booking.
  function remindPill(b) {
    const at = b.remind_at ? whenLabel({ return_at: b.remind_at, tz: b.tz }) : '';
    const txt = {
      scheduled: (info.mail && info.mail.on) ? 'Reminder ' + at : 'Reminder email off',
      sending: 'Reminder sending', sent: 'Reminder sent', off: 'Reminder email off',
      failed: 'Reminder failed', late: 'Reminder skipped (past return)',
    }[b.remind] || '';
    return txt ? `<span class="pill" data-remind="${esc(b.remind)}">${esc(txt)}</span>` : '';
  }
  function linkFor(b) {
    const s = state.shopBundle && state.shopBundle.shop;
    return location.origin + '/p/' + encodeURIComponent((s && s.slug) || '') + '/go?code=' + encodeURIComponent(b.code);
  }

  function rowsHtml() {
    const list = info.bookings || [];
    if (!list.length) return '<tr><td colspan="3" class="muted">No renters booked yet.</td></tr>';
    return list.map(b => {
      const st = STATUS[b.welcome] || STATUS.pending;
      return `<tr data-booking="${esc(b.id)}">
        <td><b>${esc(b.renter_name)}</b><div class="muted">${esc(b.email)}${b.phone ? ' · ' + esc(b.phone) : ''}</div>
          <div class="muted">Code <code>${esc(b.code)}</code></div></td>
        <td>Return ${esc(whenLabel(b))}<div><span class="pill ${st[0]}" data-welcome="${esc(b.welcome)}">${esc(st[1])}</span>
          ${b.phone ? `<span class="pill" data-sms="${esc(b.sms)}">${b.sms === 'sent' ? 'Texted' : 'Text: not set up'}</span>` : ''}
          ${remindPill(b)}</div></td>
        <td><div class="ex-actions">
          <button class="btn alt" type="button" data-bk-copy="${esc(b.id)}">Copy link</button>
          <button class="btn alt" type="button" data-bk-resend="${esc(b.id)}">Resend</button>
          <button class="btn warn" type="button" data-bk-del="${esc(b.id)}">Remove</button>
        </div></td></tr>`;
    }).join('');
  }

  function stateNote() {
    const m = info.mail || {};
    const bits = [];
    if (!m.on) bits.push(esc(m.reason || 'Renter email is off for now.') + ' Bookings still save, and each renter gets a link you can copy and send yourself.');
    bits.push('Text messages are not set up yet, so a phone number is kept for your records only.');
    return bits.join(' ');
  }

  function card() {
    const b = state.shopBundle || {};
    const s = b.shop || {};
    const nowSec = Date.now() / 1000;
    const codes = (b.codes || []).filter(c => !c.expires_at || c.expires_at > nowSec);
    return `<div class="card" id="bookingsCard"><h2>Renters today</h2>
      <p class="muted">Add a renter when they book. They get an email with your map link, the local cart rules, and their return time.</p>
      <p class="msg" id="bkState">${stateNote()}</p>
      <div class="row">
        <div><label for="bkName">Renter name</label><input id="bkName" maxlength="80" autocomplete="off" placeholder="Jamie Rivera"></div>
        <div><label for="bkEmail">Renter email</label><input id="bkEmail" type="email" autocomplete="off" placeholder="jamie@example.com"></div>
      </div>
      <div class="row">
        <div><label for="bkPhone">Phone (optional)</label><input id="bkPhone" inputmode="tel" autocomplete="off" placeholder="858-555-0100"></div>
        <div><label for="bkReturn">Return time</label><input id="bkReturn" type="datetime-local" value="${esc(defaultReturn(s, new Date()))}"></div>
      </div>
      <label for="bkCode">Access code</label>
      <select id="bkCode"><option value="">New code for this renter (ends a day after return)</option>${codes.map(c => `<option value="${esc(c.code)}">${esc(c.code)}${c.cart_label ? ' (cart ' + esc(c.cart_label) + ')' : ''}</option>`).join('')}</select>
      <p><button class="btn" id="addBooking" type="button">Add renter and send welcome</button>
        <button class="btn alt" id="previewBooking" type="button">Preview email</button></p>
      <div id="bkPreview" hidden><p class="muted" id="bkSubject"></p><iframe id="bkFrame" title="Welcome email preview" sandbox="" style="width:100%;height:560px;border:1px solid #cfe7ea;border-radius:12px;background:#fff"></iframe></div>
      <table id="bkTable"><thead><tr><th>Renter</th><th>Return</th><th></th></tr></thead><tbody id="bkRows"><tr><td colspan="3" class="muted">Loading renters…</td></tr></tbody></table>
    </div>`;
  }

  function form() {
    const ret = $('#bkReturn').value;
    const at = ret ? Math.floor(new Date(ret).getTime() / 1000) : NaN;
    return {
      renter_name: $('#bkName').value, email: $('#bkEmail').value, phone: $('#bkPhone').value,
      return_at: at, tz: Intl.DateTimeFormat().resolvedOptions().timeZone, code: $('#bkCode').value,
    };
  }

  function paint() {
    const rows = $('#bkRows');
    if (rows) rows.innerHTML = rowsHtml();
    const note = $('#bkState');
    if (note) note.innerHTML = stateNote();
    document.querySelectorAll('[data-bk-copy]').forEach(btn => btn.onclick = async () => {
      const b = info.bookings.find(x => x.id === btn.dataset.bkCopy);
      if (!b) return;
      try { await navigator.clipboard.writeText(linkFor(b)); btn.textContent = 'Copied'; } catch (e) { prompt('Renter link', linkFor(b)); }
    });
    document.querySelectorAll('[data-bk-resend]').forEach(btn => btn.onclick = async () => {
      try {
        const j = await api('/shop/bookings/' + encodeURIComponent(btn.dataset.bkResend) + '/resend', { method: 'POST', body: '{}' });
        await load();
        flashKeep(j.mail.status === 'sent', j.mail.status === 'sent' ? 'Welcome sent again.' : (j.mail.reason || j.mail.error || 'Email not sent.'));
      } catch (e) { flashKeep(false, e.message); }
    });
    document.querySelectorAll('[data-bk-del]').forEach(btn => btn.onclick = async () => {
      if (!confirm('Remove this renter? Their access code keeps working until it ends.')) return;
      try { await api('/shop/bookings/' + encodeURIComponent(btn.dataset.bkDel), { method: 'DELETE' }); await load(); } catch (e) { flashKeep(false, e.message); }
    });
  }

  // A note inside the card, so the list is not redrawn from scratch.
  function flashKeep(ok, text) {
    const note = $('#bkState');
    if (!note) return;
    note.className = 'msg ' + (ok ? 'ok' : 'err');
    note.textContent = text;
  }

  async function load() {
    const my = ++token;
    try {
      const j = await api('/shop/bookings');
      if (my !== token) return;
      info = j;
    } catch (e) {
      info = { bookings: [], mail: { on: false, reason: e.message }, sms: { on: false } };
    }
    paint();
  }

  function bind() {
    if (!$('#bookingsCard')) return;
    $('#addBooking').onclick = async () => {
      try {
        const j = await api('/shop/bookings', { method: 'POST', body: JSON.stringify(form()) });
        ['#bkName', '#bkEmail', '#bkPhone'].forEach(s => { $(s).value = ''; });
        await load();
        const m = j.mail || {};
        flashKeep(m.status !== 'failed', m.status === 'sent'
          ? 'Welcome sent to ' + j.booking.email + '.'
          : m.status === 'failed' ? 'Saved, but the email failed. Copy the link and send it yourself.'
          : 'Saved. Email is off for now, so copy the link and send it yourself.');
      } catch (e) { flashKeep(false, e.message); }
    };
    $('#previewBooking').onclick = async () => {
      try {
        const j = await api('/shop/bookings/preview', { method: 'POST', body: JSON.stringify(form()) });
        $('#bkPreview').hidden = false;
        $('#bkSubject').textContent = 'Subject: ' + j.subject;
        $('#bkFrame').srcdoc = j.html;
      } catch (e) { flashKeep(false, e.message); }
    };
    load();
  }

  window.GCMBookings = { card, bind, defaultReturn };
})();
