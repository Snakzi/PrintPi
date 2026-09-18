<script setup>
import { defineAsyncComponent } from 'vue';
import Icon from '../Icon.vue';

// three.js only loads once there is a file to show.
const ModelViewer = defineAsyncComponent(() => import('../ModelViewer.vue'));

/* The part of the running job in the filament colour; a job without a known file shows nothing but a cube. */
defineProps({
  file: { type: Object, default: null },
  color: { type: String, default: null },
  still: { type: Boolean, default: false },
});
</script>

<template>
  <div class="relative min-h-0">
    <ModelViewer v-if="file" :file="file" :color="color ?? undefined" :still="still" class="absolute inset-0" />
    <div v-else class="flex h-full items-center justify-center">
      <Icon name="cube" class="size-8 text-zinc-700" />
    </div>
  </div>
</template>
