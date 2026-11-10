// Shop activity for the partner admin. Same exclusion as /stats (lib/analytics_exclude.js):
// denylisted install ids, internal/test/simulator traffic, and test UTMs are left out.
// Counts only events whose props.shop is this shop. No install ids in the result.
import { denylistJson, rowIsInternalSql } from './analytics_exclude.js';

const SHOP = /^[a-z][a-z0-9-]{1,47}$/;
const SIGNAL = rowIsInternalSql('props');

function queries(deny) {
  const withEx = body => `WITH excluded(iid) AS (
      SELECT iid FROM events WHERE iid IS NOT NULL AND ${SIGNAL}
      UNION SELECT value FROM json_each(?)
    ) ${body}`;
  const F = `AND (iid IS NULL OR iid NOT IN (SELECT iid FROM excluded)) AND NOT ${SIGNAL}`;
  return {
    run(q, body, ...params) { return q(withEx(body), deny, ...params); },
    F,
  };
}

/**
 * Aggregates for one shop slug. Throws on a bad slug (callers return 400).
 * q(sql, ...params) => rows, same shape as the analytics Durable Object.
 */
export function computeShopStats(q, { shop, days = 30, now = Date.now(), extraIids } = {}) {
  const slug = String(shop || '').trim().toLowerCase();
  if (!SHOP.test(slug)) throw new Error('bad shop');
  const n = Math.min(400, Math.max(1, Math.floor(Number(days) || 30)));
  const deny = denylistJson(extraIids);
  const { run, F } = queries(deny);
  const since = new Date(now - (n - 1) * 864e5).toISOString().slice(0, 10);
  const one = rows => (rows && rows[0]) || {};
  const where = `day>=? AND json_extract(props,'$.shop')=? ${F}`;
  const totals = one(run(q, `SELECT
      SUM(event='partner_unlock') unlocks,
      SUM(event='experience_started') started,
      SUM(event='experience_finished') finished,
      SUM(event='affiliate_tap') affiliate_taps
    FROM events WHERE ${where}`, since, slug));
  return {
    shop: slug,
    days: n,
    generated: new Date(now).toISOString(),
    timezone: 'UTC days',
    filter: 'internal-test-excluded',
    totals: {
      unlocks: totals.unlocks || 0,
      started: totals.started || 0,
      finished: totals.finished || 0,
      affiliate_taps: totals.affiliate_taps || 0,
    },
    daily: run(q, `SELECT day,
        SUM(event='partner_unlock') unlocks,
        SUM(event='experience_started') started,
        SUM(event='experience_finished') finished,
        SUM(event='affiliate_tap') affiliate_taps
      FROM events WHERE ${where} GROUP BY day ORDER BY day DESC`, since, slug),
    codes: run(q, `SELECT COALESCE(json_extract(props,'$.code'),'') code, COUNT(*) unlocks
      FROM events WHERE ${where} AND event='partner_unlock'
      GROUP BY 1 ORDER BY unlocks DESC`, since, slug),
    rides: run(q, `SELECT COALESCE(json_extract(props,'$.ride'),'') ride,
        SUM(event='experience_started') started,
        SUM(event='experience_finished') finished
      FROM events WHERE ${where} AND event IN ('experience_started','experience_finished')
      GROUP BY 1 ORDER BY started DESC`, since, slug),
    pins: run(q, `SELECT COALESCE(json_extract(props,'$.pin'),'') pin, COUNT(*) taps
      FROM events WHERE ${where} AND event='affiliate_tap'
      GROUP BY 1 ORDER BY taps DESC`, since, slug),
  };
}

/** URL + header for the analytics Worker, or null when the stats key is not set. */
export function shopStatsRequest(base, key, shop, days) {
  if (!base || !key) return null;
  const slug = String(shop || '').trim().toLowerCase();
  if (!SHOP.test(slug)) return null;
  const n = Math.min(400, Math.max(1, Math.floor(Number(days) || 30)));
  const root = String(base).replace(/\/$/, '').replace(/\/(shop-stats|stats)$/, '');
  return {
    url: `${root}/shop-stats?shop=${encodeURIComponent(slug)}&days=${n}`,
    headers: { 'x-stats-key': key },
  };
}

/** What the partner admin reads. Never forwards another shop's payload. */
export async function fetchShopStats(fetchImpl, { base, key, shop, days }) {
  const slug = String(shop || '').trim().toLowerCase();
  const n = Math.min(400, Math.max(1, Math.floor(Number(days) || 30)));
  const req = shopStatsRequest(base, key, slug, n);
  if (!req) return { ready: false, shop: slug, days: n, reason: key ? 'bad shop' : 'not_configured' };
  let r;
  try { r = await fetchImpl(req.url, { headers: req.headers }); }
  catch { return { ready: false, shop: slug, days: n, reason: 'unavailable' }; }
  if (!r || !r.ok) return { ready: false, shop: slug, days: n, reason: 'unavailable' };
  let j = {};
  try { j = await r.json(); } catch { return { ready: false, shop: slug, days: n, reason: 'unavailable' }; }
  if (!j || j.shop !== slug || j.error) return { ready: false, shop: slug, days: n, reason: 'unavailable' };
  return { ready: true, ...j };
}
