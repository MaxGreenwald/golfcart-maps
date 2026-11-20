// Storage for the gcm-analytics Durable Object (SQLite). Shared by the Worker and the tests.
//
// Why this exists: Durable Object SQLite bills every row a query reads, and json_each rows count.
// The old /stats rebuilt the excluded-install list on every query by running the internal/test
// check (a 9-row json_each per event) over every stored event, in 11 of its 13 statements:
// about 125 rows read per stored event per /stats call.
//
// Now the check runs once per event, when it is stored, and the result lives beside the events
// table (the events table itself is unchanged, so an older Worker version can still write to it):
//   internal_rows(rid, iid, channel)  one row per stored event that is internal/test traffic
//   excluded_iids(iid, internal)      every install id that ever sent such an event; internal=1
//                                     when one of them carried props.internal ('internal' reason)
// /stats and /shop-stats read only the events in their day window plus these small tables.
// meta.signal: which version of rowIsInternalSql the stored flags use (a change re-flags everything).
// meta.flagged_through: highest events rowid already checked; on wake, any newer rows that were
// written without a check (for example by a rolled-back Worker) are checked then.
import { rowIsInternalSql, INTERNAL_CHANNELS } from './analytics_exclude.js';

export const SIGNAL_SQL = rowIsInternalSql('props');
const INTERNAL_IN = INTERNAL_CHANNELS.map(s => `'${s}'`).join(',');
const CHANNEL = p => `(lower(COALESCE(json_extract(${p},'$.internal'),'')) IN (${INTERNAL_IN}))`;
export const RETAIN_DAYS = 400;

