<script setup>
import { onMounted, ref, watch } from 'vue';
import { HEIGHT, WIDTH, renderPostcard } from '../../postcard/render';

/* The postcard of a print, drawn onto a canvas. options: { energyPrice, currency, printerName }. */
const props = defineProps({
  print: { type: Object, required: true },
  options: { type: Object, default: () => ({}) },
});
const emit = defineEmits(['rendered']);

const canvas = ref(null);
const busy = ref(true);

async function draw() {
  if (!canvas.value) return;
  busy.value = true;
  await renderPostcard(canvas.value, props.print, props.options);
  busy.value = false;
  emit('rendered', canvas.value);
}

onMounted(draw);
watch(() => [props.print, props.options], draw, { deep: true });
</script>

<template>
  <div class="relative">
    <canvas ref="canvas" :width="WIDTH" :height="HEIGHT" class="block w-full rounded-xl" :class="busy ? 'opacity-50' : ''" />
  </div>
</template>
