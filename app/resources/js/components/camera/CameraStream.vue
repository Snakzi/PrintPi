<script setup>
import { ref } from 'vue';
import { useVisible } from '../../composables/useVisible';

/* An MJPEG stream or still image, letterboxed into whatever box it sits in. */
defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: 'Camera' },
});
const emit = defineEmits(['error']);
const container = ref(null);
const visible = useVisible(container);
</script>

<template>
  <img ref="container" :src="visible ? src : undefined" :alt="alt" class="size-full object-contain" @error="visible && emit('error')">
</template>
