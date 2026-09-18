<script setup>
/* value is 0..1; null shows an indeterminate bar with a sweeping segment. full stretches to the container
   instead of a fixed width. tone: emerald | amber | red | zinc | sky. size: sm | md. */
defineProps({
  value: { type: Number, default: null },
  full: { type: Boolean, default: false },
  tone: { type: String, default: 'emerald' },
  size: { type: String, default: 'md' },
});

const TONES = {
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-400',
  red: 'bg-red-500',
  zinc: 'bg-zinc-600',
  sky: 'bg-sky-500',
};
</script>

<template>
  <div class="overflow-hidden rounded-full bg-zinc-800" :class="[full ? 'w-full' : 'w-64 max-w-full', size === 'sm' ? 'h-1.5' : 'h-2']">
    <div v-if="value === null" class="h-full w-1/3 animate-sweep rounded-full" :class="TONES[tone] ?? TONES.emerald" />
    <div
      v-else
      class="h-full rounded-full transition-[width] duration-500"
      :class="TONES[tone] ?? TONES.emerald"
      :style="{ width: `${Math.min(100, Math.max(0, value * 100))}%` }"
    />
  </div>
</template>
