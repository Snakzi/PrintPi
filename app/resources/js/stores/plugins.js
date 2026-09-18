import { defineStore } from 'pinia';
import { api } from '../api';
import { dashboardControls } from '../pluginControls';

export const usePluginStore = defineStore('plugins', {
  state: () => ({
    items: [],
    loaded: false,
    timer: null,
  }),

  getters: {
    find: (state) => (id) => state.items.find((plugin) => plugin.id === id) ?? null,
    installed: (state) => state.items.filter((plugin) => plugin.installed),
    available: (state) => state.items.filter((plugin) => !plugin.installed),
    /** Enabled plugins with controls that have a dashboard form; page-sized ones stay on their page. */
    withControls: (state) => state.items.filter((plugin) => plugin.enabled && dashboardControls(plugin).length),
  },

  actions: {
    async load() {
      const data = await api('plugins');
      this.items = data.data;
      this.loaded = true;
    },

    /** The daemon reports plugin state with its heartbeat, so pages with plugin panels poll. */
    startPolling(intervalMs = 3000) {
      this.stopPolling();
      this.load().catch(() => {});
      this.timer = setInterval(() => this.load().catch(() => {}), intervalMs);
    },

    stopPolling() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },

    replace(plugin) {
      const index = this.items.findIndex((entry) => entry.id === plugin.id);
      if (index >= 0) this.items[index] = plugin;
      else this.items.push(plugin);
      return plugin;
    },

    async install(body) {
      return this.replace(await api('plugins', { method: 'POST', body }));
    },

    async uninstall(id) {
      await api(`plugins/${id}`, { method: 'DELETE' });
      await this.load();
    },

    async setEnabled(id, enabled) {
      return this.replace(await api(`plugins/${id}`, { method: 'PUT', body: { enabled } }));
    },

    async saveSettings(id, values) {
      return this.replace(await api(`plugins/${id}/settings`, { method: 'PUT', body: values }));
    },

    async upgrade(id) {
      return this.replace(await api(`plugins/${id}/upgrade`, { method: 'POST' }));
    },

    /** Shows a new value at once; the daemon's own status arrives with the next poll. */
    async act(id, action, value, key = null) {
      const plugin = this.items.find((entry) => entry.id === id);
      if (plugin?.daemon?.status && key && value !== null) plugin.daemon.status[key] = value;
      await api(`plugins/${id}/actions`, { method: 'POST', body: { action, value } });
      setTimeout(() => this.load().catch(() => {}), 500);
    },
  },
});
