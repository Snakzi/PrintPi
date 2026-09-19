import { defineStore } from 'pinia';
import { api } from '../api.js';
import { notificationText, notificationToastType, unseenNotifications } from '../notifications/unseen.js';
import { useSettingsStore } from './settings.js';
import { useToastStore } from './toasts.js';

const HISTORY_MS = 10 * 60 * 1000;

const offlineState = () => ({
  connection: 'offline',
  status: 'idle',
  temperatures: {},
  position: {},
  firmware: {},
  capabilities: {},
  last_error: null,
  port: null,
  baudrate: null,
  updated_at: null,
  job: null,
});

export const ACTIVE_JOB_STATES = ['printing', 'paused', 'cancelling'];

export const usePrinterStore = defineStore('printer', {
  state: () => ({
    daemonAlive: false,
    ports: [],
    system: null,
    power: null,
    light: null,
    printer: offlineState(),
    serial: [],
    history: [],
    apiError: null,
    timer: null,
    connecting: false,
    receivedAt: null,
    /** The daemon's newest notifications and the time of the newest one already shown as a toast. */
    notifications: [],
    notificationsSeenAt: null,
    /** Visible terminals that need the serial log, including multiple dashboard widgets. */
    serialConsumers: 0,
    refreshing: false,
  }),

  getters: {
    connected: (state) => state.printer.connection === 'connected',
    connectionState: (state) => state.printer.connection,
    busy: (state) => state.printer.status !== 'idle',
    halted: (state) => state.printer.status === 'halted',
    job: (state) => state.printer.job ?? null,
    /** A job the daemon is still working on: printing, paused or cancelling. */
    printing: (state) => ACTIVE_JOB_STATES.includes(state.printer.job?.state),
    statusLabel() {
      if (!this.daemonAlive) return 'Daemon unreachable';
      switch (this.connectionState) {
        case 'connected':
          if (this.halted) return 'Halted';
          if (this.job?.state === 'paused') return 'Paused';
          if (this.job?.state === 'cancelling') return 'Cancelling…';
          if (this.job?.state === 'printing') return 'Printing';
          return this.busy ? 'Busy' : 'Connected';
        case 'connecting':
          return 'Connecting…';
        case 'error':
          return 'Error';
        default:
          return 'Not connected';
      }
    },
    /** Tailwind classes for the status dot next to statusLabel. */
    statusDotClass() {
      if (!this.daemonAlive) return 'bg-zinc-500';
      if (this.halted || this.connectionState === 'error') return 'bg-red-500';
      if (this.connected) {
        if (this.job?.state === 'printing') return 'bg-emerald-400 animate-pulse';
        return this.busy ? 'bg-amber-400' : 'bg-emerald-400';
      }
      if (this.connectionState === 'connecting') return 'bg-amber-400 animate-pulse';
      return 'bg-zinc-500';
    },
    temperatures: (state) => state.printer.temperatures ?? {},
    hotend: (state) => state.printer.temperatures?.T0 ?? null,
    bed: (state) => state.printer.temperatures?.B ?? null,
    extraSensors: (state) =>
      Object.entries(state.printer.temperatures ?? {}).filter(([key]) => key !== 'T0' && key !== 'B'),
    firmwareName: (state) => state.printer.firmware?.FIRMWARE_NAME ?? null,
    machineType: (state) => state.printer.firmware?.MACHINE_TYPE ?? null,
  },

  actions: {
    /** Plugin notifications that arrived since the last poll become toasts. */
    announce(items) {
      this.notifications = items;
      const { fresh, seenAt } = unseenNotifications(items, this.notificationsSeenAt);
      this.notificationsSeenAt = seenAt;
      if (useSettingsStore().values.notify_plugins === false) return;
      const toasts = useToastStore();
      for (const item of fresh) {
        toasts.push(notificationText(item), notificationToastType(item.level), item.level === 'info' ? 4000 : 6000);
      }
    },
    /** State is always fetched; serial data only for a connected printer with a visible terminal. */
    async refresh() {
      if (this.refreshing) return;
      this.refreshing = true;
      try {
        const state = await api('printer/state');
        this.daemonAlive = state.daemon_alive;
        this.ports = state.ports ?? [];
        this.system = state.system ?? null;
        this.power = state.power ?? null;
        this.light = state.light ?? null;
        this.printer = state.printer;
        this.receivedAt = Date.now();
        this.announce(state.notifications ?? []);
        this.apiError = null;
        if (this.connected) {
          this.recordSample();
          if (this.serialConsumers > 0) {
            const log = await api('printer/serial?limit=300');
            this.serial = log.lines;
          }
        } else {
          this.serial = [];
          this.history = [];
        }
      } catch (error) {
        this.apiError = error.message;
      } finally {
        this.refreshing = false;
      }
    },

    recordSample() {
      const now = Date.now();
      const temps = {};
      for (const [key, reading] of Object.entries(this.temperatures)) {
        temps[key] = { actual: reading.actual, target: reading.target };
      }
      this.history.push({ t: now, temps });
      const cutoff = now - HISTORY_MS;
      while (this.history.length && this.history[0].t < cutoff) this.history.shift();
    },

    startPolling(intervalMs = 2000) {
      this.stopPolling();
      this.refresh();
      this.timer = setInterval(() => this.refresh(), intervalMs);
    },

    stopPolling() {
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },

    refreshSoon(delay = 400) {
      setTimeout(() => this.refresh(), delay);
    },

    /** Asks the daemon to open a port and waits until it reports connected or an error. */
    connect(port, baud) {
      return this.awaitConnection(() => api('printer/connect', { method: 'POST', body: { port, baud } }));
    },

    /** Reopens the port of the last connect; the API answers 409 when there is none. */
    reconnect() {
      return this.awaitConnection(() => api('printer/reconnect', { method: 'POST' }));
    },

    async awaitConnection(request) {
      this.connecting = true;
      const before = this.printer.updated_at;
      try {
        await request();
        const deadline = Date.now() + 20000;
        while (Date.now() < deadline) {
          await new Promise((resolve) => setTimeout(resolve, 500));
          await this.refresh();
          const changed = this.printer.updated_at !== before;
          if (changed && this.connected) return true;
          if (changed && this.printer.connection === 'error') return false;
        }
        return false;
      } finally {
        this.connecting = false;
      }
    },

    async disconnect() {
      await api('printer/disconnect', { method: 'POST' });
      this.refreshSoon();
    },

    async emergencyStop() {
      await api('printer/emergency-stop', { method: 'POST' });
      this.refreshSoon();
    },

    /** Switches the light a plugin reports as the printer's, such as the LED strip. */
    async setLight(on) {
      if (!this.light) throw new Error('No printer light');
      await api(`plugins/${this.light.plugin}/actions`, {
        method: 'POST',
        body: { action: on ? 'printer_light_on' : 'printer_light_off' },
      });
      this.refreshSoon();
    },

    /** Recolours the printer's light; the status bar holds the colour until a poll confirms it, so no early refresh. */
    async setLightColor(color) {
      if (!this.light) throw new Error('No printer light');
      await api(`plugins/${this.light.plugin}/actions`, {
        method: 'POST',
        body: { action: 'printer_light_color', value: color },
      });
    },

    /** Switches the plug a plugin reports as the printer's power; off closes the port first on the daemon. */
    async setPower(on) {
      if (!this.power) throw new Error('No printer power switch');
      await api(`plugins/${this.power.plugin}/actions`, {
        method: 'POST',
        body: { action: on ? 'printer_power_on' : 'printer_power_off' },
      });
      this.refreshSoon(1500);
    },

    async send(command) {
      await api('printer/command', { method: 'POST', body: { command } });
      this.refreshSoon();
    },

    /** The daemon executes commands in arrival order, so a G91/G1/G90 sequence stays intact. */
    async sendAll(commands) {
      for (const command of commands) {
        await api('printer/command', { method: 'POST', body: { command } });
      }
      this.refreshSoon();
    },

    async pauseJob() {
      await api('printer/job/pause', { method: 'POST' });
      this.refreshSoon();
    },

    async resumeJob() {
      await api('printer/job/resume', { method: 'POST' });
      this.refreshSoon();
    },

    async cancelJob() {
      await api('printer/job/cancel', { method: 'POST' });
      this.refreshSoon();
    },

    async restartJob() {
      await api('printer/job/restart', { method: 'POST' });
      this.refreshSoon();
    },
  },
});
