<script setup>
import Icon from '../Icon.vue';

/* A pill that is lit while on: icon, label and, for a light that reports one, a dot in its colour. */
defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  on: { type: Boolean, default: false },
  color: { type: String, default: null },
  disabled: { type: Boolean, default: false },
});
</script>

<template>
  <button
    type="button"
    :aria-pressed="on"
    :disabled="disabled"
    class="flex h-12 shrink-0 items-center gap-2 rounded-full px-4 text-base font-medium whitespace-nowrap transition-colors disabled:opacity-40"
    :class="on ? 'bg-emerald-600/20 text-emerald-300 ring-1 ring-emerald-500/60 active:bg-emerald-600/30' : 'bg-zinc-900 text-zinc-400 active:bg-zinc-800'"
  >
    <span v-if="color && on" class="size-3 rounded-full ring-1 ring-black/30" :style="{ background: color }" />
    <Icon v-else :name="icon" class="size-5" />
    {{ label }}
  </button>
</template>
