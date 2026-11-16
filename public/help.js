// One-tap help. Builds a tel: link and an sms: message on this device.
// The message includes the renter's location. Nothing is sent to Golf Cart Maps.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMHelp = api;
})(typeof self !== 'undefined' ? self : this, function () {
  function digits(phone) {
    const d = String(phone || '').replace(/\D/g, '');
    const ten = d.length === 11 && d.startsWith('1') ? d.slice(1) : d;
    return /^[2-9]\d{9}$/.test(ten) ? '1' + ten : '';
  }
  function display(phone) {
    const d = digits(phone);
    if (!d) return '';
    const ten = d.slice(1);
    return '(' + ten.slice(0, 3) + ') ' + ten.slice(3, 6) + '-' + ten.slice(6);
  }
  function message(lat, lon) {
    if (lat == null || lon == null || lat === '' || lon === '') return 'I need help with my golf cart. I do not have a location fix yet.';
    const la = +lat, lo = +lon;
    if (Number.isFinite(la) && Number.isFinite(lo) && Math.abs(la) <= 90 && Math.abs(lo) <= 180) {
      const ll = la.toFixed(5) + ', ' + lo.toFixed(5);
      return 'I need help with my golf cart. I am at ' + ll + '. https://maps.apple.com/?ll=' + la.toFixed(5) + ',' + lo.toFixed(5);
    }
    return 'I need help with my golf cart. I do not have a location fix yet.';
  }
  function telHref(phone) {
    const d = digits(phone);
    return d ? 'tel:+' + d : '';
  }
  function smsHref(phone, body) {
    const d = digits(phone);
    if (!d) return '';
    return 'sms:+' + d + '?body=' + encodeURIComponent(body == null ? message() : body);
  }

  function mount(doc, opts) {
    opts = opts || {};
    if (!doc || doc.getElementById('shopHelp') || !digits(opts.phone)) return;
    if (!doc.getElementById('shopHelpCss')) {
      const css = doc.createElement('style');
      css.id = 'shopHelpCss';
      css.textContent = '#shopHelp{border:0;background:#e5484d;color:#fff;font:800 14px Nunito,system-ui,sans-serif;border-radius:999px;padding:8px 14px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.2)}'
        + '#shopHelp.floating{position:fixed;z-index:1300;left:calc(12px + env(safe-area-inset-left,0px));bottom:calc(88px + env(safe-area-inset-bottom,0px))}'
        + 'body.gcm-navigating #shopHelp.floating{bottom:calc(86px + env(safe-area-inset-bottom,0px))}'
        + '#shopHelpSheet{position:fixed;inset:0;z-index:1400;background:rgba(11,60,80,.4);display:flex;align-items:flex-end;justify-content:center}'
        + '#shopHelpSheet[hidden]{display:none!important}'
        + '#shopHelpSheet .card{width:min(420px,100%);background:#fff;color:#17384a;border-radius:18px 18px 0 0;padding:16px 16px calc(16px + env(safe-area-inset-bottom,0px));font:700 15px Nunito,system-ui,sans-serif}'
        + '#shopHelpSheet h2{margin:0 0 6px;font-size:18px}#shopHelpSheet p{margin:0 0 12px}'
        + '#shopHelpSheet a,#shopHelpSheet button{display:block;width:100%;text-align:center;text-decoration:none;border:0;border-radius:12px;padding:12px;font:800 16px Nunito,system-ui,sans-serif;margin-top:8px;cursor:pointer}'
        + '#shopHelpCall{background:#12a150;color:#fff}#shopHelpText{background:#0b6e86;color:#fff}#shopHelpClose{background:#eef3f5;color:#43606b}';
      doc.head.appendChild(css);
    }
    const btn = doc.createElement('button');
    btn.type = 'button';
    btn.id = 'shopHelp';
    btn.textContent = 'Help';
    const top = doc.querySelector('.top-inner');
    if (top) top.appendChild(btn);
    else { btn.className = 'floating'; doc.body.appendChild(btn); }
    const sheet = doc.createElement('div');
    sheet.id = 'shopHelpSheet';
    sheet.hidden = true;
    sheet.innerHTML = '<div class="card" role="dialog" aria-labelledby="shopHelpTitle"><h2 id="shopHelpTitle">Help</h2>'
      + '<p id="shopHelpSub"></p><a id="shopHelpCall">Call shop</a><a id="shopHelpText">Text my location</a>'
      + '<button type="button" id="shopHelpClose">Close</button></div>';
    doc.body.appendChild(sheet);
    const sub = sheet.querySelector('#shopHelpSub');
    const call = sheet.querySelector('#shopHelpCall');
    const text = sheet.querySelector('#shopHelpText');
    sub.textContent = display(opts.phone) ? 'Call or text ' + display(opts.phone) + '.' : 'Call or text the shop.';
    call.textContent = display(opts.phone) ? 'Call ' + display(opts.phone) : 'Call shop';
    call.href = telHref(opts.phone);
    text.href = smsHref(opts.phone, message());
    function currentFix() {
      const g = opts.getFix && opts.getFix();
      if (g && Number.isFinite(+g.lat) && Number.isFinite(+g.lon)) return Promise.resolve(g);
      const geo = typeof navigator !== 'undefined' ? navigator.geolocation : null;
      if (!geo || !geo.getCurrentPosition) return Promise.resolve(null);
      return new Promise(res => {
        geo.getCurrentPosition(
          p => res({ lat: p.coords.latitude, lon: p.coords.longitude }),
          () => res(null),
          { enableHighAccuracy: true, maximumAge: 5000, timeout: 8000 },
        );
      });
    }
    btn.onclick = async () => {
      sheet.hidden = false;
      const fix = await currentFix();
      const body = message(fix && fix.lat, fix && fix.lon);
      text.href = smsHref(opts.phone, body);
      sub.textContent = (display(opts.phone) ? 'Call or text ' + display(opts.phone) + '. ' : '') + (fix ? 'The text includes where you are.' : 'No location yet. The text says so.');
    };
    sheet.querySelector('#shopHelpClose').onclick = () => { sheet.hidden = true; };
    sheet.addEventListener('click', e => { if (e.target === sheet) sheet.hidden = true; });
  }

  return { digits, display, message, telHref, smsHref, mount };
});
