// Renter email from the partner Worker goes through the existing gcm-mailer Worker (POST /send,
// Bearer MAILER_KEY). Off unless all three are set on the partner Worker:
//   MAILER_URL   var, e.g. https://gcm-mailer.maxgreenwald-assistant.workers.dev
//   MAILER_KEY   secret, same value as gcm-mailer's MAILER_KEY
//   RENTER_EMAIL var, "on" (Max turns renter email on; anything else keeps it off)
// While off, nothing is sent and callers record status "off".

export function mailState(env) {
  const e = env || {};
  if (String(e.RENTER_EMAIL || '').toLowerCase() !== 'on') return { on: false, reason: 'Renter email is off for now.' };
  if (!e.MAILER_URL || !e.MAILER_KEY) return { on: false, reason: 'Renter email is not set up yet.' };
  return { on: true };
}

const ADDR = /^[^\s@<>,;"]+@[^\s@<>,;"]+\.[^\s@<>,;"]+$/;
export function cleanEmail(v) {
  const s = String(v ?? '').trim().toLowerCase();
  return s.length <= 254 && ADDR.test(s) ? s : '';
}

/**
 * Send one message. msg: { to, subject, html, text, reply_to }.
 * Returns { status: 'sent' } | { status: 'off', reason } | { status: 'failed', error }.
 * Never throws and never returns the key.
 */
export async function sendMail(env, msg, fetchImpl = globalThis.fetch) {
  const st = mailState(env);
  if (!st.on) return { status: 'off', reason: st.reason };
  const to = cleanEmail(msg && msg.to);
  if (!to) return { status: 'failed', error: 'bad address' };
  const body = { to: [to], subject: String(msg.subject || ''), html: String(msg.html || ''), text: String(msg.text || '') };
  const reply = cleanEmail(msg.reply_to);
  if (reply) body.reply_to = [reply];
  let r;
  try {
    r = await fetchImpl(String(env.MAILER_URL).replace(/\/$/, '') + '/send', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + env.MAILER_KEY },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return { status: 'failed', error: 'mailer unreachable' };
  }
  let j = {};
  try { j = await r.json(); } catch { j = {}; }
  if (!r.ok || !j.ok) return { status: 'failed', error: 'mailer said ' + r.status };
  return { status: 'sent' };
}
