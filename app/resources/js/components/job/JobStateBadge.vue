<script setup>
import { computed } from 'vue';

const STYLES = {
  preparing: ['Preparing', 'bg-sky-500/15 text-sky-300'],
  pausing: ['Pausing', 'bg-amber-400/15 text-amber-300'],
  resuming: ['Resuming', 'bg-amber-400/15 text-amber-300'],
  printing: ['Printing', 'bg-emerald-500/15 text-emerald-300'],
  paused: ['Paused', 'bg-amber-400/15 text-amber-300'],
  cancelling: ['Cancelling', 'bg-amber-400/15 text-amber-300'],
  finished: ['Finished', 'bg-emerald-500/15 text-emerald-300'],
  cancelled: ['Cancelled', 'bg-zinc-700 text-zinc-300'],
  error: ['Failed', 'bg-red-500/15 text-red-300'],
};

/* preparing: the start G-code still runs (heating, levelling), shown in place of Printing; the
   pause and resume scripts show as Pausing and Resuming through `activity`. */
const props = defineProps({
  state: { type: String, required: true },
  preparing: { type: Boolean, default: false },
  activity: { type: String, default: null },
});
const key = computed(() => {
  if (props.state !== 'printing' || !props.preparing) return props.state;
  return props.activity === 'pausing' || props.activity === 'resuming' ? props.activity : 'preparing';
});
const style = computed(() => STYLES[key.value] ?? [props.state, 'bg-zinc-700 text-zinc-300']);
</script>

<template>
  <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium" :class="style[1]">{{ style[0] }}</span>
</template>
