// Renter problem reports: cart number, what happened, an optional note, contact and photo.
// The shop gets an email and an admin list. Pure, so the Worker and node tests share it.
import { cleanPhone, phoneDisplay, sniffImage } from './partner.js';

export const REPORT_KINDS = {
  damage: 'Damage',
  flat: 'Flat tire',
  wont_start: 'Won\u2019t start',
  battery: 'Battery low',
  accident: 'Accident',
  other: 'Something else',
};
export const REPORT_KEEP_DAYS = 90;
export const REPORTS_PER_CODE_DAY = 5;
const NOTE_MAX = 1000;
const NAME_MAX = 80;

/** Cart number as printed on the cart: letters, digits, space and dash, up to 12. */
export function cleanCart(v) {
  const s = String(v ?? '').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  return /^[0-9A-Za-z][0-9A-Za-z -]{0,11}$/.test(s) ? s : null;
}

/** Clean a renter's report body. Returns { report } or { error }. */
export function cleanReport(body) {
  const b = body && typeof body === 'object' ? body : {};
  const cart = cleanCart(b.cart);
  if (cart === null) return { error: 'Cart number: letters and numbers only, up to 12' };
  const kind = String(b.kind || '');
  if (!Object.hasOwn(REPORT_KINDS, kind)) return { error: 'Pick what happened' };
  const note = String(b.note ?? '').replace(/\r\n?/g, '\n').trim();
  if ([...note].length > NOTE_MAX) return { error: 'Keep the note under 1000 characters' };
  if (kind === 'other' && !note) return { error: 'Tell the shop what happened' };
  const name = String(b.contact_name ?? '').replace(/\s+/g, ' ').trim();
  if ([...name].length > NAME_MAX) return { error: 'Name is too long' };
  const ph = cleanPhone(b.contact_phone == null ? '' : b.contact_phone);
  if (ph.error) return { error: 'Phone must be a 10-digit US number' };
  return { report: { cart, kind, note, contact_name: name, contact_phone: ph.value || '' } };
}

/** Photo bytes check for a report (same 1.5 MB JPEG/PNG/WebP limits as shop photos). */
export function reportPhotoKey(shopId, reportId, bytes) {
  const s = sniffImage(bytes);
  if (s.error) return { error: s.error };
  return { key: 'shops/' + shopId + '/reports/' + reportId + '.' + s.ext, content_type: s.content_type };
}

export function kindLabel(kind) { return REPORT_KINDS[kind] || 'Problem'; }

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** The email to the shop owner. photo: 'saved' | 'failed' | 'none'. */
export function reportEmail({ shop, report, adminLink, photo, when }) {
  const s = shop || {};
  const what = kindLabel(report.kind);
  const cart = report.cart ? 'Cart ' + report.cart : 'A cart (no number given)';
  const subject = `${report.cart ? 'Cart ' + report.cart : 'Cart'}: ${what} reported by a renter`;
  const phone = phoneDisplay(report.contact_phone);
  const photoLine = photo === 'saved' ? 'A photo is attached in the admin.'
    : photo === 'failed' ? 'The renter added a photo, but it could not be saved.'
    : 'No photo.';
  const lines = [
    `${cart}: ${what}`,
    when ? `Reported ${when}` : '',
    `Code ${report.code}`,
    report.note ? `Note: ${report.note}` : '',
    report.contact_name ? `Name: ${report.contact_name}` : '',
    phone ? `Phone: ${phone}` : '',
    photoLine,
    '',
    `See all reports: ${adminLink}`,
  ].filter(Boolean);
  const text = `${s.name || 'Your shop'} got a problem report.\n\n` + lines.join('\n');
  const html = `<!doctype html><html><body style="margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#0b3c50">
<div style="max-width:520px;margin:0 auto;padding:20px">
<h2 style="margin:0 0 12px;font-size:18px">${esc(cart)}: ${esc(what)}</h2>
${when ? `<p style="margin:0 0 6px">Reported ${esc(when)}</p>` : ''}
<p style="margin:0 0 6px">Code <b>${esc(report.code)}</b></p>
${report.note ? `<p style="margin:0 0 6px;white-space:pre-wrap">Note: ${esc(report.note)}</p>` : ''}
${report.contact_name ? `<p style="margin:0 0 6px">Name: ${esc(report.contact_name)}</p>` : ''}
${phone ? `<p style="margin:0 0 6px">Phone: <a href="tel:+1${esc(report.contact_phone)}">${esc(phone)}</a></p>` : ''}
<p style="margin:0 0 16px">${esc(photoLine)}</p>
<p><a href="${esc(adminLink)}" style="display:inline-block;background:#14b8c4;color:#073044;font-weight:800;text-decoration:none;padding:10px 16px;border-radius:10px">Open problem reports</a></p>
</div></body></html>`;
  return { subject, text, html };
}

export function reportRow(r) {
  if (!r) return null;
  return {
    id: r.id, cart: r.cart || '', kind: r.kind, kind_label: kindLabel(r.kind), note: r.note || '',
    contact_name: r.contact_name || '', contact_phone: r.contact_phone || '', code: r.code,
    photo: !!r.photo_key, photo_status: r.photo_status || 'none', mail: r.mail_status || 'pending',
    status: r.status || 'open', created_at: r.created_at, fixed_at: r.fixed_at || null,
  };
}