/** Short stable id for the current internal/test rule, so a rule change triggers a recompute. */
export function signalVersion(sql = SIGNAL_SQL) {
  let h = 2166136261;
  for (let i = 0; i < sql.length; i++) { h ^= sql.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
  return h.toString(16);
}

const setMeta = (exec, k, v) => exec(`INSERT INTO meta(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v`, k, String(v));

/**
 * Create or upgrade the schema and check any events stored without a flag.
 * exec(sql, ...params) runs a statement; q(sql, ...params) returns rows.
 * On an up-to-date store this reads a few rows (meta and the newest rowid).
 */
export function ensureSchema(exec, q) {
  exec(`CREATE TABLE IF NOT EXISTS events(ts INTEGER NOT NULL, day TEXT NOT NULL, event TEXT NOT NULL, town TEXT, platform TEXT, pwa INTEGER, iid TEXT, sid TEXT, props TEXT)`);
  exec('CREATE INDEX IF NOT EXISTS ev_day ON events(day)');
  exec('CREATE INDEX IF NOT EXISTS ev_event_day ON events(event, day)');
  exec('CREATE INDEX IF NOT EXISTS ev_iid ON events(iid)');
  exec(`CREATE TABLE IF NOT EXISTS internal_rows(rid INTEGER PRIMARY KEY, iid TEXT, channel INTEGER NOT NULL DEFAULT 0)`);
  exec('CREATE INDEX IF NOT EXISTS ir_anon ON internal_rows(rid) WHERE iid IS NULL');
  exec(`CREATE TABLE IF NOT EXISTS excluded_iids(iid TEXT PRIMARY KEY, internal INTEGER NOT NULL DEFAULT 0) WITHOUT ROWID`);
  exec(`CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL)`);
  const meta = Object.fromEntries(q(`SELECT k, v FROM meta WHERE k IN ('signal', 'flagged_through')`).map(r => [r.k, r.v]));
  const want = signalVersion();
  if (meta.signal !== want) {
    // First wake after this deploy, or the internal/test rule changed: check every stored event once.
    exec('DELETE FROM internal_rows');
    const top = flagRange(exec, q, 0);
    setMeta(exec, 'signal', want);
    setMeta(exec, 'flagged_through', top);
    return { migrated: true, checked: 'all' };
  }
  const from = Number(meta.flagged_through || 0);
  const newest = (q('SELECT MAX(rowid) m FROM events')[0] || {}).m || 0;
  if (newest > from) {
    flagRange(exec, q, from);
    setMeta(exec, 'flagged_through', newest);
    return { migrated: false, checked: newest - from };
  }
  return { migrated: false, checked: 0 };
}

/** Flag events with rowid > after (rowid range on the primary key), then rebuild excluded_iids. */
function flagRange(exec, q, after) {
  exec(`INSERT OR IGNORE INTO internal_rows(rid, iid, channel)
    SELECT rowid, iid, ${CHANNEL('props')} FROM events WHERE rowid > ? AND ${SIGNAL_SQL}`, after);
  rebuildExcluded(exec);
  return (q('SELECT MAX(rowid) m FROM events')[0] || {}).m || 0;
}

/** excluded_iids from internal_rows (small: only internal/test events). */
export function rebuildExcluded(exec) {
  exec('DELETE FROM excluded_iids');
  exec(`INSERT INTO excluded_iids(iid, internal) SELECT iid, MAX(channel) FROM internal_rows WHERE iid IS NOT NULL GROUP BY iid`);
}

/** Store one sanitized event (lib/analytics.js sanitize output) and its internal/test flag. */
export function insertEvent(q, exec, r, now) {
  const day = new Date(now).toISOString().slice(0, 10);
  const props = JSON.stringify(r.props || {});
  // Same SQL predicate /stats used to evaluate at read time, bound to this event's props (?9).
  const row = q(`INSERT INTO events(ts, day, event, town, platform, pwa, iid, sid, props) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)
    RETURNING rowid AS rid, ${rowIsInternalSql('?9')} AS internal, ${CHANNEL('?9')} AS channel`,
    now, day, r.event, r.town ?? null, r.platform ?? null, r.pwa ?? null, r.iid ?? null, r.sid ?? null, props)[0];
  if (row.internal) {
    exec('INSERT OR IGNORE INTO internal_rows(rid, iid, channel) VALUES(?, ?, ?)', row.rid, r.iid ?? null, row.channel ? 1 : 0);
    if (r.iid) {
      exec(`INSERT INTO excluded_iids(iid, internal) VALUES(?, ?)
        ON CONFLICT(iid) DO UPDATE SET internal=MAX(internal, excluded.internal)`, r.iid, row.channel ? 1 : 0);
    }
  }
  // Advance only over a gap-free run: a row written meanwhile by another Worker version stays
  // unchecked until the next wake (ensureSchema) checks everything after flagged_through.
  exec(`UPDATE meta SET v=? WHERE k='flagged_through' AND v=?`, String(row.rid), String(row.rid - 1));
  return { day, rid: row.rid, internal: row.internal ? 1 : 0 };
}

/** Delete events older than RETAIN_DAYS. Uses the day index, so it reads only the rows it deletes. */
export function purgeOld(q, exec, now) {
  const cut = new Date(now - RETAIN_DAYS * 864e5).toISOString().slice(0, 10);
  const gone = q('DELETE FROM events WHERE day < ? RETURNING rowid AS rid', cut);
  if (!gone.length) return 0;
  const hit = q(`DELETE FROM internal_rows WHERE rid IN (SELECT value FROM json_each(?)) RETURNING rid`, JSON.stringify(gone.map(r => r.rid)));
  if (hit.length) rebuildExcluded(exec);
  return gone.length;
}

/** SQL filter (AND ...) that keeps an events row out of published numbers. Needs the excluded CTE. */
// Events with an install id are judged by the id; the rare events without one, by their own row.
export const KEEP_SQL = `(CASE WHEN iid IS NULL THEN rowid NOT IN (SELECT rid FROM internal_rows WHERE iid IS NULL) ELSE iid NOT IN (SELECT iid FROM excluded) END)`;
