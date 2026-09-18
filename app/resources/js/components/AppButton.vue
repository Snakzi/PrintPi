<script setup>
import { computed } from 'vue';
import Icon from './Icon.vue';

/* variant: primary | secondary | muted | ghost | danger | destructive | success. size: sm | md | lg. block stretches to the container. */
const props = defineProps({
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: 'md' },
  icon: { type: String, default: null },
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
});

const VARIANTS = {
  primary: 'bg-emerald-600 text-white hover:enabled:bg-emerald-500',
  secondary: 'border border-zinc-700 text-zinc-200 hover:enabled:border-zinc-600 hover:enabled:bg-zinc-800',
  muted: 'bg-zinc-800 text-zinc-100 hover:enabled:bg-zinc-700',
  ghost: 'text-zinc-400 hover:enabled:bg-zinc-800 hover:enabled:text-zinc-100',
  danger: 'border border-red-900/70 text-red-300 hover:enabled:bg-red-950/60 hover:enabled:text-red-200',
  destructive: 'bg-red-600 text-white hover:enabled:bg-red-500',
  success: 'border border-emerald-500 bg-emerald-500/15 text-emerald-300',
};

const SIZES = {
  sm: 'h-7 px-2.5 text-xs',
  md: 'h-9 px-3.5 text-sm',
  lg: 'h-11 px-4 text-sm',
};

const classes = computed(() => [
  VARIANTS[props.variant] ?? VARIANTS.secondary,
  SIZES[props.size] ?? SIZES.md,
  props.block ? 'flex w-full' : 'inline-flex',
]);
</script>

<template>
  <button
    :type="type"
    :disabled="disabled"
    class="items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
    :class="classes"
  >
    <Icon v-if="icon" :name="icon" :class="size === 'sm' ? 'size-3.5' : 'size-4'" />
    <slot />
  </button>
</template>
