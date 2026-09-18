import { defineStore } from 'pinia';

/* Whether the navigation drawer is open on a phone; the sidebar from md up ignores it. */
export const useNavStore = defineStore('nav', {
  state: () => ({ open: false }),

  actions: {
    toggle() {
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
  },
});
