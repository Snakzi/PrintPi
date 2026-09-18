<script setup>
import { useCameraSource } from '../../composables/useCameraSource';
import CameraStream from '../camera/CameraStream.vue';
import Icon from '../Icon.vue';

/* The picture as large as the screen allows; a tap reopens the stream. */
const { src, reload } = useCameraSource();
</script>

<template>
  <button type="button" class="flex size-full items-center justify-center overflow-hidden rounded-2xl bg-black" @click="reload">
    <CameraStream v-if="src" :src="src" @error="reload" />
    <span v-else class="flex flex-col items-center gap-2 text-zinc-600"><Icon name="camera" class="size-12" /> No camera</span>
  </button>
</template>
