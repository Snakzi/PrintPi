/**
 * What to tell the user when a WebAuthn ceremony fails. The browser throws DOMExceptions
 * with a `name`; the interesting ones are the user backing out, a key that is already
 * registered and a host the browser refuses (plain HTTP or an IP address).
 */
const MESSAGES = {
  NotAllowedError: 'Cancelled or timed out.',
  InvalidStateError: 'This passkey is already registered.',
  NotSupportedError: 'This browser does not support passkeys.',
  SecurityError: 'Passkeys need HTTPS and a hostname, not an IP address.',
  AbortError: null,
};

export function passkeyErrorMessage(error) {
  if (!error) return 'Passkey failed.';
  const name = error.name ?? '';
  if (name in MESSAGES) return MESSAGES[name];
  return error.message || 'Passkey failed.';
}

/** Whether this page may use passkeys at all: a secure context with the WebAuthn API. */
export function passkeysUsable(win = globalThis) {
  return Boolean(win?.isSecureContext && win?.PublicKeyCredential);
}
