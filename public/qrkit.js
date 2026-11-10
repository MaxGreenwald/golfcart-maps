// Printable cart sticker and counter card for a partner shop.
// The QR encodes the same renter link the admin already copies: /p/<slug>/go?code=CODE.
(function (root, factory) {
  const api = factory(typeof root.qrcode === 'function' ? root.qrcode : null);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMQrKit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (qrcode) {
  const DEFAULT_COLOR = '#14b8c4';

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function hexColor(raw) {
    const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(raw ?? '').trim());
    if (!m) return '';
    let h = m[1].toLowerCase();
    if (h.length === 3) h = h.replace(/./g, c => c + c);
    return '#' + h;
  }

  function safeLogo(url) {
    try {
      const u = new URL(String(url || '').trim());
      if (u.protocol !== 'https:' && u.protocol !== 'http:') return '';
      if (u.username || u.password) return '';
      return u.href;
    } catch (e) { return ''; }
  }

  /** Absolute renter link with the access code filled in. */
  function renterUrl(origin, slug, code) {
    const base = String(origin || '').replace(/\/$/, '');
    const s = encodeURIComponent(String(slug || '').trim());
    const c = encodeURIComponent(String(code || '').trim().toUpperCase());
    return base + '/p/' + s + '/go?code=' + c;
  }

  /** Module rows as '0'/'1' strings. Finder patterns sit in the corners (no quiet zone). */
  function modules(text) {
    if (typeof qrcode !== 'function') throw new Error('QR library did not load');
    const qr = qrcode(0, 'M');
    qr.addData(String(text || ''));
    qr.make();
    const n = qr.getModuleCount();
    const rows = [];
    for (let r = 0; r < n; r++) {
      let bits = '';
      for (let c = 0; c < n; c++) bits += qr.isDark(r, c) ? '1' : '0';
      rows.push(bits);
    }
    return rows;
  }

  function softUrl(url) {
    return esc(url).replace(/([/?&=])/g, '$1<wbr>');
  }

  function svg(rows) {
    const n = rows.length;
    const cell = 8;
    const quiet = 4;
    const size = (n + quiet * 2) * cell;
    let d = '';
    for (let r = 0; r < n; r++) {
      const row = rows[r];
      for (let c = 0; c < n; c++) {
        if (row[c] !== '1') continue;
        const x = (c + quiet) * cell;
        const y = (r + quiet) * cell;
        d += 'M' + x + ' ' + y + 'h' + cell + 'v' + cell + 'h-' + cell + 'z';
      }
    }
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + size + ' ' + size + '" role="img" aria-label="QR code"><rect width="100%" height="100%" fill="#ffffff"/><path fill="#000000" d="' + d + '"/></svg>';
  }

  /**
   * Standalone print page: a cart sticker and a counter card.
   * opts: { name, slug, color, logoUrl, code, origin }
   */
  function printHtml(opts) {
    const o = opts || {};
    const name = String(o.name || 'Golf cart rentals').trim() || 'Golf cart rentals';
    const code = String(o.code || '').trim().toUpperCase();
    if (!code) throw new Error('Pick an access code first');
    const slug = String(o.slug || '').trim();
    const url = renterUrl(o.origin || '', slug, code);
    const color = hexColor(o.color) || DEFAULT_COLOR;
    const logo = safeLogo(o.logoUrl);
    const mark = svg(modules(url));
    const logoImg = logo ? '<img class="logo" alt="" src="' + esc(logo) + '">' : '';
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>QR kit · ' + esc(name) + '</title>' +
      '<style>' +
      'body{margin:0;font:700 16px/1.35 Nunito,system-ui,sans-serif;color:#0b3c50;background:#eef6f7}' +
      '.bar{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:14px 18px;background:#fff;border-bottom:1px solid #cfe7ea}' +
      '.bar button{border:0;border-radius:12px;padding:10px 14px;font:800 14px system-ui;background:#14b8c4;color:#fff;cursor:pointer}' +
      '.hint{margin:0;font-size:13px;font-weight:600}' +
      '.sheet{display:flex;flex-wrap:wrap;gap:18px;justify-content:center;padding:18px}' +
      '.piece{background:#fff;border:1px solid #cfe7ea;border-radius:16px;overflow:hidden;box-shadow:0 2px 10px #0b3c5010}' +
      '.sticker{width:3.4in}.card{width:4.2in}' +
      '.band{background:' + color + ';color:#073044;padding:12px 14px;display:flex;gap:10px;align-items:center}' +
      '.logo{width:42px;height:42px;object-fit:cover;border-radius:10px;background:#fff}' +
      'h1{margin:0;font-size:18px;line-height:1.2}' +
      '.body{padding:12px 14px 16px;text-align:center}' +
      '.body svg{width:2.15in;height:2.15in;display:block;margin:0 auto}' +
      '.card .body svg{width:2.6in;height:2.6in}' +
      '.kicker{margin:0 0 8px;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:#0b6e86}' +
      '.code{margin:8px 0 0;font:800 22px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em}' +
      '.url{margin:8px 0 0;font-size:11px;font-weight:600;overflow-wrap:anywhere;color:#3e6270}' +
      '@media print{.bar{display:none}body{background:#fff}.sheet{padding:0;gap:0.35in}.piece{box-shadow:none;break-inside:avoid}}' +
      '@page{margin:0.5in}' +
      '</style></head><body>' +
      '<div class="bar"><p class="hint">Cart sticker and counter card. Use the print dialog to print or save a PDF.</p><button type="button" id="doPrint">Print or save as PDF</button></div>' +
      '<div class="sheet">' +
      '<section class="piece sticker"><div class="band">' + logoImg + '<h1>' + esc(name) + '</h1></div>' +
      '<div class="body"><p class="kicker">Scan for your rides</p>' + mark +
      '<p class="code">' + esc(code) + '</p>' +
      '<p class="url">' + softUrl(url) + '</p></div></section>' +
      '<section class="piece card"><div class="band">' + logoImg + '<h1>' + esc(name) + '</h1></div>' +
      '<div class="body"><p class="kicker">Ask the desk, then scan</p>' + mark +
      '<p class="code">' + esc(code) + '</p>' +
      '<p class="url">Or open ' + softUrl(url) + '</p></div></section>' +
      '</div><script>document.getElementById("doPrint").onclick=function(){window.print();};<\/script></body></html>';
  }

  return { DEFAULT_COLOR, esc, hexColor, safeLogo, renterUrl, modules, svg, printHtml };
});
