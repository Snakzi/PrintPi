<script setup>
defineProps({
  size: { type: String, default: 'size-8' },
});

// Served as is from public/, so Vite must not try to bundle it.
const src = '/images/logo.svg';
</script>

<template>
  <img :src="src" alt="PrintPi" :class="size" class="shrink-0 rounded-lg" draggable="false">
</template>
