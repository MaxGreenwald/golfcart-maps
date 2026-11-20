// Printable cart sticker and counter card for a partner shop.
// The QR encodes the same renter link the admin already copies: /p/<slug>/go?code=CODE.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GCMQrKit = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
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

  // Byte-mode QR, error correction M, versions 1 to 10. Enough for a shop URL.
  // Matrix placement follows the same rules as the Kazuhiko Arase generator (ISO/IEC 18004).
  const RS_M = [
    [[1, 26, 16]],
    [[1, 44, 28]],
    [[1, 70, 44]],
    [[2, 50, 32]],
    [[2, 67, 43]],
    [[4, 43, 27]],
    [[4, 49, 31]],
    [[2, 60, 38], [2, 61, 39]],
    [[3, 58, 36], [2, 59, 37]],
    [[4, 69, 43], [1, 70, 44]],
  ];
  const ALIGN = [
    [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34],
    [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50],
  ];
  const EXP = new Array(256);
  const LOG = new Array(256);
  for (let i = 0; i < 8; i++) EXP[i] = 1 << i;
  for (let i = 8; i < 256; i++) EXP[i] = EXP[i - 4] ^ EXP[i - 5] ^ EXP[i - 6] ^ EXP[i - 8];
  for (let i = 0; i < 255; i++) LOG[EXP[i]] = i;
  function gexp(n) { while (n < 0) n += 255; while (n >= 256) n -= 255; return EXP[n]; }
  function glog(n) { if (n < 1) throw new Error('bad gf'); return LOG[n]; }

  function poly(num) {
    let off = 0;
    while (off < num.length && num[off] === 0) off++;
    const a = num.slice(off);
    if (!a.length) a.push(0);
    return {
      at: i => a[i],
      len: () => a.length,
      mul(e) {
        const out = new Array(a.length + e.len() - 1).fill(0);
        for (let i = 0; i < a.length; i++) if (a[i]) {
          for (let j = 0; j < e.len(); j++) if (e.at(j)) out[i + j] ^= gexp(glog(a[i]) + glog(e.at(j)));
        }
        return poly(out);
      },
      mod(e) {
        if (a.length - e.len() < 0) return this;
        const ratio = glog(a[0]) - glog(e.at(0));
        const out = a.slice();
        for (let i = 0; i < e.len(); i++) if (e.at(i)) out[i] ^= gexp(glog(e.at(i)) + ratio);
        return poly(out).mod(e);
      },
    };
  }
  function eccPoly(n) {
    let p = poly([1]);
    for (let i = 0; i < n; i++) p = p.mul(poly([1, gexp(i)]));
    return p;
  }
  const ECC_POLY = {};
  function blocksFor(version) {
    const out = [];
    for (const [count, total, data] of RS_M[version - 1]) {
      for (let i = 0; i < count; i++) out.push({ total, data, ecc: total - data });
    }
    return out;
  }
  function bytesOf(text) {
    const s = String(text || '');
    const out = [];
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      if (c > 255) throw new Error('QR text must be plain ASCII');
      out.push(c);
    }
    return out;
  }
  function dataBytes(raw, version) {
    const blocks = blocksFor(version);
    let dataCW = 0;
    for (const b of blocks) dataCW += b.data;
    const lenBits = version < 10 ? 8 : 16;
    const bits = [];
    const put = (num, len) => { for (let i = len - 1; i >= 0; i--) bits.push((num >>> i) & 1); };
    put(0b0100, 4);
    put(raw.length, lenBits);
    for (const byte of raw) put(byte, 8);
    const maxBits = dataCW * 8;
    if (bits.length > maxBits) return null;
    for (let i = 0; i < 4 && bits.length < maxBits; i++) bits.push(0);
    while (bits.length % 8) bits.push(0);
    const pad = [0xec, 0x11];
    let p = 0;
    while (bits.length < maxBits) { put(pad[p], 8); p ^= 1; }
    const buf = [];
    for (let i = 0; i < bits.length; i += 8) {
      let v = 0;
      for (let b = 0; b < 8; b++) v = (v << 1) | bits[i + b];
      buf.push(v);
    }
    let offset = 0;
    let maxDc = 0;
    let maxEc = 0;
    const dc = [];
    const ec = [];
    for (const block of blocks) {
      maxDc = Math.max(maxDc, block.data);
      maxEc = Math.max(maxEc, block.ecc);
      const chunk = buf.slice(offset, offset + block.data);
      offset += block.data;
      dc.push(chunk);
      const gen = ECC_POLY[block.ecc] || (ECC_POLY[block.ecc] = eccPoly(block.ecc));
      const mod = poly(chunk.concat(new Array(gen.len() - 1).fill(0))).mod(gen);
      const ecc = new Array(gen.len() - 1).fill(0);
      for (let i = 0; i < ecc.length; i++) {
        const idx = i + mod.len() - ecc.length;
        ecc[i] = idx >= 0 ? mod.at(idx) : 0;
      }
      ec.push(ecc);
    }
    const out = [];
    for (let i = 0; i < maxDc; i++) for (const row of dc) if (i < row.length) out.push(row[i]);
    for (let i = 0; i < maxEc; i++) for (const row of ec) if (i < row.length) out.push(row[i]);
    return out;
  }
  function bchDigit(data) { let n = 0; while (data) { n++; data >>>= 1; } return n; }
  function bch(data, poly, shift) {
    let d = data << shift;
    while (bchDigit(d) - bchDigit(poly) >= 0) d ^= poly << (bchDigit(d) - bchDigit(poly));
    return (data << shift) | d;
  }
  const G15 = 0x537;
  const G18 = 0x1f25;
  const G15_MASK = 0x5412;
  const MASKS = [
    (i, j) => (i + j) % 2 === 0,
    (i, j) => i % 2 === 0,
    (i, j) => j % 3 === 0,
    (i, j) => (i + j) % 3 === 0,
    (i, j) => (Math.floor(i / 2) + Math.floor(j / 3)) % 2 === 0,
    (i, j) => ((i * j) % 2 + (i * j) % 3) === 0,
    (i, j) => (((i * j) % 2 + (i * j) % 3) % 2) === 0,
    (i, j) => (((i * j) % 3 + (i + j) % 2) % 2) === 0,
  ];
  function paint(version, codewords, mask, test) {
    const n = version * 4 + 17;
    const m = Array.from({ length: n }, () => Array(n).fill(null));
    const setFinder = (row, col) => {
      for (let r = -1; r <= 7; r++) {
        if (row + r < 0 || row + r >= n) continue;
        for (let c = -1; c <= 7; c++) {
          if (col + c < 0 || col + c >= n) continue;
          const edge = (r >= 0 && r <= 6 && (c === 0 || c === 6)) || (c >= 0 && c <= 6 && (r === 0 || r === 6));
          const core = r >= 2 && r <= 4 && c >= 2 && c <= 4;
          m[row + r][col + c] = edge || core;
        }
      }
    };
    setFinder(0, 0);
    setFinder(n - 7, 0);
    setFinder(0, n - 7);
    const pos = ALIGN[version - 1];
    for (const row of pos) for (const col of pos) {
      if (m[row][col] != null) continue;
      for (let r = -2; r <= 2; r++) for (let c = -2; c <= 2; c++) {
        m[row + r][col + c] = r === -2 || r === 2 || c === -2 || c === 2 || (r === 0 && c === 0);
      }
    }
    for (let i = 8; i < n - 8; i++) {
      if (m[i][6] == null) m[i][6] = i % 2 === 0;
      if (m[6][i] == null) m[6][i] = i % 2 === 0;
    }
    const info = bch((0 << 3) | mask, G15, 10) ^ G15_MASK;
    for (let i = 0; i < 15; i++) {
      const bit = !test && ((info >> i) & 1) === 1;
      if (i < 6) m[i][8] = bit;
      else if (i < 8) m[i + 1][8] = bit;
      else m[n - 15 + i][8] = bit;
      if (i < 8) m[8][n - i - 1] = bit;
      else if (i < 9) m[8][15 - i - 1 + 1] = bit;
      else m[8][15 - i - 1] = bit;
    }
    m[n - 8][8] = !test;
    if (version >= 7) {
      const bits = bch(version, G18, 12);
      for (let i = 0; i < 18; i++) {
        const mod = !test && ((bits >> i) & 1) === 1;
        m[Math.floor(i / 3)][i % 3 + n - 11] = mod;
        m[i % 3 + n - 11][Math.floor(i / 3)] = mod;
      }
    }
    let row = n - 1;
    let col = n - 1;
    let dir = -1;
    let bitIndex = 7;
    let byteIndex = 0;
    const maskFn = MASKS[mask];
    while (col > 0) {
      if (col === 6) col--;
      while (true) {
        for (let c = 0; c < 2; c++) {
          if (m[row][col - c] == null) {
            let dark = false;
            if (byteIndex < codewords.length) dark = ((codewords[byteIndex] >>> bitIndex) & 1) === 1;
            if (maskFn(row, col - c)) dark = !dark;
            m[row][col - c] = dark;
            bitIndex--;
            if (bitIndex < 0) { byteIndex++; bitIndex = 7; }
          }
        }
        row += dir;
        if (row < 0 || row >= n) { row -= dir; dir = -dir; break; }
      }
      col -= 2;
    }
    return m;
  }
  function penalty(grid) {
    const n = grid.length;
    const darkAt = (r, c) => grid[r][c] === true;
    let lost = 0;
    for (let row = 0; row < n; row++) for (let col = 0; col < n; col++) {
      let same = 0;
      const dark = darkAt(row, col);
      for (let r = -1; r <= 1; r++) {
        if (row + r < 0 || row + r >= n) continue;
        for (let c = -1; c <= 1; c++) {
          if (col + c < 0 || col + c >= n || (r === 0 && c === 0)) continue;
          if (dark === darkAt(row + r, col + c)) same++;
        }
      }
      if (same > 5) lost += 3 + same - 5;
    }
    for (let row = 0; row < n - 1; row++) for (let col = 0; col < n - 1; col++) {
      let count = 0;
      if (darkAt(row, col)) count++;
      if (darkAt(row + 1, col)) count++;
      if (darkAt(row, col + 1)) count++;
      if (darkAt(row + 1, col + 1)) count++;
      if (count === 0 || count === 4) lost += 3;
    }
    for (let row = 0; row < n; row++) for (let col = 0; col < n - 6; col++) {
      if (darkAt(row, col) && !darkAt(row, col + 1) && darkAt(row, col + 2) && darkAt(row, col + 3) && darkAt(row, col + 4) && !darkAt(row, col + 5) && darkAt(row, col + 6)) lost += 40;
    }
    for (let col = 0; col < n; col++) for (let row = 0; row < n - 6; row++) {
      if (darkAt(row, col) && !darkAt(row + 1, col) && darkAt(row + 2, col) && darkAt(row + 3, col) && darkAt(row + 4, col) && !darkAt(row + 5, col) && darkAt(row + 6, col)) lost += 40;
    }
    let darkCount = 0;
    for (let row = 0; row < n; row++) for (let col = 0; col < n; col++) if (darkAt(row, col)) darkCount++;
    lost += (Math.abs(100 * darkCount / n / n - 50) / 5) * 10;
    return lost;
  }
  function gridFor(text) {
    const raw = bytesOf(text);
    let version = 0;
    let codewords = null;
    for (let v = 1; v <= RS_M.length; v++) {
      const data = dataBytes(raw, v);
      if (data) { version = v; codewords = data; break; }
    }
    if (!codewords) throw new Error('That link is too long for a QR code');
    let best = 0;
    let bestLost = 0;
    for (let mask = 0; mask < 8; mask++) {
      const lost = penalty(paint(version, codewords, mask, true));
      if (mask === 0 || lost < bestLost) { bestLost = lost; best = mask; }
    }
    return paint(version, codewords, best, false);
  }

  /** Module rows as '0'/'1' strings. Finder patterns sit in the corners (no quiet zone). */
  function modules(text) {
    return gridFor(text).map(row => row.map(cell => (cell ? '1' : '0')).join(''));
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

  // Fleet sheet: one sticker per cart, six to a letter page. Each page also saves as a PNG.
  const PER_PAGE = 6;
  const PNG_PAGE = { w: 1275, h: 1650, cols: 2, rows: 3, margin: 60, gap: 36 };

  /** Readable text color on a band color (dark text on light colors). */
  function bandInk(color) {
    const h = hexColor(color) || DEFAULT_COLOR;
    const n = parseInt(h.slice(1), 16);
    const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return lum > 140 ? '#073044' : '#ffffff';
  }

  /** Split cart stickers into printed pages of PER_PAGE. */
  function fleetPages(items) {
    const pages = [];
    for (let i = 0; i < (items || []).length; i += PER_PAGE) pages.push(items.slice(i, i + PER_PAGE));
    return pages;
  }

  /**
   * Draw one cart sticker on a 2D canvas context. Self-contained (no outer names) so the
   * print page can carry it as source. item: { cart, code, url, rows }. look: { name, color, ink }.
   */
  function drawSticker(ctx, x, y, w, h, item, look) {
    const r = Math.round(w * 0.05);
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.lineWidth = 2; ctx.strokeStyle = '#cfe7ea'; ctx.stroke();
    ctx.clip();
    const band = Math.round(h * 0.17);
    ctx.fillStyle = look.color; ctx.fillRect(x, y, w, band);
    ctx.fillStyle = look.ink;
    ctx.textBaseline = 'middle';
    const pad = Math.round(w * 0.05);
    const cartText = 'Cart ' + item.cart;
    ctx.font = '800 ' + Math.round(band * 0.42) + 'px system-ui, sans-serif';
    const cartW = ctx.measureText(cartText).width;
    ctx.textAlign = 'right';
    ctx.fillText(cartText, x + w - pad, y + band / 2);
    let size = Math.round(band * 0.36);
    let name = String(look.name || '');
    ctx.textAlign = 'left';
    ctx.font = '800 ' + size + 'px system-ui, sans-serif';
    const room = w - pad * 3 - cartW;
    while (name.length > 1 && ctx.measureText(name).width > room) name = name.slice(0, -2) + '\u2026';
    ctx.fillText(name, x + pad, y + band / 2);
    ctx.fillStyle = '#0b6e86';
    ctx.textAlign = 'center';
    ctx.font = '800 ' + Math.round(h * 0.045) + 'px system-ui, sans-serif';
    ctx.fillText('SCAN FOR YOUR RIDES', x + w / 2, y + band + h * 0.06);
    const rows = item.rows || [];
    const n = rows.length;
    const qr = Math.round(Math.min(w * 0.56, h * 0.5));
    const quiet = 2;
    const cell = qr / (n + quiet * 2);
    const qx = x + (w - qr) / 2, qy = y + band + h * 0.1;
    ctx.fillStyle = '#ffffff'; ctx.fillRect(qx, qy, qr, qr);
    ctx.fillStyle = '#000000';
    for (let rr = 0; rr < n; rr++) {
      for (let cc = 0; cc < n; cc++) {
        if (rows[rr][cc] === '1') ctx.fillRect(qx + (cc + quiet) * cell, qy + (rr + quiet) * cell, Math.ceil(cell), Math.ceil(cell));
      }
    }
    ctx.fillStyle = '#0b3c50';
    ctx.font = '800 ' + Math.round(h * 0.07) + 'px ui-monospace, Menlo, monospace';
    ctx.fillText(item.code, x + w / 2, qy + qr + h * 0.065);
    ctx.fillStyle = '#3e6270';
    ctx.font = '600 ' + Math.round(h * 0.03) + 'px system-ui, sans-serif';
    let url = String(item.url || '');
    while (url.length > 8 && ctx.measureText(url).width > w - pad * 2) url = url.slice(0, -2) + '\u2026';
    ctx.fillText(url, x + w / 2, qy + qr + h * 0.13);
    ctx.restore();
  }

  /** Draw one printed page (up to six stickers) at 150 dpi. Self-contained like drawSticker. */
  function drawPage(ctx, items, look, P, draw) {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, P.w, P.h);
    const cw = (P.w - P.margin * 2 - P.gap * (P.cols - 1)) / P.cols;
    const ch = (P.h - P.margin * 2 - P.gap * (P.rows - 1)) / P.rows;
    items.forEach((item, i) => {
      const col = i % P.cols, row = Math.floor(i / P.cols);
      draw(ctx, P.margin + col * (cw + P.gap), P.margin + row * (ch + P.gap), cw, ch, item, look);
    });
  }

  /**
   * Print page for a whole fleet: opts { name, slug, color, logoUrl, origin, fleet: [{ cart, code }] }.
   * Print or save as PDF from the dialog; "Save page N as PNG" draws the same page on a canvas.
   */
  function fleetHtml(opts) {
    const o = opts || {};
    const name = String(o.name || 'Golf cart rentals').trim() || 'Golf cart rentals';
    const slug = String(o.slug || '').trim();
    const list = (o.fleet || []).filter(f => f && f.code && f.cart);
    if (!list.length) throw new Error('Make cart codes first');
    const color = hexColor(o.color) || DEFAULT_COLOR;
    const ink = bandInk(color);
    const logo = safeLogo(o.logoUrl);
    const items = list.map(f => {
      const code = String(f.code).trim().toUpperCase();
      const url = renterUrl(o.origin || '', slug, code);
      return { cart: String(f.cart), code, url, rows: modules(url) };
    });
    const pages = fleetPages(items);
    const logoImg = logo ? '<img class="logo" alt="" src="' + esc(logo) + '">' : '';
    const sheet = pages.map((pg, pi) => '<div class="page" data-page="' + (pi + 1) + '">' + pg.map(it =>
      '<section class="piece sticker" data-cart="' + esc(it.cart) + '"><div class="band">' + logoImg +
      '<h1>' + esc(name) + '</h1><span class="cart">Cart ' + esc(it.cart) + '</span></div>' +
      '<div class="body"><p class="kicker">Scan for your rides</p>' + svg(it.rows) +
      '<p class="code">' + esc(it.code) + '</p><p class="url">' + softUrl(it.url) + '</p></div></section>').join('') + '</div>').join('');
    const pngButtons = pages.map((_, pi) => '<button type="button" class="png" data-png="' + (pi + 1) + '">Save page ' + (pi + 1) + ' as PNG</button>').join('');
    const data = JSON.stringify({ pages, look: { name, color, ink }, P: PNG_PAGE, slug }).replace(/</g, '\\u003c');
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fleet stickers · ' + esc(name) + '</title>' +
      '<style>' +
      'body{margin:0;font:700 16px/1.35 Nunito,system-ui,sans-serif;color:#0b3c50;background:#eef6f7}' +
      '.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;padding:14px 18px;background:#fff;border-bottom:1px solid #cfe7ea}' +
      '.bar .btns{display:flex;flex-wrap:wrap;gap:8px}' +
      '.bar button{border:0;border-radius:12px;padding:10px 14px;font:800 14px system-ui;background:#14b8c4;color:#fff;cursor:pointer}' +
      '.bar button.png{background:#0b6e86}' +
      '.hint{margin:0;font-size:13px;font-weight:600;max-width:46ch}' +
      '.page{display:grid;grid-template-columns:repeat(2,3.6in);gap:0.25in;justify-content:center;padding:18px}' +
      '.piece{background:#fff;border:1px solid #cfe7ea;border-radius:16px;overflow:hidden;height:3.15in;break-inside:avoid}' +
      '.band{background:' + color + ';color:' + ink + ';padding:8px 12px;display:flex;gap:8px;align-items:center}' +
      '.logo{width:30px;height:30px;object-fit:cover;border-radius:8px;background:#fff}' +
      'h1{margin:0;font-size:15px;line-height:1.2;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.cart{font:900 18px system-ui;white-space:nowrap}' +
      '.body{padding:6px 12px 8px;text-align:center}' +
      '.body svg{width:1.7in;height:1.7in;display:block;margin:0 auto}' +
      '.kicker{margin:0 0 4px;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#0b6e86}' +
      '.code{margin:4px 0 0;font:800 18px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.08em}' +
      '.url{margin:2px 0 0;font-size:9px;font-weight:600;overflow-wrap:anywhere;color:#3e6270}' +
      '@media print{.bar{display:none}body{background:#fff}.page{padding:0;break-after:page}.page:last-child{break-after:auto}}' +
      '@page{size:letter;margin:0.4in}' +
      '</style></head><body>' +
      '<div class="bar"><p class="hint">' + items.length + ' cart sticker' + (items.length === 1 ? '' : 's') + ', six per page. Each QR opens your page with that cart\'s code filled in. Print, or save as PDF from the print dialog.</p>' +
      '<div class="btns"><button type="button" id="doPrint">Print or save as PDF</button>' + pngButtons + '</div></div>' +
      sheet +
      '<script>(function(){var D=' + data + ';var drawSticker=' + drawSticker.toString() + ';var drawPage=' + drawPage.toString() + ';' +
      'document.getElementById("doPrint").onclick=function(){window.print();};' +
      'document.querySelectorAll("[data-png]").forEach(function(b){b.onclick=function(){var i=+b.getAttribute("data-png")-1;' +
      'var c=document.createElement("canvas");c.width=D.P.w;c.height=D.P.h;drawPage(c.getContext("2d"),D.pages[i],D.look,D.P,drawSticker);' +
      'var a=document.createElement("a");a.download=(D.slug||"fleet")+"-stickers-page-"+(i+1)+".png";a.href=c.toDataURL("image/png");document.body.appendChild(a);a.click();a.remove();};});' +
      '})();<\/script></body></html>';
  }

  return { DEFAULT_COLOR, PER_PAGE, PNG_PAGE, esc, hexColor, safeLogo, renterUrl, modules, svg, printHtml, bandInk, fleetPages, drawSticker, drawPage, fleetHtml };
});
