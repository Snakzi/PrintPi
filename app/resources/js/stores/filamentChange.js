import { defineStore } from 'pinia';
import { api } from '../api';
import { endedRecently, isEnded } from '../filament/walkthrough';
import { usePrinterStore } from './printer';

/**
 * The daemon's filament walkthrough as the UI sees it. Its state comes with every printer
 * poll as `printer.filament`; this store starts one, answers it and remembers which ended one
 * the user has already closed, so the panel and the modal can show the result once.
 */
export const useFilamentChangeStore = defineStore('filamentChange', {
  state: () => ({ dismissedId: null, busy: false }),

  getters: {
    current: () => usePrinterStore().printer.filament ?? null,
    /** The daemon is still on it. */
    active() {
      return Boolean(this.current) && !isEnded(this.current);
    },
    /** Running, or ended a moment ago and not closed yet: what the flow screens show. */
    visible() {
      if (!this.current) return false;
      return this.active || (this.current.id !== this.dismissedId && endedRecently(this.current));
    },
    /** Whether a walkthrough can start: a connected printer with nothing else going on. */
    available() {
      const printer = usePrinterStore();
      return printer.connected && !printer.printing && !this.active;
    },
  },

  actions: {
    /** Load a spool of the inventory (by id) or a bare material; unloadFirst turns it into a change. */
    async load({ spoolId = null, material = null, unloadFirst = false }) {
      await this.send('printer/filament/load', { spool_id: spoolId, material, unload_first: unloadFirst });
    },

    async unload() {
      await this.send('printer/filament/unload');
    },

    async proceed() {
      await this.send('printer/filament/continue');
    },

    /** yes when the filament runs clean, purge for another purge length. */
    async answer(answer) {
      await this.send('printer/filament/answer', { answer });
    },

    async cancel() {
      await this.send('printer/filament/cancel');
    },

    /** Closes the result of an ended walkthrough; a running one cannot be dismissed. */
    dismiss() {
      if (this.current && !this.active) this.dismissedId = this.current.id;
    },

    async send(path, body = undefined) {
      this.busy = true;
      try {
        await api(path, { method: 'POST', body });
        const printer = usePrinterStore();
        printer.refreshSoon(250);
        printer.refreshSoon(1200);
      } finally {
        this.busy = false;
      }
    },
  },
});
