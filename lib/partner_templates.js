// Copy a partner experience or page to another of that partner's locations.
// Map pins travel only when both shops use the same town. A later edit can
// update every linked copy. Text always updates. Pins update only in the same town.

export function sameTown(a, b) {
  return !!(a && b && a.region_id && a.region_id === b.region_id);
}

function text(v, n) { return String(v || '').slice(0, n); }

function pin(lat, lon) {
  const la = +lat, lo = +lon;
  if (!Number.isFinite(la) || !Number.isFinite(lo)) return null;
  if (Math.abs(la) > 90 || Math.abs(lo) > 180) return null;
  return { lat: la, lon: lo };
}

/** Stops for a new copy. keepPins false drops coordinates so another town is not pinned in the wrong place. */
export function copyStops(stops, keepPins) {
  const out = [];
  for (const s of stops || []) {
    const label = text(s && s.label, 120).trim();
    if (!label) continue;
    const row = { label, note: text(s.note, 500) };
    if (keepPins) {
      const p = pin(s.lat, s.lon);
      if (p) Object.assign(row, p);
    }
    out.push(row);
  }
  return out;
}

/**
 * Apply a source stop list onto a sibling. Same town: take the source pins.
 * Other town: keep the sibling's pin at each index, and add new stops without pins.
 */
export function pushStops(sourceStops, destStops, keepPins) {
  const src = sourceStops || [];
  const dst = destStops || [];
  const out = [];
  for (let i = 0; i < src.length; i++) {
    const s = src[i] || {};
    const prev = dst[i] || {};
    const label = text(s.label || prev.label, 120).trim();
    if (!label) continue;
    const row = { label, note: text(s.note, 500) };
    const p = keepPins ? pin(s.lat, s.lon) : pin(prev.lat, prev.lon);
    if (p) Object.assign(row, p);
    out.push(row);
  }
  return out;
}

/** Brand fields that are the page, not the location. Name, slug, town, and owner stay put. */
export function brandFields(shop) {
  return {
    blurb: text(shop && shop.blurb, 2000),
    logo_url: text(shop && shop.logo_url, 500),
    color: text(shop && shop.color, 32),
    vehicle: shop && shop.vehicle === 'lsv' ? 'lsv' : 'golf_cart',
  };
}

export function experiencePayload(ex, { keepPins, templateId }) {
  return {
    title: text(ex && ex.title, 160).trim(),
    description: text(ex && ex.description, 2000),
    stops: copyStops(ex && ex.stops, keepPins),
    nearest_start: !(ex && (ex.nearest_start === false || ex.nearest_start === 0)),
    template_id: templateId || null,
  };
}
