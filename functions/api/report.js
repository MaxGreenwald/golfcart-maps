// Same-origin road/hazard report endpoint: cleans the report (lib/reports.js) and forwards it to the gcm-reports
// Worker review queue. Forwards no IP, user agent, cookies or headers. golfcartmap.com -> gcm-reports;
// previews -> gcm-reports-preview. GET returns only reviewed, active closures/hazards (never legality data).
import { sanitizeReport } from '../../lib/reports.js';
const SUB = 'maxgreenwald-assistant.workers.dev';
export function queueFor(host, env) {
  if (env && env.REPORTS_URL) return env.REPORTS_URL;
  return (host === 'golfcartmap.com' || host === 'www.golfcartmap.com') ? `https://gcm-reports.${SUB}` : `https://gcm-reports-preview.${SUB}`;
}
const J = (o, s) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
export async function onRequestPost({ request, env }) {
  let r; try { const t = await request.text(); if (t.length > 4000) return J({ ok: false }, 413); r = sanitizeReport(JSON.parse(t)) } catch (_) { r = null }
  if (!r) return J({ ok: false, error: 'bad report' }, 400);
  try { const f = await fetch(queueFor(new URL(request.url).hostname, env) + '/r', { method: 'POST', body: JSON.stringify(r), headers: { 'content-type': 'application/json' } });
    if (!f.ok) return J({ ok: false }, 502); const j = await f.json(); return J({ ok: true, id: j.id, status: 'pending' }, 202) } catch (_) { return J({ ok: false }, 502) }
}
export async function onRequestGet({ request, env }) {
  try { const f = await fetch(queueFor(new URL(request.url).hostname, env) + '/active'); if (!f.ok) throw 0;
    return new Response(await f.text(), { headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=300' } }) } catch (_) { return J([], 200) }
}
