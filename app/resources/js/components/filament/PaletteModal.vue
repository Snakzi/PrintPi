<script setup>
import { computed, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import CanvasShareActions from '../CanvasShareActions.vue';
import Modal from '../Modal.vue';
import PaletteCanvas from './PaletteCanvas.vue';

/* The colour card of the active spools, ready to share or save. */
const emit = defineEmits(['close']);

const filament = useFilamentStore();
const canvas = ref(null);
const spools = computed(() => filament.active);
</script>

<template>
  <Modal @close="emit('close')">
    <template #title>
      <h2 class="font-medium">Colour card</h2>
    </template>
    <div class="flex max-h-[80vh] flex-col gap-4 overflow-y-auto p-4">
      <PaletteCanvas :spools="spools" @rendered="canvas = $event" />
      <CanvasShareActions :canvas="canvas" name="filament-colours" save-label="Save card" />
    </div>
  </Modal>
</template>
