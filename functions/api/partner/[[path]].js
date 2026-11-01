// Same-origin proxy to the gcm-partner Worker (shops / invites / experiences / affiliates / codes).
// golfcartmap.com -> gcm-partner; previews -> gcm-partner-preview. Forwards Cookie for sessions.
const SUB = 'maxgreenwald-assistant.workers.dev';
export function partnerBase(host, env) {
  if (env && env.PARTNER_URL) return env.PARTNER_URL.replace(/\/$/, '');
  return (host === 'golfcartmap.com' || host === 'www.golfcartmap.com')
    ? `https://gcm-partner.${SUB}`
    : `https://gcm-partner-preview.${SUB}`;
}
function cors(origin) {
  return {
    'access-control-allow-origin': origin || '*',
    'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': 'content-type',
    'access-control-allow-credentials': 'true',
    'access-control-max-age': '86400',
  };
}
export async function onRequest(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: cors(request.headers.get('origin')) });
  }
  const parts = [].concat(params.path || []);
  const path = '/' + parts.map(decodeURIComponent).join('/');
  const base = partnerBase(url.hostname, env);
  const target = base + path + url.search;
  const headers = new Headers();
  const ct = request.headers.get('content-type');
  if (ct) headers.set('content-type', ct);
  const cookie = request.headers.get('cookie');
  if (cookie) headers.set('cookie', cookie);
  headers.set('x-partner-origin', url.origin);
  let body = undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') body = await request.arrayBuffer();
  let res;
  try {
    res = await fetch(target, { method: request.method, headers, body });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'partner worker unreachable', detail: String(e), target: base }), {
      status: 502,
      headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  }
  const out = new Headers(res.headers);
  out.set('cache-control', 'no-store');
  // Public shop pages are read from the iOS app too (capacitor://localhost), so allow any origin, no cookies.
  if (path.startsWith('/public/')) {
    out.set('access-control-allow-origin', '*');
    out.delete('access-control-allow-credentials');
  }
  // Forward Set-Cookie (session) to the Pages host
  const sc = res.headers.getSetCookie ? res.headers.getSetCookie() : [];
  if (sc && sc.length) {
    out.delete('set-cookie');
    for (const c of sc) out.append('set-cookie', c);
  }
  return new Response(res.body, { status: res.status, headers: out });
}
