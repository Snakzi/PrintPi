<script setup>
import Icon from '../Icon.vue';

/* One entry of the rail: icon over a short label, 64 px wide and 52 px high so six of them fit above the stop. */
defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  badge: { type: Boolean, default: false },
});
</script>

<template>
  <button
    type="button"
    :aria-pressed="active"
    class="relative flex h-13 w-16 flex-col items-center justify-center gap-0.5 rounded-xl transition-colors"
    :class="active ? 'bg-zinc-800 text-emerald-400' : 'text-zinc-400 active:bg-zinc-800'"
  >
    <Icon :name="icon" class="size-6" />
    <span class="text-[10px] font-medium">{{ label }}</span>
    <span v-if="badge" class="absolute top-1.5 right-2 size-2 rounded-full bg-emerald-400 animate-pulse" />
  </button>
</template>
