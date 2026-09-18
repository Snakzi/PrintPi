<script setup>
import Icon from '../Icon.vue';

/* A button sized for a finger: 56 px high, big label, no hover states that a touch screen never shows. */
defineProps({
  variant: { type: String, default: 'secondary' },
  icon: { type: String, default: null },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
});

const VARIANTS = {
  primary: 'bg-emerald-600 text-white active:bg-emerald-500',
  secondary: 'bg-zinc-800 text-zinc-100 active:bg-zinc-700',
  danger: 'bg-red-600 text-white active:bg-red-500',
  ghost: 'text-zinc-300 active:bg-zinc-800',
};
</script>

<template>
  <button
    type="button"
    :disabled="disabled"
    class="inline-flex h-14 items-center justify-center gap-2 rounded-xl px-5 text-base font-semibold whitespace-nowrap transition-colors disabled:opacity-40"
    :class="[VARIANTS[variant] ?? VARIANTS.secondary, block ? 'w-full' : '']"
  >
    <Icon v-if="icon" :name="icon" class="size-6" />
    <slot />
  </button>
</template>
