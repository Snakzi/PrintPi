<script setup>
import Icon from '../Icon.vue';

/* One key of the jog pad. rotate turns the chevron: 0 down, 90 left, 180 up, 270 right. */
defineProps({
  icon: { type: String, default: 'chevron' },
  title: { type: String, required: true },
  rotate: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
});

const SIZES = { md: 'size-11', lg: 'size-16' };
</script>

<template>
  <button
    type="button"
    :title="title"
    :aria-label="title"
    :disabled="disabled"
    :class="SIZES[size] ?? SIZES.md"
    class="flex items-center justify-center rounded-md bg-zinc-800/70 text-zinc-200 transition-colors select-none hover:bg-zinc-700 active:bg-zinc-600 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-zinc-800/70"
  >
    <Icon :name="icon" :class="size === 'lg' ? 'size-7' : 'size-5'" :style="rotate ? { transform: `rotate(${rotate}deg)` } : null" />
  </button>
</template>
