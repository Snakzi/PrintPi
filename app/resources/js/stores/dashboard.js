import { defineStore } from 'pinia';
import { api } from '../api';

let saveTimer = null;

/** Only the fields the API validates; grid-layout-plus adds its own bookkeeping to items. */
function clean(item) {
  return { i: String(item.i), type: item.type, x: item.x, y: item.y, w: item.w, h: item.h };
}

function same(a, b) {
  return JSON.stringify(a.map(clean)) === JSON.stringify(b.map(clean));
}

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    layout: [],
    widgets: {},
    columns: 12,
    customized: false,
    editing: false,
    loaded: false,
    saving: false,
    error: null,
  }),

  getters: {
    /** Widget types that are not on the board yet. */
    available: (state) =>
      Object.entries(state.widgets)
        .filter(([type]) => !state.layout.some((item) => item.type === type))
        .map(([type, meta]) => ({ type, ...meta })),
    meta: (state) => (type) =>
      state.widgets[type] ?? { title: type, description: '', w: 3, h: 4, min_w: 1, min_h: 1, needs_connection: false },
  },

  actions: {
    async load() {
      const data = await api('dashboard');
      this.layout = data.layout.map(clean);
      this.widgets = data.widgets;
      this.columns = data.columns;
      this.customized = data.customized;
      this.loaded = true;
    },

    /** Called by the grid after a drag or resize. */
    setLayout(layout) {
      const next = layout.map(clean);
      if (same(next, this.layout)) return;
      this.layout = next;
      this.scheduleSave();
    },

    add(type) {
      const meta = this.widgets[type];
      if (!meta || this.layout.some((item) => item.type === type)) return;
      const bottom = this.layout.reduce((max, item) => Math.max(max, item.y + item.h), 0);
      this.layout = [...this.layout, { i: type, type, x: 0, y: bottom, w: meta.w, h: meta.h }];
      this.scheduleSave();
    },

    remove(i) {
      this.layout = this.layout.filter((item) => item.i !== i);
      this.scheduleSave();
    },

    async reset() {
      clearTimeout(saveTimer);
      const data = await api('dashboard', { method: 'DELETE' });
      this.layout = data.layout.map(clean);
      this.customized = false;
    },

    scheduleSave() {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => this.save(), 600);
    },

    async save() {
      this.saving = true;
      try {
        const data = await api('dashboard', { method: 'PUT', body: { layout: this.layout.map(clean) } });
        this.customized = data.customized;
        this.error = null;
      } catch (error) {
        this.error = error.message;
      } finally {
        this.saving = false;
      }
    },
  },
});
