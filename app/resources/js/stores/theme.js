import { defineStore } from 'pinia';

const STORAGE_KEY = 'printpi:theme';

/** Puts the theme on <html>, where the stylesheet reads it, and tells the three.js views. */
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  window.dispatchEvent(new CustomEvent('printpi:theme', { detail: theme }));
}

/* The colour theme of this browser: dark unless light was chosen. The choice lives in localStorage
   and app.blade.php applies it before the first paint, so the store only mirrors what is there. */
export const useThemeStore = defineStore('theme', {
  state: () => ({ theme: document.documentElement.dataset.theme === 'light' ? 'light' : 'dark' }),

  getters: {
    light: (state) => state.theme === 'light',
  },

  actions: {
    set(theme) {
      this.theme = theme;
      applyTheme(theme);
      try {
        localStorage.setItem(STORAGE_KEY, theme);
      } catch {
        // private mode or blocked storage: the choice lasts for this page
      }
    },
    toggle() {
      this.set(this.light ? 'dark' : 'light');
    },
  },
});
