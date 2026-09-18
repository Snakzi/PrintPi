<script setup>
import { computed } from 'vue';
import { stripGcodeExtension } from '../../format';
import AppButton from '../AppButton.vue';
import CanvasShareActions from '../CanvasShareActions.vue';

/* Share or save the rendered card and the timelapse. canvas is the element PostcardCanvas drew;
   without `card` only the timelapse is offered. */
const props = defineProps({
  print: { type: Object, required: true },
  canvas: { type: Object, default: null },
  card: { type: Boolean, default: true },
});

const baseName = computed(() => stripGcodeExtension(props.print.name));
</script>

<template>
  <component :is="card ? CanvasShareActions : 'div'" v-bind="card ? { canvas, name: baseName, saveLabel: 'Save card' } : { class: 'flex flex-wrap gap-2' }">
    <a v-if="print.video_url" :href="print.video_url" :download="`${baseName}.mp4`">
      <AppButton :variant="card ? 'secondary' : 'primary'" icon="download">Save video</AppButton>
    </a>
    <a v-else-if="print.timelapse_url" :href="print.timelapse_url" :download="`${baseName}.gif`">
      <AppButton :variant="card ? 'secondary' : 'primary'" icon="download">Save timelapse</AppButton>
    </a>
  </component>
</template>
