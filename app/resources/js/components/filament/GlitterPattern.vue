<script setup>
/* The sparkle of glitter filament as an SVG pattern for a <defs> block: a few specks of varying
   size and brightness in a 20-unit tile, most of them bright and two dark so the effect shows on
   light and on dark colours. Use it as `fill="url(#id)"` on the shape that should sparkle. */
defineProps({ id: { type: String, required: true } });

const BRIGHT = [
  [2.5, 3.1, 0.5, 0.85], [9.4, 1.6, 0.35, 0.6], [16.8, 4.7, 0.55, 0.9],
  [5.7, 9.3, 0.4, 0.7], [13.1, 11.2, 0.35, 0.55], [18.6, 15.4, 0.45, 0.8],
  [1.9, 15.8, 0.4, 0.65], [9.8, 17.6, 0.5, 0.9],
];
const DARK = [[12.6, 6.4, 0.4, 0.28], [5.1, 13.9, 0.35, 0.25]];
</script>

<template>
  <pattern :id="id" patternUnits="userSpaceOnUse" width="20" height="20">
    <circle v-for="([x, y, r, opacity], index) in BRIGHT" :key="`b${index}`" :cx="x" :cy="y" :r="r" fill="#fff" :fill-opacity="opacity" />
    <circle v-for="([x, y, r, opacity], index) in DARK" :key="`d${index}`" :cx="x" :cy="y" :r="r" fill="#000" :fill-opacity="opacity" />
  </pattern>
</template>
