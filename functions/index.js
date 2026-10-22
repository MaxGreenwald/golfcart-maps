// "/" only: the landing page, except map-state links and returning "always open the map" users go straight to /map (302).
// Bots never carry the cookie, so they always get the landing page. utm-only visits stay on the landing page.
const MAP_PARAMS = ['r', 'veh', 'lat', 'lon', 'z', 'paid'];
export function target(url, cookie) {
  const u = new URL(url);
  const param = MAP_PARAMS.some(k => u.searchParams.has(k));
  const skip = /(?:^|;\s*)gcm_skip=1(?:;|$)/.test(cookie || '');
  if (!param && !skip) return null;
  return { location: '/map' + u.search, reason: param ? 'param' : 'cookie' };
}
export async function onRequest(context) {
  const t = target(context.request.url, context.request.headers.get('cookie'));
  if (!t) return context.next();
  return new Response(null, { status: 302, headers: { location: t.location, 'cache-control': 'no-store',
    'set-cookie': `gcm_rd=${t.reason}; Max-Age=60; Path=/; SameSite=Lax; Secure` } });
}
