<script setup>
import { onMounted, ref, watch } from 'vue';
import { renderPalette } from '../../filament/paletteRender';

/* The colour card of the given spools, drawn onto a canvas. */
const props = defineProps({ spools: { type: Array, required: true } });
const emit = defineEmits(['rendered']);

const canvas = ref(null);

function draw() {
  if (!canvas.value) return;
  renderPalette(canvas.value, props.spools);
  emit('rendered', canvas.value);
}

onMounted(draw);
watch(() => props.spools, draw, { deep: true });
</script>

<template>
  <canvas ref="canvas" class="block w-full rounded-xl" />
</template>
