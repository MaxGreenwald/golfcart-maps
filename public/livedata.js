// livedata.js: native-app town data. The iPhone and CarPlay shells bundle public/ at build time
// (Capacitor webDir dist/, no server.url), so a town added on the site would not show up until
// the next app build. When window.GCM_NATIVE is set (native.js, from Capacitor.isNativePlatform),
// region list and region JSON are fetched from https://golfcartmap.com, stored in the Cache API,
// and the bundled files are the fallback.
//
// Website: this file does not patch fetch. Same-origin data/ requests are unchanged.
// CarPlay: the native scene calls into this same WebView (carplay.js), so it sees the same towns.
// App Store 2.5.2: JSON under /data only. Nothing here downloads or runs script.
// Schema: data/schema.json "schema" must equal SCHEMA. A different number means the live files
// changed shape; this build keeps the bundled copy instead of parsing data it does not understand.
(function (root) {
  const SCHEMA = 1;
  const ORIGIN = 'https://golfcartmap.com';
  const CACHE = 'gcm-live-data-s' + SCHEMA;
  const DATA_RE = /^data\/[a-z0-9][a-z0-9/_-]*\.json$/;
  const TIMEOUT_MS = 8000;

  function dataRel(input) {
    let s = typeof input === 'string' ? input : (input && input.url) || '';
    if (!s) return '';
    if (/^[a-z][a-z0-9+.-]*:/i.test(s)) {
      let u;
      try { u = new URL(s); } catch (e) { return ''; }
      if (u.origin === ORIGIN) return '';
      const local = u.protocol === 'capacitor:' || u.protocol === 'ionic:' || u.hostname === 'localhost' || u.hostname === '127.0.0.1';
      if (!local) return '';
      s = u.pathname;
    }
    s = s.replace(/^\/+/, '').split('?')[0].split('#')[0];
    if (s.indexOf('..') !== -1) return '';
    if (!DATA_RE.test(s)) return '';
    return s;
  }

  function memoryStore() {
    const m = new Map();
    return {
      async get(k) { return m.has(k) ? m.get(k) : null; },
      async put(k, text) { m.set(k, text); },
      async clear() { m.clear(); },
    };
  }

  function cacheStore(caches) {
    if (!caches || typeof caches.open !== 'function') return memoryStore();
    const key = rel => ORIGIN + '/' + rel;
    return {
      async get(rel) {
        try {
          const c = await caches.open(CACHE);
          const r = await c.match(key(rel));
          return r ? await r.text() : null;
        } catch (e) { return null; }
      },
      async put(rel, text) {
        try {
          const c = await caches.open(CACHE);
          await c.put(key(rel), new Response(text, { status: 200, headers: { 'content-type': 'application/json' } }));
        } catch (e) {
          try { console.warn('[gcm] cache put', rel, e && (e.message || e)); } catch (_) {}
        }
      },
      async clear() {
        try { await caches.delete(CACHE); } catch (e) {}
      },
    };
  }

  function schemaNumber(json) {
    if (!json || typeof json !== 'object' || Array.isArray(json)) return null;
    const keys = Object.keys(json);
    if (!keys.every(k => k === 'schema' || k === 'note')) return null;
    if (typeof json.schema !== 'number' || !Number.isInteger(json.schema) || json.schema < 1) return null;
    if (json.note != null && typeof json.note !== 'string') return null;
    return json.schema;
  }

  function validRegion(r) {
    if (!r || typeof r !== 'object') return false;
    if (typeof r.id !== 'string' || !/^[a-z0-9_]+$/.test(r.id)) return false;
    if (typeof r.state !== 'string' || !/^[A-Z]{2}$/.test(r.state)) return false;
    if (typeof r.zoom !== 'number' || !isFinite(r.zoom)) return false;
    if (!Array.isArray(r.center) || r.center.length !== 2 || r.center.some(n => typeof n !== 'number')) return false;
    if (!Array.isArray(r.bbox) || r.bbox.length !== 4 || r.bbox.some(n => typeof n !== 'number')) return false;
    return true;
  }

  function kind(rel) {
    if (rel === 'data/schema.json') return 'schema';
    if (rel === 'data/regions.json') return 'regions';
    if (rel === 'data/rules.json') return 'rules';
    if (/\/index\.json$/.test(rel)) return 'index';
    if (/\/tiles\/[^/]+\.json$/.test(rel)) return 'tile';
    if (/\/pois\.json$/.test(rel)) return 'pois';
    if (/\/chargers\.json$/.test(rel)) return 'chargers';
    return 'json';
  }

  function validate(rel, json) {
    switch (kind(rel)) {
      case 'schema': return schemaNumber(json) != null;
      case 'regions': return Array.isArray(json) && json.length > 0 && json.every(validRegion);
      case 'rules': return !!json && typeof json === 'object' && !Array.isArray(json) && Object.keys(json).length > 0;
      case 'index': return !!json && !!json.meta && Array.isArray(json.meta.tiles) && typeof json.meta.tileSize === 'number' && Array.isArray(json.names);
      case 'tile': return Array.isArray(json);
      case 'pois': return Array.isArray(json);
      case 'chargers': return !!json && typeof json === 'object' && Array.isArray(json.stations);
      default: return !!json && typeof json === 'object' && !Array.isArray(json);
    }
  }

  function parseJson(text) {
    try { return JSON.parse(text); } catch (e) { return undefined; }
  }

  function jsonResponse(text, status) {
    return new Response(text, { status: status || 200, headers: { 'content-type': 'application/json' } });
  }

  function createLoader(opts) {
    opts = opts || {};
    const fetchImpl = opts.fetch;
    const store = opts.store || memoryStore();
    const origin = String(opts.origin || ORIGIN).replace(/\/$/, '');
    const expect = opts.schema == null ? SCHEMA : opts.schema;
    const timeoutMs = opts.timeoutMs == null ? TIMEOUT_MS : opts.timeoutMs;
    let mode = null;
    let gateP = null;
    let net = true;
    let netFails = 0;

    async function fetchLive(rel) {
      if (!net) throw new Error('offline');
      const ctrl = typeof AbortController === 'function' ? new AbortController() : null;
      const timer = setTimeout(() => { if (ctrl) ctrl.abort(); }, timeoutMs);
      try {
        const init = { cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer' };
        if (ctrl) init.signal = ctrl.signal;
        const res = await fetchImpl(origin + '/' + rel, init);
        const text = await res.text();
        return { ok: res.ok, status: res.status, text: text };
      } finally {
        clearTimeout(timer);
      }
    }

    function noteFail() {
      netFails += 1;
      if (netFails >= 2) net = false;
    }

    async function offlineMode() {
      const text = await store.get('data/schema.json');
      const n = schemaNumber(parseJson(text));
      if (n === expect) return 'cache';
      return 'bundled';
    }

    function gate() {
      if (mode) return Promise.resolve(mode);
      if (!gateP) gateP = (async () => {
        try {
          const res = await fetchLive('data/schema.json');
          const n = res.ok ? schemaNumber(parseJson(res.text)) : null;
          if (n === expect) {
            await store.put('data/schema.json', res.text);
            mode = 'live';
          } else if (n != null) {
            mode = 'mismatch';
            await store.clear();
            net = false;
          } else {
            net = false;
            mode = await offlineMode();
          }
        } catch (e) {
          net = false;
          mode = await offlineMode();
        }
        try { console.info('[gcm] towns:', mode); } catch (e) {}
        return mode;
      })();
      return gateP;
    }

    async function fromCache(rel) {
      const text = await store.get(rel);
      if (text == null) return null;
      if (!validate(rel, parseJson(text))) return null;
      return jsonResponse(text, 200);
    }

    async function fetchData(rel, bundledFetch) {
      if (!DATA_RE.test(rel)) return bundledFetch();
      await gate();
      if (mode === 'mismatch' || mode === 'bundled') return bundledFetch();
      if (mode === 'live' && net) {
        try {
          const res = await fetchLive(rel);
          if (res.ok) {
            const json = parseJson(res.text);
            if (validate(rel, json)) {
              await store.put(rel, res.text);
              return jsonResponse(res.text, 200);
            }
          } else if (res.status === 404) {
            return bundledFetch();
          }
        } catch (e) {
          noteFail();
        }
      }
      const cached = await fromCache(rel);
      if (cached) return cached;
      return bundledFetch();
    }

    return {
      fetchData: fetchData,
      gate: gate,
      get mode() { return mode; },
    };
  }

  function install(win) {
    if (!win || !win.GCM_NATIVE || !win.fetch || win.__gcmLiveInstalled) return;
    win.__gcmLiveInstalled = true;
    const orig = win.fetch.bind(win);
    const loader = createLoader({ fetch: orig, store: cacheStore(win.caches) });
    win.GCMLiveData = loader;
    win.fetch = function (input, init) {
      const rel = dataRel(input);
      if (!rel) return orig(input, init);
      return loader.fetchData(rel, function () { return orig(input, init); });
    };
  }

  const api = {
    SCHEMA: SCHEMA,
    ORIGIN: ORIGIN,
    CACHE: CACHE,
    dataRel: dataRel,
    schemaNumber: schemaNumber,
    validate: validate,
    memoryStore: memoryStore,
    createLoader: createLoader,
    install: install,
  };
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.GCMLive = api;
  if (root.document && root.GCM_NATIVE) install(root);
})(typeof window !== 'undefined' ? window : globalThis);
