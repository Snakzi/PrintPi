<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

/* The camera as a still refreshed every `interval` ms from the snapshot URL: one JPEG per
   refresh instead of a 30 fps MJPEG stream, which a Pi's browser cannot decode on the side. */
const props = defineProps({
  src: { type: String, required: true },
  interval: { type: Number, default: 500 },
  alt: { type: String, default: 'Camera' },
});

const current = ref(null);
let timer = null;
let stopped = false;

function next() {
  if (stopped) return;
  current.value = `${props.src}${props.src.includes('?') ? '&' : '?'}_=${Date.now()}`;
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(next, props.interval);
}

onMounted(next);
onBeforeUnmount(() => {
  stopped = true;
  clearTimeout(timer);
});
</script>

<template>
  <img v-if="current" :src="current" :alt="alt" class="size-full object-contain" @load="schedule" @error="schedule">
</template>
