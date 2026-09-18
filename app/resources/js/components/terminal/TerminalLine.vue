<script setup>
import { computed } from 'vue';

/* One line of the serial log: { t, dir: 'tx' | 'rx', line }. */
const props = defineProps({ entry: { type: Object, required: true } });

const classes = computed(() => {
  if (props.entry.dir === 'tx') return 'text-emerald-400';
  if (/^(Error:|!!)/.test(props.entry.line)) return 'text-red-400';
  if (/^Resend:/.test(props.entry.line)) return 'text-amber-400';
  if (/^echo:/.test(props.entry.line)) return 'text-zinc-400';
  return 'text-zinc-300';
});

const stamp = computed(() => new Date(props.entry.t * 1000).toLocaleTimeString());
</script>

<template>
  <div class="flex gap-2 whitespace-pre-wrap" :class="classes">
    <span class="shrink-0 text-zinc-600 tabular-nums">{{ stamp }}</span>
    <span class="w-2 shrink-0 text-center" :class="entry.dir === 'tx' ? 'text-emerald-600' : 'text-zinc-600'">{{ entry.dir === 'tx' ? '›' : '‹' }}</span>
    <span class="min-w-0 break-all">{{ entry.line }}</span>
  </div>
</template>
