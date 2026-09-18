import { defineStore } from 'pinia';
import { api } from '../api';

/**
 * The spool inventory. The catalog behind the form is fetched separately: `materials` maps a
 * material to its typical density, `vendors` a vendor to its empty spool weight and product lines.
 */
export const useFilamentStore = defineStore('filament', {
  state: () => ({ items: [], materials: {}, vendors: {}, catalogLoaded: false, loading: false, loaded: false }),

  getters: {
    /** The spool in the printer, or null. */
    current: (state) => state.items.find((spool) => spool.loaded) ?? null,
    active: (state) => state.items.filter((spool) => !spool.archived_at),
    archived: (state) => state.items.filter((spool) => spool.archived_at),
    byId: (state) => (id) => state.items.find((spool) => spool.id === id) ?? null,
  },

  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = (await api('spools')).data;
        this.loaded = true;
      } finally {
        this.loading = false;
      }
    },

    /** Fetches the inventory once; later calls are free. */
    async ensure() {
      if (!this.loaded && !this.loading) await this.load();
    },

    /** Fetches materials and vendors once, when a form needs them. */
    async loadCatalog() {
      if (this.catalogLoaded) return;
      const catalog = await api('spools/catalog');
      this.materials = catalog.materials ?? {};
      this.vendors = catalog.vendors ?? {};
      this.catalogLoaded = true;
    },

    async create(data) {
      const { data: spool } = await api('spools', { method: 'POST', body: data });
      this.items.unshift(spool);
      return spool;
    },

    async update(spool, data) {
      const { data: updated } = await api(`spools/${spool.id}`, { method: 'PUT', body: data });
      this.replace(updated);
      return updated;
    },

    async remove(spool) {
      await api(`spools/${spool.id}`, { method: 'DELETE' });
      this.items = this.items.filter((item) => item.id !== spool.id);
    },

    /** Puts a spool into the printer; the one loaded before is taken out. */
    async loadSpool(spool) {
      const { data: loaded } = await api(`spools/${spool.id}/load`, { method: 'POST' });
      this.items.forEach((item) => {
        item.loaded = false;
      });
      this.replace(loaded);
    },

    async unloadSpool() {
      await api('spools/unload', { method: 'POST' });
      this.items.forEach((item) => {
        item.loaded = false;
      });
    },

    replace(spool) {
      const index = this.items.findIndex((item) => item.id === spool.id);
      if (index === -1) this.items.unshift(spool);
      else this.items.splice(index, 1, spool);
    },
  },
});
