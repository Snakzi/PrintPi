import { defineStore } from 'pinia';
import { api } from '../api.js';

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    values: { serial_port: null, baud_rate: 115200, camera_url: null, energy_price: null, currency: '€' },
    loaded: false,
    saving: false,
  }),

  actions: {
    async load() {
      this.values = await api('settings');
      this.loaded = true;
    },
    async save(patch) {
      this.saving = true;
      try {
        this.values = await api('settings', { method: 'PUT', body: patch });
      } finally {
        this.saving = false;
      }
    },
  },
});
