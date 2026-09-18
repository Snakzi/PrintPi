import { defineStore } from 'pinia';
import { api } from '../api';
import { useSessionStore } from './session';

/** `pending` is reboot, restart or update while the host is going away. */
export const useSystemStore = defineStore('system', {
  state: () => ({
    pending: null,
    /** CPU and memory usage of the last 24 hours as { t (ms), cpu, memory } in percent, oldest first. */
    history: [],
    historyInterval: 30_000,
    historyLoaded: false,
  }),

  getters: {
    available: () => useSessionStore().systemControl,
  },

  actions: {
    async reboot() {
      await api('system/reboot', { method: 'POST' });
      this.pending = 'reboot';
    },
    async restartWebServer() {
      await api('system/restart-web', { method: 'POST' });
      this.pending = 'restart';
    },
    async loadHistory() {
      const data = await api('system/history');
      this.historyInterval = data.interval * 1000;
      this.history = data.points.map(([t, cpu, memory]) => ({ t: t * 1000, cpu, memory }));
      this.historyLoaded = true;
    },
  },
});
