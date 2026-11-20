/* Partner admin: sales mode for dealers. The shop turns on a public /s/<slug> page, sets the
   "buy from this shop" card, and makes a link for any home address that shows the legal cart roads
   reachable from it. Uses admin.js globals: api, esc, $, flash, refreshShop, state,
   wireSearchInput, resolvePickedPlace. */
(function () {
  let draft = null; // unsaved edits kept across the re-render a failed save causes
  function shop() { return (state.shopBundle && state.shopBundle.shop) || {}; }
  function sales() { return draft ? { ...GCMSales.DEFAULTS, ...draft } : GCMSales.fromRow(shop().sales || {}); }
  function card() {
    const s = sales(), sh = shop();
    const reach = GCMSales.REACH.map(n => `<option value="${n}"${n === s.reach_mi ? ' selected' : ''}>${n} miles</option>`).join('');
    return `<div class="card" id="salesCard"><h2>Sales mode (for dealers)</h2>
      <p class="muted">Selling carts? Send a buyer a link for their address. It shows every legal ${sh.vehicle === 'lsv' ? 'LSV' : 'golf cart'} road they can drive from home, your places in reach, and a card to buy from you. No code needed.</p>
      <label class="sales-on"><input type="checkbox" id="salesOn"${s.on ? ' checked' : ''}> Turn on my sales page</label>
      <label for="salesHeadline">Headline (optional)</label><input id="salesHeadline" maxlength="80" value="${esc(s.headline)}" placeholder="Your new neighborhood, by cart">
      <label for="salesBlurb">About (optional)</label><textarea id="salesBlurb" maxlength="400" placeholder="Street-legal LSVs and golf carts, delivered and serviced locally.">${esc(s.blurb)}</textarea>
      <div class="row">
        <div><label for="salesUrl">Link to buy (https)</label><input id="salesUrl" maxlength="300" inputmode="url" value="${esc(s.url)}" placeholder="https://yourshop.com/carts"></div>
        <div><label for="salesCta">Button text</label><input id="salesCta" maxlength="40" value="${esc(s.cta)}" placeholder="Buy from this shop"></div>
      </div>
      <div class="row">
        <div><label for="salesPhone">Sales phone (optional)</label><input id="salesPhone" maxlength="40" inputmode="tel" value="${esc(s.phone)}" placeholder="${esc(sh.phone || 'Uses your shop phone')}"></div>
        <div><label for="salesReach">How far to show</label><select id="salesReach">${reach}</select></div>
      </div>
      <p style="margin-top:12px"><button class="btn" id="saveSales" type="button">Save sales page</button></p>
      <h3 class="dash-h">Make a link for a home</h3>
      <div class="place-wrap"><label for="salesAddr">Buyer's address</label><input id="salesAddr" autocomplete="off" placeholder="Search an address"><div class="sugg" id="salesSugg"></div></div>
      <div id="salesLinkRow" class="hidden" style="margin-top:8px">
        <input id="salesLink" readonly aria-label="Sales link">
        <p><button class="btn alt" id="copySales" type="button">Copy link</button> <a class="btn alt" id="openSales" href="#" target="_blank" rel="noopener">Open</a></p>
      </div>
      <p class="muted" id="salesOffNote"${s.on ? ' hidden' : ''}>The link works once the sales page is on and saved.</p>
    </div>`;
  }
  function body() {
    return { sales: {
      on: $('#salesOn').checked, headline: $('#salesHeadline').value, blurb: $('#salesBlurb').value,
      url: $('#salesUrl').value.trim(), cta: $('#salesCta').value, phone: $('#salesPhone').value, reach_mi: +$('#salesReach').value,
    } };
  }
  function bind() {
    const save = $('#saveSales');
    if (!save) return;
    save.onclick = async () => {
      const b = body();
      try {
        const c = GCMSales.clean(b.sales);
        if (c.error) throw new Error(c.error);
        await api('/shop', { method: 'PATCH', body: JSON.stringify(b) });
        draft = null;
        await refreshShop();
        flash(true, b.sales.on ? 'Sales page saved and on' : 'Sales page saved (off)');
      } catch (e) { draft = b.sales; flash(false, e.message); }
    };
    const inp = $('#salesAddr');
    wireSearchInput(inp, $('#salesSugg'), async (x, input) => {
      const p = await resolvePickedPlace(x, input);
      if (!p) { flash(false, 'Could not find that address'); return; }
      const url = GCMSales.link(location.origin, shop().slug, { lat: p.lat, lon: p.lon, label: p.name });
      inp.value = p.name;
      $('#salesLink').value = url;
      $('#openSales').href = url;
      $('#salesLinkRow').classList.remove('hidden');
    });
    $('#copySales').onclick = async () => {
      const v = $('#salesLink').value;
      try { await navigator.clipboard.writeText(v); flash(true, 'Link copied'); }
      catch (e) { $('#salesLink').select(); flash(true, 'Link selected. Copy it to share.'); }
    };
  }
  window.GCMSalesAdmin = { card, bind };
})();
