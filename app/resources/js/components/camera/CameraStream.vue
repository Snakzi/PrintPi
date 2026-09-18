<script setup>
/* An MJPEG stream or still image, letterboxed into whatever box it sits in. */
defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: 'Camera' },
});
const emit = defineEmits(['error']);
</script>

<template>
  <img :src="src" :alt="alt" class="size-full object-contain" @error="emit('error')">
</template>
