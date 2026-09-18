import { defineStore } from 'pinia';
import { api, upload } from '../api';

export const useFileStore = defineStore('files', {
  state: () => ({ items: [], loading: false, uploading: false, progress: 0 }),

  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = (await api('files')).data;
      } finally {
        this.loading = false;
      }
    },
    async upload(file) {
      this.uploading = true;
      this.progress = 0;
      try {
        await upload('files', file, (progress) => {
          this.progress = progress;
        });
        await this.load();
      } finally {
        this.uploading = false;
      }
    },
    async remove(file) {
      await api(`files/${file.id}`, { method: 'DELETE' });
      this.items = this.items.filter((item) => item.id !== file.id);
    },
    async print(file) {
      await api(`files/${file.id}/print`, { method: 'POST' });
    },
  },
});
