import { defineStore } from 'pinia';
import { api } from '../api';

/** Past prints, newest first; `key` is the daemon's job id and links a print to the job in the printer state. */
export const usePrintStore = defineStore('prints', {
  state: () => ({ items: [], loading: false, loaded: false }),

  getters: {
    byKey: (state) => (key) => state.items.find((item) => item.key === key) ?? null,
  },

  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = (await api('prints')).data;
        this.loaded = true;
      } finally {
        this.loading = false;
      }
    },

    /** The print filed for a job id, fetched when the list does not have it yet; null while the daemon still writes it. */
    async find(key) {
      const known = this.byKey(key);
      if (known) return known;
      const [found] = (await api(`prints?key=${encodeURIComponent(key)}`)).data;
      if (found && !this.byKey(key)) this.items.unshift(found);
      return found ?? null;
    },

    async remove(print) {
      await api(`prints/${print.id}`, { method: 'DELETE' });
      this.items = this.items.filter((item) => item.id !== print.id);
    },

    /** Books the print on another spool (null for none); the filament it used moves along. */
    async setSpool(print, spoolId) {
      const { data } = await api(`prints/${print.id}`, { method: 'PUT', body: { spool_id: spoolId } });
      const index = this.items.findIndex((item) => item.id === print.id);
      if (index !== -1) this.items.splice(index, 1, data);
      return data;
    },
  },
});
