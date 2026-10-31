// offline.js: "Download for offline" for one city (Max, Oct 31 2026).
// Rule (Max, Oct 29 2026, PR #20): online, every request still goes to the network first, so a
// shop page or the map always shows the latest roads. A downloaded city is only a fallback used
// when the network fails. Offline answers carry X-GCM-Offline: 1 so pages can say so, and the
// download date is shown. When back online, each downloaded city is re-checked against the live
// index.json stamp and data/schema.json, and re-downloaded if anything changed.
// Storage: Cache API (web, PWA, and the iOS WKWebView, where it persists per app). JSON and the
// page's own same-origin files only; nothing here downloads script from another origin.
// Basemap: OpenStreetMap's tile servers forbid bulk or offline prefetch, so photo/street tiles are
// NOT saved. Offline, the road lines draw on a plain background (class gcm-offline on <html>).
(function (root) {
  const PREFIX = 'gcm-offline-';
  const META = 'gcm-offline-meta';
  const SCHEMA = 1; // must match data/schema.json and livedata.js
  const ID_RE = /^[a-z0-9_]+$/;

  function readMeta() { try { return JSON.parse(root.localStorage.getItem(META) || '{}') || {}; } catch (e) { return {}; } }
  function writeMeta(m) { try { root.localStorage.setItem(META, JSON.stringify(m)); } catch (e) {} }
  function stampOf(index) { const m = (index && index.meta) || {}; return [m.generated, m.segments, m.ways, (m.tiles || []).length].join('|'); }

  // Every file a city needs. Pure, so it is unit tested.
  function filesFor(id, index) {
    if (!ID_RE.test(id)) throw new Error('bad region id');
    const b = '/data/' + id + '/';
    const out = ['/data/schema.json', '/data/regions.json', '/data/rules.json', b + 'index.json', b + 'pois.json', b + 'chargers.json'];
    /* sd-verified-badge:start */if (id === 'sd') out.push(b + 'verified.json');/* sd-verified-badge:end */
    for (const k of (index.meta.tiles || [])) out.push(b + 'tiles/' + k + '.json');
    return out;
  }

  function create(opts) {
    const fetchImpl = opts.fetch, caches = opts.caches;
    const abs = u => new URL(u, opts.base || root.location.href).href;
    const cacheName = id => PREFIX + id;

    async function getJson(u) {
      const r = await fetchImpl(u, { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + u);
      return r.json();
    }

    async function download(id, o) {
      o = o || {};
      const index = await getJson('/data/' + id + '/index.json');
      const files = filesFor(id, index).concat(o.extra || []);
      const tmp = cacheName(id) + '-tmp';
      await caches.delete(tmp);
      const c = await caches.open(tmp);
      let done = 0, bytes = 0;
      const prog = () => o.onProgress && o.onProgress(done, files.length, bytes);
      prog();
      const one = async u => {
        let r;
        try { r = await fetchImpl(u, { cache: 'no-store' }); } catch (e) { r = null; }
        if (r && r.ok) {
          const body = await r.arrayBuffer();
          bytes += body.byteLength;
          const h = new Headers({ 'content-type': r.headers.get('content-type') || 'application/json' });
          await c.put(abs(u), new Response(body, { status: 200, headers: h }));
        } else if (!/(pois|chargers)\.json$/.test(u) && !(id === 'sd' && /\/sd\/[a-z]+\.json$/.test(u) && !/index\.json$/.test(u)) && !(o.optional || []).includes(u)) {
          throw new Error('Could not download ' + u);
        }
        done++; prog();
      };
      const q = files.slice();
      try {
        await Promise.all(Array.from({ length: 6 }, async () => { while (q.length) await one(q.shift()); }));
      } catch (e) { await caches.delete(tmp); throw e; }
      // Swap in the complete copy only after every required file arrived.
      await caches.delete(cacheName(id));
      const fin = await caches.open(cacheName(id));
      for (const req of await c.keys()) await fin.put(req, await c.match(req));
      await caches.delete(tmp);
      const m = readMeta();
      m[id] = { at: new Date().toISOString(), stamp: stampOf(index), bytes, schema: SCHEMA, files: files.length, extra: o.extra || [] };
      writeMeta(m);
      return m[id];
    }

    async function remove(id) { await caches.delete(cacheName(id)); const m = readMeta(); delete m[id]; writeMeta(m); }

    // Online check: re-download a city whose live data changed, drop it if the schema changed.
    async function refreshAll(onChange) {
      const m = readMeta(), ids = Object.keys(m);
      if (!ids.length) return [];
      let schema;
      try { schema = (await getJson('/data/schema.json')).schema; } catch (e) { return []; }
      const changed = [];
      for (const id of ids) {
        try {
          if (schema !== SCHEMA) { await remove(id); changed.push(id); continue; }
          const idx = await getJson('/data/' + id + '/index.json');
          if (stampOf(idx) !== m[id].stamp) { await download(id, { extra: m[id].extra }); changed.push(id); }
        } catch (e) { /* offline again; try next time */ }
      }
      if (changed.length && onChange) onChange(changed);
      return changed;
    }

    // Network first, always. Only when the network throws do we answer from a downloaded city.
    async function fallback(u) {
      const key = abs(u);
      for (const id of Object.keys(readMeta())) {
        try {
          const c = await caches.open(cacheName(id));
          const r = await c.match(key);
          if (r) { const h = new Headers(r.headers); h.set('X-GCM-Offline', '1'); return new Response(await r.blob(), { status: 200, headers: h }); }
        } catch (e) {}
      }
      return null;
    }

    return { download, remove, refreshAll, fallback, list: readMeta, isDownloaded: id => !!readMeta()[id] };
  }

  function fmtBytes(n) { return n >= 1e6 ? (n / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1e3)) + ' KB'; }
  function fmtDate(iso) { try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }); } catch (e) { return iso; } }

  let sizes = null;
  async function sizeOf(fetchImpl, id) {
    try { if (!sizes) sizes = await (await fetchImpl('/data/offline-sizes.json', { cache: 'no-store' })).json(); } catch (e) { sizes = {}; }
    return sizes[id] || 0;
  }

  function install(win) {
    if (!win || !win.caches || !win.fetch || win.GCMOffline) return;
    const net = win.fetch.bind(win);
    const api = create({ fetch: net, caches: win.caches });
    // Wrap fetch: same-origin data/ and saved page files fall back to the download only on a network error.
    win.fetch = function (input, init) {
      const u = typeof input === 'string' ? input : (input && input.url) || '';
      return net(input, init).catch(async err => {
        let same = false; try { same = new URL(u, win.location.href).origin === win.location.origin; } catch (e) {}
        if (same) { const r = await api.fallback(u); if (r) { win.document.documentElement.classList.add('gcm-offline'); return r; } }
        throw err;
      });
    };
    api.sizeOf = id => sizeOf(net, id);
    api.fmtBytes = fmtBytes; api.fmtDate = fmtDate;
    win.GCMOffline = api;
    const refresh = () => { if (win.navigator.onLine !== false) api.refreshAll(ids => win.dispatchEvent(new CustomEvent('gcm-offline-refreshed', { detail: ids }))); };
    win.addEventListener('online', refresh);
    win.addEventListener('offline', () => win.document.documentElement.classList.add('gcm-offline'));
    if (win.navigator.onLine === false) win.document.documentElement.classList.add('gcm-offline');
    win.addEventListener('online', () => win.document.documentElement.classList.remove('gcm-offline'));
    setTimeout(refresh, 3000);
  }

  const exp = { filesFor, stampOf, create, fmtBytes, install, PREFIX, SCHEMA };
  if (typeof module === 'object' && module.exports) module.exports = exp;
  root.GCMOfflineLib = exp;
  if (root.document) install(root);
})(typeof window !== 'undefined' ? window : globalThis);
