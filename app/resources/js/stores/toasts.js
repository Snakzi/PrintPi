import { defineStore } from 'pinia';

let sequence = 0;

export const useToastStore = defineStore('toasts', {
  state: () => ({ items: [] }),

  actions: {
    push(message, type = 'info', ttl = 4000) {
      const id = ++sequence;
      this.items.push({ id, message, type });
      setTimeout(() => this.remove(id), ttl);
    },
    remove(id) {
      this.items = this.items.filter((item) => item.id !== id);
    },
    info(message) {
      this.push(message, 'info');
    },
    success(message) {
      this.push(message, 'success');
    },
    error(message) {
      this.push(message, 'error', 6000);
    },
  },
});
