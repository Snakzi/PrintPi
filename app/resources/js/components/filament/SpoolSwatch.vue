<script setup>
import { computed, useId } from 'vue';
import GlitterPattern from './GlitterPattern.vue';

/* The colour of a spool as a dot, with its sparkle when the finish is glitter; a spool without
   a colour shows an empty ring. size: sm | md | lg | xl. */
const props = defineProps({
  color: { type: String, default: null },
  finish: { type: String, default: null },
  size: { type: String, default: 'md' },
});

// The sparkle's viewBox follows the pixel size so its specks stay speck-sized at every size.
const SIZES = {
  sm: { class: 'size-2.5', px: 10 },
  md: { class: 'size-4', px: 16 },
  lg: { class: 'size-9 shadow-md shadow-black/40', px: 36 },
  xl: { class: 'size-12 shadow-lg shadow-black/40', px: 48 },
};
const dims = computed(() => SIZES[props.size] ?? SIZES.md);
const pattern = useId();
</script>

<template>
  <span
    class="relative inline-block shrink-0 overflow-hidden rounded-full border"
    :class="[dims.class, color ? 'border-white/20' : 'border-dashed border-zinc-500']"
    :style="color ? { backgroundColor: color } : null"
    aria-hidden="true"
  >
    <svg v-if="color && finish === 'glitter'" class="absolute inset-0 size-full" :viewBox="`0 0 ${dims.px} ${dims.px}`">
      <defs><GlitterPattern :id="pattern" /></defs>
      <rect width="100%" height="100%" :fill="`url(#${pattern})`" />
    </svg>
  </span>
</template>
