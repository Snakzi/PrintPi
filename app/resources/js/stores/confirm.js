import { defineStore } from 'pinia';

/* One question at a time for the user, answered through ConfirmModal: ask() resolves true for
   Confirm, false for Cancel, Escape or a click outside. */
export const useConfirmStore = defineStore('confirm', {
  state: () => ({ request: null }),

  actions: {
    ask({ title, message = '', danger = false }) {
      if (this.request) this.request.resolve(false);
      return new Promise((resolve) => {
        this.request = { title, message, danger, resolve };
      });
    },
    answer(value) {
      const request = this.request;
      this.request = null;
      request?.resolve(value);
    },
  },
});
