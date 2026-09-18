<script setup>
import { ref } from 'vue';
import { useCameraSource } from '../../composables/useCameraSource';
import CameraSnapshot from '../camera/CameraSnapshot.vue';
import CameraStream from '../camera/CameraStream.vue';
import Icon from '../Icon.vue';

/* A spot for the camera that starts empty: a camera icon in the middle, the picture only after
   a tap, and a tap on the picture puts the icon back. Leaving the screen forgets it. */
const { src, snapshot } = useCameraSource();
const shown = ref(false);
</script>

<template>
  <div class="flex min-h-0 w-full items-center justify-center overflow-hidden rounded-2xl" :class="shown && src ? 'bg-black' : ''" @click="shown = !shown">
    <CameraSnapshot v-if="shown && snapshot" :src="snapshot" :interval="500" />
    <CameraStream v-else-if="shown && src" :src="src" />
    <Icon v-else name="camera" class="size-9" :class="src ? 'text-zinc-500' : 'text-zinc-800'" />
  </div>
</template>
