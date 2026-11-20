// Fleet stickers: one renter access code per cart, labeled with the shop's cart number.
// Pure helpers shared by the partner Worker, the admin page, and node tests.

export const FLEET_MAX = 100;
export const CART_LABEL_MAX = 12;
const LABEL = /^[A-Za-z0-9][A-Za-z0-9 #-]{0,11}$/;

/** Clean one cart label ("7", "A12", "Blue 3"). Returns '' when empty or not allowed. */
export function cleanCartLabel(v) {
  const s = String(v ?? '').replace(/\s+/g, ' ').trim().slice(0, CART_LABEL_MAX).trim();
  return LABEL.test(s) ? s : '';
}

/**
 * Parse what a shop types for its fleet: "1-12", "A1-A6", "1, 2, 5, Blue".
 * Returns { carts: [labels in order, no repeats] } or { error }.
 */
export function parseCarts(text) {
  const out = [];
  const seen = new Set();
  const add = label => {
    const key = label.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push(label);
  };
  const parts = String(text ?? '').split(/[,\n;]+/).map(s => s.trim()).filter(Boolean);
  if (!parts.length) return { error: 'Type your cart numbers, like 1-12 or A1, A2, B7' };
  for (const part of parts) {
    const m = /^([A-Za-z#]*)\s*(\d{1,4})\s*-\s*([A-Za-z#]*)\s*(\d{1,4})$/.exec(part);
    if (m && (m[3] === '' || m[3].toLowerCase() === m[1].toLowerCase())) {
      const a = +m[2], b = +m[4];
      if (b < a) return { error: `"${part}" counts down. Write it low to high.` };
      if (b - a + 1 > FLEET_MAX) return { error: `Up to ${FLEET_MAX} carts at a time.` };
      const width = m[2].length > 1 && m[2].startsWith('0') ? m[2].length : 0;
      for (let n = a; n <= b; n++) add(m[1] + String(n).padStart(width, '0'));
    } else {
      const label = cleanCartLabel(part);
      if (!label) return { error: `"${part.slice(0, 20)}" is not a cart number. Use letters, digits, spaces, # or -, up to ${CART_LABEL_MAX} characters.` };
      add(label);
    }
    if (out.length > FLEET_MAX) return { error: `Up to ${FLEET_MAX} carts at a time.` };
  }
  return { carts: out };
}

/**
 * Which carts need a new code. existing: code rows for this shop ({ code, cart_label, expires_at }).
 * A cart keeps its code while that code has not expired, so printing twice gives the same stickers.
 */
export function fleetPlan(carts, existing, nowSec) {
  const live = new Map();
  for (const c of existing || []) {
    const label = cleanCartLabel(c.cart_label);
    if (!label) continue;
    if (c.expires_at && c.expires_at < nowSec) continue;
    const key = label.toLowerCase();
    if (!live.has(key)) live.set(key, c);
  }
  const reuse = [], make = [];
  for (const cart of carts) {
    const hit = live.get(cart.toLowerCase());
    if (hit) reuse.push({ cart, code: hit.code });
    else make.push(cart);
  }
  return { reuse, make };
}

/** Natural sort for cart labels: 2 before 10, A2 before A10. */
export function cartOrder(a, b) {
  return String(a).localeCompare(String(b), 'en', { numeric: true, sensitivity: 'base' });
}
