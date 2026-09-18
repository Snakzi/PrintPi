import { defineStore } from 'pinia';
import { startAuthentication } from '@simplewebauthn/browser';
import { api } from '../api';

export const useSessionStore = defineStore('session', {
  state: () => ({ loaded: false, setupComplete: false, user: null, systemControl: false, apiKey: null, passkeys: false }),

  getters: {
    authenticated: (state) => state.user !== null,
  },

  actions: {
    async load() {
      const data = await api('session');
      this.setupComplete = data.setup_complete;
      this.user = data.user;
      this.systemControl = Boolean(data.system_control);
      this.passkeys = Boolean(data.passkeys);
      this.loaded = true;
    },
    async login(username, password, remember = false) {
      const data = await api('login', { method: 'POST', body: { username, password, remember } });
      this.user = data.user;
      this.setupComplete = true;
    },
    /**
     * The passkey ceremony for signing in: options from the server, the authenticator
     * picks an account it knows for this host, the server verifies the assertion.
     * With `autofill` the browser offers the passkeys in the username field instead
     * of a dialog and the promise waits until the user picks one.
     */
    async loginWithPasskey(remember = false, autofill = false) {
      const { options } = await api('passkeys/login/options');
      const credential = await startAuthentication({ optionsJSON: options, useBrowserAutofill: autofill });
      const data = await api('passkeys/login', { method: 'POST', body: { credential, remember } });
      this.user = data.user;
      this.setupComplete = true;
    },
    async logout() {
      try {
        await api('logout', { method: 'POST' });
      } finally {
        this.clear();
      }
    },
    async updateProfile(username, email) {
      const data = await api('account', { method: 'PUT', body: { username, email } });
      this.user = data.user;
    },
    async updatePassword(currentPassword, password, passwordConfirmation) {
      await api('account/password', { method: 'PUT', body: { current_password: currentPassword, password, password_confirmation: passwordConfirmation } });
    },
    completeSetup(user) {
      this.setupComplete = true;
      this.user = user;
    },
    clear() {
      this.user = null;
      this.apiKey = null;
    },
    /** The user's key for the upload API slicers use. */
    async loadApiKey() {
      const data = await api('api-key');
      this.apiKey = data.api_key;
    },
    async regenerateApiKey() {
      const data = await api('api-key', { method: 'POST' });
      this.apiKey = data.api_key;
    },
  },
});
