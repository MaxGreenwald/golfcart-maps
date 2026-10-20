// Road and hazard reports: one shared schema for the app form, /api/report, the gcm-reports Worker and the tests.
// TOP-OF-PYRAMID RULES (enforced here, tested in tests/reports.test.mjs):
//  1. Reports NEVER change legality data. Nothing in this module returns speed limits, road classes or allow/block
//     decisions, and no data build script (scripts/build_*.py, overrides.py) reads the queue. A "wrong speed" or
//     "should be allowed" report only becomes a data change when a person edits scripts/overrides.py with a source.
//  2. Routing only steers around a report after a person reviews it AND gives it a short expiry (temporary closures
//     and hazards). Unreviewed reports have no effect on anyone's map.
//  3. Stored: issue type, road name, coordinates, region, optional suggested speed, short notes, app version.
//     Never stored: IP address, user agent, emails, names, install/session ids.
export const ISSUES = ['wrong_speed', 'allow', 'block', 'closed', 'hazard', 'other'];
export const AVOIDABLE = ['closed', 'hazard'];          // only these can ever become a temporary routing avoid
export const MAX_AVOID_DAYS = 14;
const REGION = /^[a-z0-9]{1,20}$/;
const clean = (v, n) => typeof v === 'string' ? v.replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, n) : '';
const num = (v, lo, hi) => { const n = +v; return Number.isFinite(n) && n >= lo && n <= hi ? n : null };
/** Clean an incoming report; returns null if unusable. */
export function sanitizeReport(b) {
  if (!b || typeof b !== 'object') return null;
  const issue = ISSUES.includes(b.issue) ? b.issue : null, lat = num(b.lat, -90, 90), lon = num(b.lon, -180, 180);
  if (!issue || lat == null || lon == null) return null;
  const region = typeof b.region === 'string' && REGION.test(b.region) ? b.region : null;
  // notes: drop anything that looks like an email or phone number (we never want contact details in the queue)
  const notes = clean(b.notes, 500).replace(/[^\s@]+@[^\s@]+\.[^\s@]+/g, '[email removed]').replace(/\+?\d[\d ().-]{7,}\d/g, '[number removed]');
  const sp = num(b.speed, 5, 70);
  return { issue, lat: +lat.toFixed(5), lon: +lon.toFixed(5), region, road: clean(b.road, 120) || '(not a specific road)',
    speed: sp == null ? null : Math.round(sp), notes, app: clean(b.app, 30) || null };
}
/** A new queue row: always pending, never active. */
export function queued(r, now, id) { return { ...r, id, ts: now, status: 'pending', reviewed_at: null, avoid_until: null, review_note: null } }
/** Apply a reviewer's decision. Only status / temporary avoid can change; the report's facts never do. */
export function review(row, d, now) {
  if (!row || !d) throw new Error('bad review');
  const status = ['accepted', 'rejected', 'fixed'].includes(d.status) ? d.status : null; if (!status) throw new Error('bad status');
  let avoid_until = null;
  if (d.avoid_days != null) {
    if (status !== 'accepted') throw new Error('avoid needs accepted');
    if (!AVOIDABLE.includes(row.issue)) throw new Error('only closures/hazards can be avoided');
    const days = num(d.avoid_days, 0.04, MAX_AVOID_DAYS); if (days == null) throw new Error('avoid_days 1h..' + MAX_AVOID_DAYS + 'd');
    avoid_until = now + Math.round(days * 86400000);
  }
  return { ...row, status, reviewed_at: now, avoid_until, review_note: clean(d.note, 200) || null };
}
/** What the app may use: reviewed, accepted, avoidable, unexpired. Points only, nothing about legality. */
export function activeAvoids(rows, now) {
  return (rows || []).filter(r => r && r.status === 'accepted' && r.reviewed_at && AVOIDABLE.includes(r.issue) && r.avoid_until && r.avoid_until > now && r.avoid_until - (r.reviewed_at || 0) <= MAX_AVOID_DAYS * 86400000 + 1)
    .map(r => ({ id: r.id, issue: r.issue, lat: r.lat, lon: r.lon, road: r.road, until: r.avoid_until }));
}
