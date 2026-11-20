// Rental-day bookings: what a shop types when a renter books, and the welcome message
// (map link, local cart rules, return time). Pure, so the Worker and node tests share it.
import roadrule from '../public/roadrule.js';
import { cleanPhone, phoneDisplay } from './partner.js';
import { cleanEmail } from './partner_mail.js';

export const BOOKING_KEEP_DAYS = 30;
const NAME_MAX = 80;

export function validZone(tz) {
  const z = String(tz || '').trim();
  if (!z || z.length > 64) return '';
  try { new Intl.DateTimeFormat('en-US', { timeZone: z }); return z; } catch { return ''; }
}

/**
 * Clean a booking body: { renter_name, email, phone?, return_at (unix seconds), tz, code? }.
 * Returns { booking } or { error }.
 */
export function cleanBooking(body, nowSec) {
  const b = body && typeof body === 'object' ? body : {};
  const name = String(b.renter_name ?? '').replace(/\s+/g, ' ').trim();
  if (!name) return { error: 'Renter name required' };
  if ([...name].length > NAME_MAX) return { error: 'Renter name is too long' };
  const email = cleanEmail(b.email);
  if (!email) return { error: 'A valid renter email is required' };
  const ph = cleanPhone(b.phone == null ? '' : b.phone);
  if (ph.error) return { error: 'Renter phone must be a 10-digit US number' };
  const at = Math.floor(Number(b.return_at));
  if (!Number.isFinite(at)) return { error: 'Return time required' };
  if (at < nowSec - 3600) return { error: 'Return time is in the past' };
  if (at > nowSec + 30 * 86400) return { error: 'Return time must be within 30 days' };
  const tz = validZone(b.tz) || 'America/Los_Angeles';
  const code = String(b.code ?? '').trim().toUpperCase();
  if (code && !/^[0-9A-Z]{3,16}$/.test(code)) return { error: 'Pick one of your access codes' };
  return { booking: { renter_name: name, email, phone: ph.value || '', return_at: at, tz, code } };
}

/** "5:00 PM, Thu Nov 19" in the shop's time zone. */
export function returnLabel(at, tz) {
  const d = new Date(Number(at) * 1000);
  const zone = validZone(tz) || 'America/Los_Angeles';
  const time = new Intl.DateTimeFormat('en-US', { timeZone: zone, hour: 'numeric', minute: '2-digit' }).format(d);
  const day = new Intl.DateTimeFormat('en-US', { timeZone: zone, weekday: 'short', month: 'short', day: 'numeric' }).format(d).replace(',', '');
  return time + ', ' + day;
}

