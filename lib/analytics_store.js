// Storage for the gcm-analytics Durable Object (SQLite). Shared by the Worker and the tests.
//
// Why this exists: Durable Object SQLite bills every row a query reads, and json_each counts.
// The old /stats rebuilt the excluded-install list on every query by running the internal/test
// check (a 9-row json_each per event) over the whole events table, 13 times per request.
// About 127 rows read per stored event per /stats call; 15k events was ~2M rows per call.
//
// Now the check runs once, when an event is stored:
//   events.internal      1 when this event alone is internal/test traffic (same SQL as before)
//   excluded_iids        every install id that ever sent such an event; internal=1 when one of
//                        them carried props.internal (the 'internal' reason on /stats)
// /stats and /shop-stats read only the events in their day window (day index) plus this table.
// meta.signal records which version of rowIsInternalSql the stored flags were computed with.
// When lib/analytics_exclude.js changes, the next wake recomputes the flags, writing only the
// rows whose flag changed.
import { rowIsInternalSql, INTERNAL_CHANNELS } from './analytics_exclude.js';

export const SIGNAL_SQL = rowIsInternalSql('props');
const INTERNAL_IN = INTERNAL_CHANNELS.map(s => `'${s}'`).join(',');
const CHANNEL = p => `lower(COALESCE(json_extract(${p},'$.internal'),'')) IN (${INTERNAL_IN})`;
export const RETAIN_DAYS = 400;

const COLS = 'ts, day, event, town, platform, pwa, iid, sid, props, internal';

/** Short stable id for the current internal/test rule, so a rule change triggers a recompute. */
export function signalVersion(sql = SIGNAL_SQL) {
  let h = 2166136261;
  for (let i = 0; i < sql.length; i++) { h ^= sql.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h.toString(16);
}

/**
 * Create or upgrade the schema. exec(sql, ...params) runs a statement; q(sql, ...params) returns rows.
 * Safe to run on every wake: on an up-to-date store it reads one meta row.
 */
export function ensureSchema(exec, q) {
  exec(`CREATE TABLE IF NOT EXISTS events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT, internal INTEGER NOT NULL DEFAULT 0)`);
  exec(`CREATE TABLE IF NOT EXISTS excluded_iids(iid TEXT PRIMARY KEY, internal INTEGER NOT NULL DEFAULT 0) WITHOUT ROWID`);
  exec(`CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL)`);
  const want = signalVersion();
  const have = (q(`SELECT v FROM meta WHERE k='signal'`)[0] || {}).v;
  if (have === want) return { migrated: false };
  // First wake after this deploy, or the internal/test rule changed.
  const cols = q('PRAGMA table_info(events)').map(c => c.name);
  if (!cols.includes('internal')) exec('ALTER TABLE events ADD COLUMN internal INTEGER NOT NULL DEFAULT 0');
  exec('CREATE INDEX IF NOT EXISTS ev_day ON events(day)');
  exec('CREATE INDEX IF NOT EXISTS ev_event_day ON events(event, day)');
  exec('CREATE INDEX IF NOT EXISTS ev_iid ON events(iid)');
  exec('CREATE INDEX IF NOT EXISTS ev_internal_iid ON events(iid) WHERE internal=1');
  refreshFlags(exec);
  exec(`INSERT INTO meta(k, v) VALUES('signal', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v`, want);
  return { migrated: true };
}

/** Recompute events.internal with the current rule, then excluded_iids. Writes only rows whose flag changes
 * (row writes are billed too). Reads every event once, so it runs only when the rule version changes. */
export function refreshFlags(exec) {
  exec(`UPDATE events SET internal=0 WHERE internal=1 AND NOT ${SIGNAL_SQL}`);
  exec(`UPDATE events SET internal=1 WHERE internal=0 AND ${SIGNAL_SQL}`);
  rebuildExcluded(exec);
}

/** excluded_iids from the flagged events (reads only flagged rows, via ev_internal_iid). */
export function rebuildExcluded(exec) {
  exec('DELETE FROM excluded_iids');
  exec(`INSERT INTO excluded_iids(iid, internal)
    SELECT iid, MAX(${CHANNEL('props')}) FROM events WHERE internal=1 AND iid IS NOT NULL GROUP BY iid`);
}

/** Store one sanitized event (lib/analytics.js sanitize output). */
export function insertEvent(q, exec, r, now) {
  const day = new Date(now).toISOString().slice(0, 10);
  const props = JSON.stringify(r.props || {});
  // The flag uses the same SQL predicate /stats used to evaluate at read time, bound to ?9.
  const row = q(`INSERT INTO events(${COLS}) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9, ${rowIsInternalSql('?9')})
    RETURNING internal, ${CHANNEL('?9')} AS channel`, now, day, r.event, r.town ?? null, r.platform ?? null, r.pwa ?? null, r.iid ?? null, r.sid ?? null, props)[0];
  if (row && row.internal && r.iid) {
    exec(`INSERT INTO excluded_iids(iid, internal) VALUES(?, ?)
      ON CONFLICT(iid) DO UPDATE SET internal=MAX(internal, excluded.internal)`, r.iid, row.channel ? 1 : 0);
  }
  return { day, internal: row ? row.internal : 0 };
}

/** Delete events older than RETAIN_DAYS. Uses the day index, so it reads only the rows it deletes. */
export function purgeOld(q, exec, now) {
  const cut = new Date(now - RETAIN_DAYS * 864e5).toISOString().slice(0, 10);
  const gone = q('DELETE FROM events WHERE day < ? RETURNING internal', cut);
  if (gone.some(r => r.internal)) rebuildExcluded(exec);
  return gone.length;
}
