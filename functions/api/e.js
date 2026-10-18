// Same-origin analytics sink: cleans the event (lib/analytics.js allowlist) and forwards it to the
// gcm-analytics Worker. Forwards no IP, user agent, cookies or headers. Always 204, so a failure
// never reaches the app. golfcartmap.com -> gcm-analytics; previews -> gcm-analytics-preview.
import { sanitize } from '../../lib/analytics.js';
const SUB = 'maxgreenwald-assistant.workers.dev';
const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST', 'access-control-allow-headers': 'content-type', 'access-control-max-age': '86400' };
const NC = () => new Response(null, { status: 204, headers: { 'cache-control': 'no-store', ...CORS } });
export function sinkFor(host, env) {
  if (env && env.ANALYTICS_URL) return env.ANALYTICS_URL;
  return (host === 'golfcartmap.com' || host === 'www.golfcartmap.com') ? `https://gcm-analytics.${SUB}/e` : `https://gcm-analytics-preview.${SUB}/e`;
}
export async function onRequestPost({ request, env, waitUntil }) {
  try {
    const t = await request.text(); if (t.length > 4000) return NC();
    const r = sanitize(JSON.parse(t)); if (!r) return NC();
    const body = JSON.stringify({ e: r.event, t: r.town, pl: r.platform, pwa: r.pwa === 1, i: r.iid, s: r.sid, p: r.props });
    const f = fetch(sinkFor(new URL(request.url).hostname, env), { method: 'POST', body, headers: { 'content-type': 'application/json' } }).catch(() => {});
    if (waitUntil) waitUntil(f); else await f;
  } catch (_) {}
  return NC();
}
export const onRequestOptions = () => new Response(null, { status: 204, headers: CORS });
export const onRequestGet = () => new Response('POST only', { status: 405 });
