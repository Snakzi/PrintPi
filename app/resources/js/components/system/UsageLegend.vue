<script setup>
/* series: [{ key, label, color }]; latest: the newest point, whose values sit next to the labels. */
defineProps({
  series: { type: Array, required: true },
  latest: { type: Object, default: null },
  range: { type: String, default: '' },
});

const formatPercent = (value) => (value == null ? '–' : `${value.toFixed(1)} %`);
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
    <span v-for="entry in series" :key="entry.key" class="flex items-center gap-1.5">
      <span class="inline-block h-0.5 w-4 rounded-full" :style="{ background: entry.color }" />
      <span class="text-zinc-400">{{ entry.label }}</span>
      <span class="font-mono text-zinc-200 tabular-nums">{{ formatPercent(latest?.[entry.key]) }}</span>
    </span>
    <span v-if="range" class="ml-auto text-zinc-500 tabular-nums">{{ range }}</span>
  </div>
</template>
