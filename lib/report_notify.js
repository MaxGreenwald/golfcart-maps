// Email Max when someone files a road/hazard report (gcm-reports Worker -> gcm-mailer -> Zoho, max@ -> max@).
// Rules: notifications go ONLY to NOTIFY_TO (hard-coded, never taken from a report or request); at most one email
// per MIN_GAP_MS (extra reports wait and go out together as one digest); at most MAX_PER_DAY emails a day;
// reports whose notes start with "[automated test]" never notify (test runs can't email Max).
export const NOTIFY_TO = 'max@golfcartmap.com';
export const MIN_GAP_MS = 5 * 60 * 1000;
export const MAX_PER_DAY = 40;
export const DIGEST_MAX = 25;
const LABEL = { wrong_speed: 'Wrong speed limit', allow: 'Should be allowed', block: 'Should be blocked', closed: 'Road closed', hazard: 'Hazard', other: 'Other' };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const isTest = r => /^\s*\[automated test\]/i.test(r?.notes || '');
export const mapLink = r => `https://golfcartmap.com/?lat=${r.lat}&lon=${r.lon}&z=18`;
export const etTime = ts => new Date(ts).toLocaleString('en-US', { timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) + ' ET';
/** When the next email may go out. */
export function nextSendAt(lastSent, now) { return Math.max(now, (lastSent || 0) + MIN_GAP_MS) }
/** Build {subject, html, text} for one or more pending reports (newest last). `more` = pending beyond the digest cap. */
export function buildEmail(rows, { prod = true, more = 0 } = {}) {
  const n = rows.length + more, tag = prod ? '' : '[preview] ';
  const subject = n === 1 ? `${tag}New road report: ${LABEL[rows[0].issue] || rows[0].issue} on ${rows[0].road}` : `${tag}${n} new road reports`;
  const cmd = `python3 scripts/review_reports.py list pending${prod ? ' --prod' : ''}`;
  const item = r => `<li style="margin-bottom:12px"><b>${esc(LABEL[r.issue] || r.issue)}</b>${r.speed ? ` (suggested ${r.speed} mph)` : ''} on ${esc(r.road)}${r.region ? ` (${esc(r.region)})` : ''}<br>`
    + `<a href="${mapLink(r)}">Open on the map</a> · ${esc(etTime(r.ts))}<br>`
    + (r.notes ? `Note: “${esc(r.notes)}”<br>` : 'No note.<br>') + `<span style="color:#666">ID ${esc(r.id)}</span></li>`;
  const html = `<div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;font-size:15px;line-height:1.4">`
    + `<p>${n === 1 ? 'Someone filed a road report' : `${n} road reports came in`} on Golf Cart Maps${prod ? '' : ' (preview site)'}. Nothing on the map changes until it's reviewed.</p>`
    + `<ul style="padding-left:18px">${rows.map(item).join('')}</ul>${more ? `<p>…and ${more} more in the queue.</p>` : ''}`
    + `<p><b>To review:</b> ask Emma, or run <code>${esc(cmd)}</code>, then <code>accept ID</code> / <code>reject ID</code>${prod ? ' with <code>--prod</code>' : ''}. Closures and hazards can get a temporary avoid (up to 14 days); speed and allowed/blocked fixes are made by hand with a source.</p>`
    + `<p style="color:#666;font-size:13px">At most one of these emails every 5 minutes; extra reports are grouped.</p></div>`;
  const text = rows.map(r => `- ${LABEL[r.issue] || r.issue} on ${r.road}${r.region ? ` (${r.region})` : ''}, ${etTime(r.ts)}\n  ${mapLink(r)}\n  ${r.notes ? 'Note: ' + r.notes : 'No note.'}\n  ID ${r.id}`).join('\n')
    + (more ? `\n...and ${more} more.` : '') + `\n\nTo review: ${cmd}`;
  return { subject, html, text };
}
