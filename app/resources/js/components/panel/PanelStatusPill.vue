<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import Icon from '../Icon.vue';

/* The printer's state as a pill; while nothing is connected it is the Connect button and
   reopens the last port, the same as the connect button of the status bar. */
const printer = usePrinterStore();
const toasts = useToastStore();

const offline = computed(() => printer.daemonAlive && !printer.connected && printer.connectionState !== 'connecting' && !printer.connecting);
const busy = computed(() => printer.connecting || printer.connectionState === 'connecting');

async function connect() {
  try {
    const ok = await printer.reconnect();
    if (!ok) toasts.error(printer.printer.error || 'Could not connect');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <button
    v-if="offline || busy"
    type="button"
    class="flex h-12 shrink-0 items-center gap-2 rounded-full px-5 text-base font-semibold whitespace-nowrap transition-colors disabled:opacity-60"
    :class="busy ? 'bg-zinc-800 text-zinc-300' : 'bg-emerald-600 text-white active:bg-emerald-500'"
    :disabled="busy"
    @click="connect"
  >
    <Icon name="link" class="size-5" />
    {{ busy ? 'Connecting…' : 'Connect' }}
  </button>
  <div v-else class="flex h-12 shrink-0 items-center gap-2 rounded-full bg-zinc-900 px-5 text-base font-medium whitespace-nowrap">
    <span class="size-2.5 rounded-full" :class="printer.statusDotClass" />
    {{ printer.statusLabel }}
  </div>
</template>
