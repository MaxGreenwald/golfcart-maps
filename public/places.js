// Saved places on this device (Max, Oct 31 2026, t414u): Home, Favorite beach, plus a few custom favorites.
// Stored in localStorage (works in the iOS app web view too). No account, nothing sent anywhere.
(function (root, f) { const m = f(); if (typeof module === 'object' && module.exports) module.exports = m; else root.GCMPlaces = m; })(this, function () {
  const KEY = 'gcm-places', MAX_CUSTOM = 5;
  const SLOTS = [{ id: 'home', icon: '🏠', title: 'Home' }, { id: 'beach', icon: '🏖️', title: 'Favorite beach' }];
  function make(store) {
    const read = () => { try { const v = JSON.parse(store.getItem(KEY) || '{}'); return v && typeof v === 'object' ? v : {}; } catch (e) { return {}; } };
    const write = v => { try { store.setItem(KEY, JSON.stringify(v)); } catch (e) {} };
    const valid = p => !!p && isFinite(p.lat) && isFinite(p.lon) && Math.abs(p.lat) <= 90 && Math.abs(p.lon) <= 180;
    function list() {
      const v = read(), out = [];
      for (const s of SLOTS) out.push({ ...s, ...(v[s.id] || {}), saved: valid(v[s.id]) });
      Object.keys(v).filter(k => k.startsWith('fav')).sort().forEach(k => { if (valid(v[k])) out.push({ id: k, icon: '⭐', title: v[k].name || 'Favorite', ...v[k], saved: true }); });
      return out;
    }
    function saved() { return list().filter(p => p.saved); }
    function get(id) { return list().find(p => p.id === id && p.saved) || null; }
    function save(id, p) {
      if (!valid(p)) return false;
      const v = read();
      if (id === 'new') {
        const n = Object.keys(v).filter(k => k.startsWith('fav')).length;
        if (n >= MAX_CUSTOM) return false;
        let i = 1; while (v['fav' + i]) i++; id = 'fav' + i;
      }
      if (!SLOTS.some(s => s.id === id) && !/^fav\d+$/.test(id)) return false;
      v[id] = { name: String(p.name || '').slice(0, 60), lat: +p.lat, lon: +p.lon };
      write(v); return id;
    }
    function rename(id, name) { const v = read(); if (!v[id]) return false; v[id].name = String(name || '').slice(0, 60); write(v); return true; }
    function remove(id) { const v = read(); if (!v[id]) return false; delete v[id]; write(v); return true; }
    // Label shown in the dropdown and chips: "Home" / "Favorite beach" / custom name.
    const label = p => p.id.startsWith('fav') ? (p.name || 'Favorite') : p.title;
    return { list, saved, get, save, rename, remove, label };
  }
  return { KEY, SLOTS, MAX_CUSTOM, make };
});
