import { defineStore } from 'pinia';

/** The file a print is about to be started for; while set, App.vue shows the spool picker. */
export const usePrintStartStore = defineStore('printStart', {
  state: () => ({ file: null }),

  actions: {
    request(file) {
      this.file = file;
    },
    dismiss() {
      this.file = null;
    },
  },
});
