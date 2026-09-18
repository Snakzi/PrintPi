<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../stores/printer';

const props = defineProps({ plugin: { type: Object, required: true } });
const printer = usePrinterStore();

const STATES = {
  running: { label: 'Running', classes: 'bg-emerald-950 text-emerald-300' },
  error: { label: 'Error', classes: 'bg-red-950 text-red-300' },
  installing: { label: 'Installing', classes: 'bg-amber-950 text-amber-300' },
  pending: { label: 'Starting', classes: 'bg-zinc-800 text-zinc-300' },
  stopped: { label: 'Stopped', classes: 'bg-zinc-800 text-zinc-400' },
};

const badge = computed(() => {
  if (!props.plugin.enabled) return { label: 'Disabled', classes: 'bg-zinc-800 text-zinc-400' };
  if (!printer.daemonAlive) return { label: 'Daemon offline', classes: 'bg-zinc-800 text-zinc-400' };
  const state = props.plugin.daemon?.state ?? 'pending';
  return STATES[state] ?? { label: state, classes: 'bg-zinc-800 text-zinc-300' };
});
</script>

<template>
  <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide" :class="badge.classes">
    {{ badge.label }}
  </span>
</template>
