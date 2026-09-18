<script setup>
/* The timelapse of a print, filling the frame it sits in: the MP4 when ffmpeg made one, else the GIF. */
defineProps({ print: { type: Object, required: true } });
</script>

<template>
  <video v-if="print.video_url" :src="print.video_url" class="block size-full object-contain" controls loop muted playsinline autoplay />
  <img v-else :src="print.timelapse_url" :alt="`Timelapse of ${print.name}`" class="block size-full object-contain">
</template>
