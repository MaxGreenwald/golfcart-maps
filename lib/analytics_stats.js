// Published /stats aggregates. Internal, test, simulator, and denylisted installs are omitted
// from every count the scorecard prints. weekly_active_unfiltered is the pre-filter number
// so a reader can see what was removed. See lib/analytics_exclude.js.
// The internal/test check is stored at ingest (events.internal, excluded_iids; lib/analytics_store.js),
// so each query here reads only the events in its day window. tests/analytics_rows.test.mjs pins
// the output to the old read-time SQL (tests/fixtures/analytics_stats_legacy.mjs).
import { denylistJson } from './analytics_exclude.js';

function queries(deny) {
  const withEx = body => `WITH excluded(iid) AS (
      SELECT iid FROM excluded_iids
      UNION SELECT value FROM json_each(?)
    ) ${body}`;
  const keep = `(iid IS NULL OR iid NOT IN (SELECT iid FROM excluded)) AND internal=0`;
  const F = `AND ${keep}`;
  return {
    // First bound param is always the denylist JSON (json_each in the CTE).
    run(q, body, ...params) { return q(withEx(body), deny, ...params); },
    F, keep,
  };
}

export function computeStats(q, days, now, opts = {}) {
  const deny = denylistJson(opts.extraIids);
  const { run, F, keep } = queries(deny);
  const since = new Date(now - (days - 1) * 864e5).toISOString().slice(0, 10);
  const wk = new Date(now - 6 * 864e5).toISOString().slice(0, 10);
  const one = (rows) => (rows && rows[0]) || {};
  // One pass over the 7-day window for all four weekly numbers (filtered and unfiltered).
  const wkRow = one(run(q, `SELECT
      COUNT(DISTINCT CASE WHEN ${keep} THEN iid END) wa,
      COUNT(DISTINCT iid) wa_raw,
      COUNT(DISTINCT CASE WHEN ${keep} AND event='route_searched' THEN iid END) ru,
      COUNT(DISTINCT CASE WHEN event='route_searched' THEN iid END) ru_raw
    FROM events WHERE day>=?`, wk));
  const weeklyActive = wkRow.wa || 0;
  const weeklyActiveRaw = wkRow.wa_raw || 0;
  const routeUsers = wkRow.ru || 0;
  const routeUsersRaw = wkRow.ru_raw || 0;
  // +iid keeps SQLite on the day index; via ev_iid it would read every stored event of each excluded install.
  const reasons = run(q, `SELECT CASE
        WHEN iid IN (SELECT value FROM json_each(?)) THEN 'iid'
        WHEN EXISTS (SELECT 1 FROM excluded_iids x WHERE x.iid = events.iid AND x.internal=1) THEN 'internal'
        ELSE 'utm' END reason,
      COUNT(DISTINCT iid) installs
    FROM events WHERE day>=? AND iid IS NOT NULL AND +iid IN (SELECT iid FROM excluded)
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
    // INDEXED BY: for GROUP BY event SQLite otherwise walks all of ev_event_day (every stored event).
    events: run(q, `SELECT event, COUNT(*) n, COUNT(DISTINCT iid) installs FROM events INDEXED BY ev_day WHERE day>=? ${F} GROUP BY event ORDER BY n DESC, event`, since),
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

/** Read-only top install ids for one town. Stats-key only; never published on /stats. */
export function topIidsByTown(q, days, now, { town, limit = 5 } = {}) {
  if (typeof town !== 'string' || !/^[a-z0-9_-]{1,32}$/.test(town)) throw new Error('bad town');
  const n = Math.min(20, Math.max(1, Number(limit) || 5));
  const since = new Date(now - (days - 1) * 864e5).toISOString().slice(0, 10);
  const rows = q(
    `SELECT iid,
        COUNT(*) AS events,
        SUM(event='route_started') AS route_started,
        SUM(event='route_completed') AS route_completed,
        SUM(event='route_searched') AS route_searched,
        SUM(event='session') AS sessions,
        GROUP_CONCAT(DISTINCT platform) AS platforms
      FROM events
      WHERE day>=? AND town=? AND iid IS NOT NULL
      GROUP BY iid
      ORDER BY route_started DESC, route_completed DESC, events DESC
      LIMIT ?`,
    since, town, n,
  );
  return { town, days, generated: new Date(now).toISOString(), iids: rows };
}
