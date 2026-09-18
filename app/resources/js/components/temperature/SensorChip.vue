<script setup>
import { formatTemp } from '../../format';

/* A read-only sensor such as the heatbreak or the chamber, with its target when it has one. */
defineProps({
  label: { type: String, required: true },
  actual: { type: Number, default: null },
  target: { type: Number, default: null },
});
</script>

<template>
  <span class="inline-flex items-center gap-1.5 rounded-md bg-zinc-950/70 px-2 py-1 text-xs">
    <span class="text-zinc-500">{{ label }}</span>
    <span class="font-mono text-zinc-200 tabular-nums">
      {{ formatTemp(actual) }}<span v-if="target" class="text-zinc-500"> / {{ formatTemp(target, 0) }}</span> °C
    </span>
  </span>
</template>
