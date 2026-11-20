// Renter text messages. There is no SMS provider yet, so every provider here is disabled and
// nothing is ever sent. A real provider implements the same shape and is picked by SMS_PROVIDER:
//   { name, enabled: true, async send({ to, text }) -> { status: 'sent' } | { status: 'failed', error } }
// Until then smsProvider() returns the disabled stub and callers record status "off".

const DISABLED = Object.freeze({
  name: 'none',
  enabled: false,
  reason: 'Text messages are not set up yet.',
  async send() { return { status: 'off', reason: 'Text messages are not set up yet.' }; },
});

export const SMS_PROVIDERS = Object.freeze({});

export function smsProvider(env) {
  const want = String((env && env.SMS_PROVIDER) || '').trim().toLowerCase();
  const p = want && SMS_PROVIDERS[want];
  return p && p.enabled ? p : DISABLED;
}

/** Send a text through the configured provider, or record that texts are off. Never throws. */
export async function sendSms(env, msg) {
  const p = smsProvider(env);
  if (!p.enabled) return { status: 'off', reason: p.reason };
  try { return await p.send(msg); } catch (e) { return { status: 'failed', error: 'sms provider error' }; }
}
