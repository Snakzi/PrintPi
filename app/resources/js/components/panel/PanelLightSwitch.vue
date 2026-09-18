<script setup>
import { computed } from 'vue';
import { useConfirmedSwitch } from '../../composables/useConfirmedSwitch';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import PanelSwitch from './PanelSwitch.vue';

/* The printer's light, when a plugin reports one; the dot takes its colour while it is on. */
const printer = usePrinterStore();
const toasts = useToastStore();
const { on, pending, toggle } = useConfirmedSwitch(() => printer.light?.on, (next) => printer.setLight(next), 5000);

const color = computed(() => (typeof printer.light?.color === 'string' ? printer.light.color : null));

async function press() {
  try {
    await toggle();
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <PanelSwitch v-if="printer.light" icon="bulb" label="Light" :on="on" :color="color" :disabled="pending" @click="press" />
</template>
