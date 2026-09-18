import assert from 'node:assert/strict';
import { test } from 'node:test';
import { passkeyErrorMessage, passkeysUsable } from './errors.js';

test('known DOMException names get their own wording', () => {
  assert.equal(passkeyErrorMessage({ name: 'NotAllowedError', message: 'x' }), 'Cancelled or timed out.');
  assert.equal(passkeyErrorMessage({ name: 'InvalidStateError' }), 'This passkey is already registered.');
  assert.equal(passkeyErrorMessage({ name: 'SecurityError' }), 'Passkeys need HTTPS and a hostname, not an IP address.');
  assert.equal(passkeyErrorMessage({ name: 'NotSupportedError' }), 'This browser does not support passkeys.');
});

test('an abort is silent, anything else keeps its message', () => {
  assert.equal(passkeyErrorMessage({ name: 'AbortError' }), null);
  assert.equal(passkeyErrorMessage(new Error('Server said no')), 'Server said no');
  assert.equal(passkeyErrorMessage({}), 'Passkey failed.');
  assert.equal(passkeyErrorMessage(null), 'Passkey failed.');
});

test('passkeys need a secure context and the API', () => {
  assert.equal(passkeysUsable({ isSecureContext: true, PublicKeyCredential: function () {} }), true);
  assert.equal(passkeysUsable({ isSecureContext: false, PublicKeyCredential: function () {} }), false);
  assert.equal(passkeysUsable({ isSecureContext: true }), false);
  assert.equal(passkeysUsable(undefined), false);
});
