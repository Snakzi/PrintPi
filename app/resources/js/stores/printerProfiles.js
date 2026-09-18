import { defineStore } from 'pinia';
import { api } from '../api';

export const usePrinterProfileStore = defineStore('printerProfiles', {
  state: () => ({ items: [], loaded: false }),

  getters: {
    find: (state) => (id) => state.items.find((printer) => printer.id === id) ?? null,
  },

  actions: {
    async load() {
      if (this.loaded) return;
      this.items = (await api('printers')).data;
      this.loaded = true;
    },
  },
});
