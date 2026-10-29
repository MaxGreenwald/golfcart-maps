// Published /stats aggregates. Internal, test, simulator, and denylisted installs are omitted
// from every count the scorecard prints. weekly_active_unfiltered is the pre-filter number
// so a reader can see what was removed. See lib/analytics_exclude.js.
import { denylistJson, rowIsInternalSql, INTERNAL_CHANNELS } from './analytics_exclude.js';

const SIGNAL = rowIsInternalSql('props');
const INTERNAL_IN = INTERNAL_CHANNELS.map(s => `'${s}'`).join(',');

function queries(deny) {
  const withEx = body => `WITH excluded(iid) AS (
      SELECT iid FROM events WHERE iid IS NOT NULL AND ${SIGNAL}
      UNION SELECT value FROM json_each(?)
    ) ${body}`;
  const F = `AND (iid IS NULL OR iid NOT IN (SELECT iid FROM excluded)) AND NOT ${SIGNAL}`;
  return {
    // First bound param is always the denylist JSON (json_each in the CTE).
    run(q, body, ...params) { return q(withEx(body), deny, ...params); },
    F,
  };
}

export function computeStats(q, days, now, opts = {}) {
  const deny = denylistJson(opts.extraIids);
  const { run, F } = queries(deny);
  const since = new Date(now - (days - 1) * 864e5).toISOString().slice(0, 10);
  const wk = new Date(now - 6 * 864e5).toISOString().slice(0, 10);
  const one = (rows) => (rows && rows[0]) || {};
  const weekly = (where) => one(run(q, `SELECT COUNT(DISTINCT iid) installs FROM events WHERE ${where} ${F}`, wk)).installs || 0;
  const weeklyRaw = (where) => one(q(`SELECT COUNT(DISTINCT iid) installs FROM events WHERE ${where}`, wk)).installs || 0;
  const weeklyActive = weekly('day>=?');
  const weeklyActiveRaw = weeklyRaw('day>=?');
  const routeUsers = weekly(`day>=? AND event='route_searched'`);
  const routeUsersRaw = weeklyRaw(`day>=? AND event='route_searched'`);
  const reasons = run(q, `SELECT CASE
        WHEN iid IN (SELECT value FROM json_each(?)) THEN 'iid'
        WHEN EXISTS (SELECT 1 FROM events e2 WHERE e2.iid = events.iid AND lower(COALESCE(json_extract(e2.props,'$.internal'),'')) IN (${INTERNAL_IN})) THEN 'internal'
        ELSE 'utm' END reason,
      COUNT(DISTINCT iid) installs
    FROM events WHERE day>=? AND iid IS NOT NULL AND iid IN (SELECT iid FROM excluded)
    GROUP BY 1 ORDER BY installs DESC`, deny, wk);
  return {
    days, generated: new Date(now).toISOString(), timezone: 'UTC days',
    filter: 'internal-test-excluded',
    weekly_active: weeklyActive,
    weekly_active_route_users: routeUsers,
    weekly_active_unfiltered: weeklyActiveRaw,
    weekly_active_route_users_unfiltered: routeUsersRaw,
    excluded: {
      weekly_active: weeklyActiveRaw - weeklyActive,
      weekly_active_route_users: routeUsersRaw - routeUsers,
      by_reason: reasons,
    },
    totals: one(run(q, `SELECT COUNT(DISTINCT iid) installs, SUM(event='session') sessions, COUNT(*) events FROM events WHERE day>=? ${F}`, since)),
    daily: run(q, `SELECT day, COUNT(DISTINCT iid) active_installs, SUM(event='session') sessions, SUM(event='town_viewed') town_views,
        SUM(event='route_searched') routes_searched, SUM(event='route_searched' AND json_extract(props,'$.ok')=1) routes_found,
        SUM(event='route_completed') routes_completed, SUM(event='road_report_filed') road_reports,
        SUM(event='session' AND json_extract(props,'$.new_install')=1) new_installs
      FROM events WHERE day>=? ${F} GROUP BY day ORDER BY day DESC`, since),
    events: run(q, `SELECT event, COUNT(*) n, COUNT(DISTINCT iid) installs FROM events WHERE day>=? ${F} GROUP BY event ORDER BY n DESC`, since),
    towns: run(q, `SELECT town, COUNT(DISTINCT iid) installs, SUM(event='town_viewed') views, SUM(event='route_searched') routes_searched, SUM(event='route_completed') routes_completed, SUM(event='road_report_filed') road_reports
      FROM events WHERE day>=? AND town IS NOT NULL ${F} GROUP BY town ORDER BY installs DESC LIMIT 50`, since),
    platforms: run(q, `SELECT platform, pwa, COUNT(DISTINCT iid) installs, SUM(event='session') sessions FROM events WHERE day>=? ${F} GROUP BY platform, pwa ORDER BY installs DESC`, since),
    sources: run(q, `SELECT COALESCE(json_extract(props,'$.utm_source'),'(none)') utm_source, COALESCE(json_extract(props,'$.utm_medium'),'') utm_medium,
        COALESCE(json_extract(props,'$.utm_campaign'),'') utm_campaign, COUNT(*) sessions, COUNT(DISTINCT iid) installs
      FROM events WHERE day>=? AND event='session' ${F} GROUP BY 1,2,3 ORDER BY sessions DESC LIMIT 30`, since),
    referrers: run(q, `SELECT COALESCE(json_extract(props,'$.ref'),'(direct)') ref, COUNT(*) sessions FROM events WHERE day>=? AND event='session' ${F} GROUP BY 1 ORDER BY sessions DESC LIMIT 20`, since),
    first_touch: run(q, `SELECT COALESCE(json_extract(props,'$.ft_source'),'(none)') ft_source, COUNT(DISTINCT iid) installs FROM events WHERE day>=? AND event='session' ${F} GROUP BY 1 ORDER BY installs DESC LIMIT 20`, since),
  };
}
