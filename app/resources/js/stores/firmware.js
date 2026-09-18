import { defineStore } from 'pinia';
import { api, upload } from '../api';
import { ACTIVE_PHASES, phaseLabel, progressLabel } from '../firmware/format.js';

const POLL_MS = 2000;
const LISTING_TIMEOUT_MS = 20000;
const watches = new WeakMap();

export const useFirmwareStore = defineStore('firmware', {
  state: () => ({
    loaded: false,
    profile: null,
    method: null,
    methods: [],
    connected: false,
    installed: { name: null, version: null },
    latest: null,
    upToDate: null,
    checkedAt: null,
    error: null,
    avrdude: { mcu: null, programmer: null, baud: null },
    status: null,
    files: { files: [], listed_at: null, error: null },
    checking: false,
    listing: false,
    busy: false,
    // The overlay follows a flash from its start until the user closes the result.
    tracking: false,
  }),

  getters: {
    inProgress: (state) => ACTIVE_PHASES.includes(state.status?.phase),
    done: (state) => state.status?.phase === 'done',
    failed: (state) => state.status?.phase === 'failed',
    phaseLabel: (state) => phaseLabel(state.status?.phase),
    progressLabel: (state) => progressLabel(state.status),
    /** Firmware files on the printer's drive, for the Buddy method. */
    driveFirmware: (state) => state.files.files.filter((file) => /\.bbf$/i.test(file.name)),
  },

  actions: {
    async load({ check = false } = {}) {
      this.checking = check;
      try {
        this.apply(await api(`printer/firmware${check ? '?check=1' : ''}`));
      } finally {
        this.checking = false;
      }
    },

    apply(data) {
      this.$patch({
        loaded: true,
        profile: data.profile,
        method: data.method,
        methods: data.methods,
        connected: data.connected,
        installed: data.installed,
        latest: data.latest,
        upToDate: data.up_to_date,
        checkedAt: data.checked_at,
        error: data.error,
        avrdude: data.avrdude,
        status: data.status,
        files: data.files,
      });
    },

    /** Asks the daemon to read the printer's drive and waits for a newer listing. */
    async refreshFiles() {
      if (this.listing) return;
      this.listing = true;
      const before = this.files.listed_at;
      try {
        await api('printer/firmware/files', { method: 'POST' });
        const deadline = Date.now() + LISTING_TIMEOUT_MS;
        while (Date.now() < deadline) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          await this.load();
          if (this.files.listed_at !== before) return;
        }
        throw new Error('The printer did not answer with a file list.');
      } finally {
        this.listing = false;
      }
    },

    /** Starts a flash: `name` for a file on the drive, `file` for an upload, `source: 'release'` for the newest release. */
    async flash({ name = null, file = null, source = null } = {}) {
      if (this.busy || this.inProgress) return;
      this.busy = true;
      try {
        if (file) await upload('printer/firmware/flash', file);
        else await api('printer/firmware/flash', { method: 'POST', body: { name, source } });
        this.status = { phase: 'preparing', method: this.method, file: name ?? file?.name ?? null, step: null, progress: null, log: [], error: null };
        this.track();
      } finally {
        this.busy = false;
      }
    },

    /** Follows a running flash until it ends; the printer is unreachable meanwhile, the web app is not. */
    track() {
      if (!this.inProgress) return;
      this.tracking = true;
      if (watches.has(this)) return;
      const watch = { timer: null };
      watches.set(this, watch);
      const active = () => watches.get(this) === watch;
      const poll = async () => {
        try {
          await this.load();
        } catch {
          // a failed poll is retried with the next one
        }
        if (!active()) return;
        if (this.inProgress) watch.timer = setTimeout(poll, POLL_MS);
        else this.stop();
      };
      watch.timer = setTimeout(poll, POLL_MS);
    },

    dismiss() {
      this.stop();
      this.tracking = false;
    },

    stop() {
      const watch = watches.get(this);
      if (watch) clearTimeout(watch.timer);
      watches.delete(this);
    },
  },
});
