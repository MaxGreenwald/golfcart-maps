// Ready-made partner rides from a town's places. A ride is kept only when every
// leg, including the return to the first stop, is a legal road route (points, not a dashed gap).
// The caller supplies routeStops(stops) => legs, so this file does not load road tiles.

const M_PER_MI = 1609.344;

export const THEMES = [
  {
    key: 'beach',
    title: 'Beach loop',
    description: 'A beach ride on roads that are legal for your carts. Edit any stop before renters see it.',
    kinds: ['beach', 'beach_resort'],
    name: /beach|pier|boardwalk|\bshore\b|coast/i,
  },
  {
    key: 'food',
    title: 'Food stops',
    description: 'Food stops on roads that are legal for your carts. Edit any stop before renters see it.',
    kinds: ['restaurant', 'cafe', 'ice_cream', 'seafood', 'fast_food', 'bar', 'pub', 'food_court'],
    name: null,
    boost: ['restaurant', 'cafe', 'ice_cream', 'seafood'],
  },
  {
    key: 'sunset',
    title: 'Sunset ride',
    description: 'A sunset ride on roads that are legal for your carts. Edit any stop before renters see it.',
    kinds: ['viewpoint', 'beach', 'attraction', 'park'],
    name: /sunset|overlook|lighthouse|pier|\bview\b/i,
  },
];

export const TOWN_THEME = {
  key: 'town',
  title: 'Around town',
  description: 'A short loop on roads that are legal for your carts. Edit any stop before renters see it.',
  kinds: ['park', 'attraction', 'viewpoint', 'museum', 'marina'],
  name: /\b(plaza|harbor|harbour|marina|downtown|pier|lighthouse)\b/i,
};

const SKIP = new Set([
  'school', 'kindergarten', 'university', 'college', 'fuel', 'hospital', 'clinic', 'police',
  'fire_station', 'place_of_worship', 'neighbourhood', 'hamlet', 'suburb', 'town', 'village',
  'locality', 'parking', 'toilets', 'atm', 'bank', 'pharmacy', 'doctors', 'dentist', 'yes',
]);

function havM(a, b) {
  const r = Math.PI / 180;
  const x = (b.lon - a.lon) * r * Math.cos(((a.lat + b.lat) / 2) * r);
  const y = (b.lat - a.lat) * r;
  return Math.sqrt(x * x + y * y) * 6371000;
}

export function placesFromPois(pois) {
  const out = [];
  const seen = new Set();
  for (const row of pois || []) {
    if (!Array.isArray(row) || row.length < 4) continue;
    const name = String(row[0] || '').trim();
    const kind = String(row[1] || '').split(';')[0].trim();
    const lon = +row[2];
    const lat = +row[3];
    if (!name || name.length > 80 || SKIP.has(kind)) continue;
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    if (Math.abs(lat) > 90 || Math.abs(lon) > 180) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ name, kind, lat, lon });
  }
  return out;
}

function themeScore(place, theme) {
  const kinds = theme.kinds instanceof Set ? theme.kinds : new Set(theme.kinds || []);
  let s = 0;
  if (kinds.has(place.kind)) s += 3;
  if (theme.name && theme.name.test(place.name)) s += 4;
  if (theme.boost && theme.boost.includes(place.kind)) s += 2;
  return s;
}

/** Up to `limit` groups of 3 places that fit the theme and sit within maxM of each other. */
export function clusters(places, theme, { limit = 8, maxM = 2800, minM = 200 } = {}) {
  const ranked = places
    .map(p => ({ p, s: themeScore(p, theme) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s || a.p.name.localeCompare(b.p.name));
  const out = [];
  const usedAnchor = new Set();
  for (const { p: anchor } of ranked) {
    if (out.length >= limit) break;
    const id = anchor.name.toLowerCase();
    if (usedAnchor.has(id)) continue;
    usedAnchor.add(id);
    const near = places
      .filter(p => p !== anchor && themeScore(p, theme) > 0)
      .map(p => ({ p, d: havM(anchor, p), s: themeScore(p, theme) }))
      .filter(x => x.d >= minM && x.d <= maxM)
      .sort((a, b) => b.s - a.s || a.d - b.d);
    let group = null;
    for (let i = 0; i < near.length && !group; i++) {
      for (let j = i + 1; j < near.length && j < i + 14; j++) {
        if (havM(near[i].p, near[j].p) < minM) continue;
        group = [anchor, near[i].p, near[j].p];
        break;
      }
    }
    if (group) out.push(group);
  }
  return out;
}

export function legIsLegal(leg) {
  return !!(leg && Array.isArray(leg.points) && leg.points.length >= 2 && !leg.dashed);
}

function routeMiles(legs) {
  let m = 0;
  for (const leg of legs) {
    const pts = leg.points;
    for (let i = 1; i < pts.length; i++) {
      m += havM({ lat: pts[i - 1][0], lon: pts[i - 1][1] }, { lat: pts[i][0], lon: pts[i][1] });
    }
  }
  return m / M_PER_MI;
}

function rideFrom(theme, group, miles) {
  return {
    key: theme.key,
    title: theme.title,
    description: theme.description,
    miles: Math.round(miles * 10) / 10,
    stops: group.map(p => ({
      label: p.name,
      lat: Math.round(p.lat * 1e5) / 1e5,
      lon: Math.round(p.lon * 1e5) / 1e5,
      note: '',
    })),
  };
}

/**
 * Up to 3 rides. routeStops(stops) returns one leg per consecutive pair.
 * A ride is kept only when the path through the stops and back to the first is fully legal
 * and between 0.4 and 18 miles.
 */
export async function pickLoops(places, routeStops, { themes = THEMES, town = true } = {}) {
  const rides = [];
  const used = new Set();
  const list = themes.concat(town ? [TOWN_THEME] : []);
  for (const theme of list) {
    if (rides.length >= 3 && theme.key === 'town') break;
    if (rides.length >= 3) break;
    let found = null;
    const groups = clusters(places, theme);
    const fresh = groups.filter(g => g.every(p => !used.has(p.name.toLowerCase())));
    for (const group of fresh.concat(groups)) {
      const closed = group.map(p => ({ lat: p.lat, lon: p.lon }));
      closed.push(closed[0]);
      let legs = null;
      try { legs = await routeStops(closed); } catch { legs = null; }
      if (!legs || legs.length !== group.length || !legs.every(legIsLegal)) continue;
      const miles = routeMiles(legs);
      if (!(miles >= 0.4 && miles <= 18)) continue;
      found = rideFrom(theme, group, miles);
      break;
    }
    if (!found) continue;
    if (theme.key === 'town' && rides.length >= 2) continue;
    rides.push(found);
    for (const stop of found.stops) used.add(stop.label.toLowerCase());
    if (rides.length >= 3) break;
  }
  return rides.slice(0, 3);
}
