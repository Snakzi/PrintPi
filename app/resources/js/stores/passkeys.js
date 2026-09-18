import { defineStore } from 'pinia';
import { startRegistration } from '@simplewebauthn/browser';
import { api } from '../api';

/**
 * The signed-in user's passkeys. Registration is the WebAuthn ceremony: options from the
 * server, the browser's authenticator makes a credential, the server stores it.
 */
export const usePasskeysStore = defineStore('passkeys', {
  state: () => ({ items: [], loaded: false, loading: false, busy: false }),

  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = (await api('passkeys')).data;
        this.loaded = true;
      } finally {
        this.loading = false;
      }
    },

    async register(name) {
      this.busy = true;
      try {
        const { options } = await api('passkeys/options');
        const credential = await startRegistration({ optionsJSON: options });
        const { data } = await api('passkeys', { method: 'POST', body: { name, credential } });
        this.items.push(data);
        return data;
      } finally {
        this.busy = false;
      }
    },

    async rename(passkey, name) {
      const { data } = await api(`passkeys/${passkey.id}`, { method: 'PUT', body: { name } });
      this.items.splice(this.items.findIndex((item) => item.id === passkey.id), 1, data);
    },

    async remove(passkey) {
      await api(`passkeys/${passkey.id}`, { method: 'DELETE' });
      this.items = this.items.filter((item) => item.id !== passkey.id);
    },
  },
});