/** Local cart rules in plain words, from the same road-rule module the map uses. */
export function rulesLines({ rules, region, vehicle, shopRules }) {
  const out = [];
  const known = !!(rules && region && rules[region.state]);
  const R = known ? roadrule.ruleFor(rules, region, vehicle === 'lsv' ? 'lsv' : 'golf_cart') : {};
  const who = vehicle === 'lsv' ? 'Street-legal LSVs' : 'Golf carts';
  if (!known) out.push('Stay on the green roads on the map. They are the legal ones for your cart.');
  else if (R.not_street_legal) out.push('Plain golf carts are not allowed on public roads here. Stay on cart paths.');
  else if (+R.max_posted > 0) out.push(`${who} may drive on roads posted ${+R.max_posted} mph or less. The green roads on the map are the legal ones.`);
  if (R.designated_only) out.push('Only designated cart routes and cart paths are allowed.');
  if (R.daylight_only) out.push('Drive in daylight only.');
  const own = String(shopRules || '').trim();
  if (own) out.push('From the shop: ' + own);
  out.push('Posted signs always take precedence. This is not legal advice.');
  return out;
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function hex(c) { return /^#[0-9a-f]{6}$/i.test(String(c || '')) ? c : '#14b8c4'; }

/**
 * Welcome email: { subject, html, text }.
 * shop: { name, color, rental: { pickup, return_spot, phone } }, booking from cleanBooking, link: renter URL.
 */
export function welcomeEmail({ shop, booking, link, rules }) {
  const s = shop || {};
  const r = s.rental || {};
  const first = String(booking.renter_name).split(' ')[0];
  const when = returnLabel(booking.return_at, booking.tz);
  const shopName = String(s.name || 'Your rental shop');
  const phone = phoneDisplay(r.phone) || String(r.phone || '').trim();
  const lines = rules || [];
  const subject = `Your ${shopName} cart map and return time`;
  const text = [
    `Hi ${first},`,
    '',
    `Here is your ${shopName} map. It shows the roads your cart can use, the shop's rides, and a route back.`,
    link,
    '',
    `Return by ${when}.`,
    r.return_spot ? `Return spot: ${r.return_spot}` : '',
    r.pickup ? `Pickup: ${r.pickup}` : '',
    phone ? `Shop phone: ${phone}` : '',
    '',
    'Local cart rules:',
    ...lines.map(l => '- ' + l),
    '',
    `Have a great ride. ${shopName}`,
  ].filter((l, i, a) => !(l === '' && a[i - 1] === '')).join('\n');
  const c = hex(s.color);
  const html = `<!doctype html><html><body style="margin:0;background:#eef6f7;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#0b3c50">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden" cellspacing="0" cellpadding="0">
<tr><td style="background:${c};padding:16px 20px;color:#073044;font-weight:800;font-size:18px">${esc(shopName)}</td></tr>
<tr><td style="padding:20px">
<p style="margin:0 0 12px;font-size:16px">Hi ${esc(first)},</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.45">Here is your ${esc(shopName)} map. It shows the roads your cart can use, the shop's rides, and a route back.</p>
<p style="margin:0 0 18px"><a href="${esc(link)}" style="display:inline-block;background:${c};color:#073044;font-weight:800;text-decoration:none;padding:12px 18px;border-radius:12px">Open your cart map</a></p>
<p style="margin:0 0 6px;font-size:16px;font-weight:800">Return by ${esc(when)}</p>
${r.return_spot ? `<p style="margin:0 0 6px;font-size:14px">Return spot: ${esc(r.return_spot)}</p>` : ''}
${r.pickup ? `<p style="margin:0 0 6px;font-size:14px">Pickup: ${esc(r.pickup)}</p>` : ''}
${phone ? `<p style="margin:0 0 6px;font-size:14px">Shop phone: ${esc(phone)}</p>` : ''}
<h3 style="margin:18px 0 8px;font-size:15px">Local cart rules</h3>
<ul style="margin:0;padding-left:20px;font-size:14px;line-height:1.45">${lines.map(l => `<li>${esc(l)}</li>`).join('')}</ul>
<p style="margin:18px 0 0;font-size:12px;color:#3e6270">If the button does not work, open ${esc(link)}</p>
</td></tr></table></td></tr></table></body></html>`;
  return { subject, html, text };
}

/** The same welcome as one text message, for when an SMS provider exists. */
export function welcomeSms({ shop, booking, link }) {
  const name = String((shop && shop.name) || 'Your rental shop');
  return `${name}: your cart map ${link} . Return by ${returnLabel(booking.return_at, booking.tz)}. Green roads are legal for your cart. Posted signs always take precedence.`;
}

/** Row for the admin list. Contact details stay; nothing else about the renter is kept. */
export function bookingRow(r) {
  if (!r) return null;
  return {
    id: r.id, renter_name: r.renter_name, email: r.email, phone: r.phone || '',
    return_at: r.return_at, tz: r.tz, code: r.code,
    welcome: r.welcome_status || 'pending', welcome_at: r.welcome_at || null,
    sms: r.sms_status || 'off', created_at: r.created_at,
    remind_at: r.remind_at || null, remind: r.remind_status || 'none', reminded_at: r.reminded_at || null,
  };
}

// ---- Return-time reminders ("head back soon") ----

/** Minutes before the return time that the shop wants renters nudged. */
export const REMIND_CHOICES = [10, 15, 20, 30, 45, 60];
export const DEFAULT_REMIND_MIN = 15;
/** A reminder that comes due more than this long after the return time is dropped, not sent late. */
export const REMIND_LATE_SEC = 3600;

/** { skip } when not sent, { value } for a listed choice, { error } otherwise. */
export function cleanRemindMin(v) {
  if (v === undefined || v === null || v === '') return { skip: true };
  const n = Number(v);
  if (!REMIND_CHOICES.includes(n)) return { error: 'Reminder must be ' + REMIND_CHOICES.join(', ') + ' minutes before return' };
  return { value: n };
}

export function remindMinutes(shop) {
  const n = Number(shop && shop.remind_min);
  return REMIND_CHOICES.includes(n) ? n : DEFAULT_REMIND_MIN;
}

/** Unix seconds when the "head back soon" email goes out. */
export function remindAt(returnAt, minutes) {
  return Math.floor(Number(returnAt)) - (REMIND_CHOICES.includes(Number(minutes)) ? Number(minutes) : DEFAULT_REMIND_MIN) * 60;
}

/** What a due reminder does: send, or drop when it is far past the return time. */
export function reminderAction(row, nowSec) {
  if (!row || row.remind_status !== 'scheduled') return 'none';
  if (Number(row.remind_at) > nowSec) return 'wait';
  if (nowSec > Number(row.return_at) + REMIND_LATE_SEC) return 'late';
  return 'send';
}

/** The renter page link that opens straight to the route back. */
export function backLink(origin, slug, code) {
  return String(origin || '').replace(/\/+$/, '') + '/p/' + encodeURIComponent(slug) + '/go?code=' + encodeURIComponent(code) + '&back=1';
}

export function reminderEmail({ shop, booking, link, minutes }) {
  const s = shop || {};
  const r = s.rental || {};
  const first = String(booking.renter_name).split(' ')[0];
  const when = returnLabel(booking.return_at, booking.tz);
  const time = when.split(',')[0];
  const shopName = String(s.name || 'Your rental shop');
  const phone = phoneDisplay(r.phone) || String(r.phone || '').trim();
  const pinned = Number.isFinite(Number(s.return_lat)) && Number.isFinite(Number(s.return_lon)) && s.return_lat !== null && s.return_lon !== null;
  const mins = Number(minutes) > 0 ? Number(minutes) : DEFAULT_REMIND_MIN;
  const subject = `Head back soon: your ${shopName} cart is due at ${time}`;
  const routeLine = pinned
    ? 'Tap the button for a route back to the shop on roads your cart can use.'
    : 'Open your map to see the roads your cart can use on the way back.';
  const text = [
    `Hi ${first},`,
    '',
    `Your cart is due back in about ${mins} minutes, at ${when}.`,
    routeLine,
    link,
    '',
    r.return_spot ? `Return spot: ${r.return_spot}` : '',
    phone ? `Running late? Call the shop: ${phone}` : '',
    '',
    `Thanks for riding with ${shopName}.`,
  ].filter((l, i, a) => !(l === '' && a[i - 1] === '')).join('\n');
  const c = hex(s.color);
  const html = `<!doctype html><html><body style="margin:0;background:#eef6f7;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#0b3c50">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden" cellspacing="0" cellpadding="0">
<tr><td style="background:${c};padding:16px 20px;color:#073044;font-weight:800;font-size:18px">${esc(shopName)}</td></tr>
<tr><td style="padding:20px">
<p style="margin:0 0 12px;font-size:16px">Hi ${esc(first)},</p>
<p style="margin:0 0 6px;font-size:18px;font-weight:800">Head back soon</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.45">Your cart is due back in about ${mins} minutes, at ${esc(when)}. ${esc(routeLine)}</p>
<p style="margin:0 0 18px"><a href="${esc(link)}" style="display:inline-block;background:${c};color:#073044;font-weight:800;text-decoration:none;padding:12px 18px;border-radius:12px">${pinned ? 'Route me back' : 'Open your cart map'}</a></p>
${r.return_spot ? `<p style="margin:0 0 6px;font-size:14px">Return spot: ${esc(r.return_spot)}</p>` : ''}
${phone ? `<p style="margin:0 0 6px;font-size:14px">Running late? Call the shop: ${esc(phone)}</p>` : ''}
<p style="margin:18px 0 0;font-size:12px;color:#3e6270">If the button does not work, open ${esc(link)}</p>
</td></tr></table></td></tr></table></body></html>`;
  return { subject, html, text };
}
