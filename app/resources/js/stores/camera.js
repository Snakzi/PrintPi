import { defineStore } from 'pinia';
import { api } from '../api';

export const useCameraStore = defineStore('camera', {
  state: () => ({
    cameras: [],
    status: { running: false, device: null, port: null, available: false, error: null },
    streamUrl: '/webcam/stream',
    snapshotUrl: '/webcam/snapshot',
    settings: { camera_device: null, camera_url: null },
    loaded: false,
  }),

  actions: {
    async load() {
      const data = await api('camera');
      this.cameras = data.cameras;
      this.status = data.status;
      this.streamUrl = data.stream_url;
      this.snapshotUrl = data.snapshot_url;
      this.settings = data.settings;
      this.loaded = true;
    },
    async start(device) {
      await api('camera/start', { method: 'POST', body: device ? { device } : {} });
    },
    async stop() {
      await api('camera/stop', { method: 'POST' });
    },
  },
});
