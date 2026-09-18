import { defineStore } from 'pinia';
import { api } from '../api';
import { phaseLabel, progressLabel } from '../updates/format.js';

const ACTIVE_PHASES = ['queued', 'downloading', 'verifying', 'unpacking', 'installing', 'switching'];
const POLL_MS = 2000;
const watches = new WeakMap();
const requests = new WeakMap();

export const useUpdatesStore = defineStore('updates', {
  state: () => ({
    loaded: false,
    installed: null,
    channel: null,
    channels: [],
    available: null,
    checkedAt: null,
    error: null,
    status: null,
    systemControl: false,
    checking: false,
    busy: false,
    // The overlay follows a run from its start until the page reloads or the user closes a failure.
    tracking: false,
    failedPolls: 0,
  }),

  getters: {
    inProgress: (state) => ACTIVE_PHASES.includes(state.status?.phase),
    done: (state) => state.status?.phase === 'done',
    failed: (state) => state.status?.phase === 'failed',
    phaseLabel: (state) => phaseLabel(state.status?.phase),
    progressLabel: (state) => progressLabel(state.status),
  },

  actions: {
    async load({ check = false } = {}) {
      const pending = requests.get(this);
      if (pending) {
        if (!check || pending.check) return pending.promise;
        await pending.promise;
        return this.load({ check });
      }

      this.checking = check;
      const promise = (async () => {
        try {
          const data = await api(`system/update${check ? '?check=1' : ''}`);
          this.$patch({
            loaded: true,
            installed: data.installed,
            channel: data.channel,
            channels: data.channels,
            available: data.available,
            checkedAt: data.checked_at,
            error: data.error,
            status: data.status,
            systemControl: data.system_control,
          });
        } finally {
          this.checking = false;
          requests.delete(this);
        }
      })();
      requests.set(this, { check, promise });
      return promise;
    },

    async install(version) {
      if (this.busy || this.inProgress) return;
      this.busy = true;
      try {
        await requests.get(this)?.promise;
        const data = await api('system/update', { method: 'POST', body: { version } });
        this.status = { action: 'update', version: data.version, phase: 'queued', step: null, error: null };
        this.track();
      } finally {
        this.busy = false;
      }
    },

    /**
     * Follows a running update (or a rollback started from the shell) until it ends. The web server restarts while the
     * release switches, so failed polls are expected; they are only counted for the overlay.
     */
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
          this.failedPolls = 0;
        } catch {
          this.failedPolls += 1;
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
