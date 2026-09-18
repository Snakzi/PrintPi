<script setup>
import { computed } from 'vue';
import { useConfirmedSwitch } from '../../composables/useConfirmedSwitch';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import PanelSwitch from './PanelSwitch.vue';

/* The printer's plug, when a plugin reports one. Turning it off while a print runs would end
   the print, so the switch waits for the print instead of asking. */
const printer = usePrinterStore();
const toasts = useToastStore();
const { on, pending, toggle } = useConfirmedSwitch(() => printer.power?.on, (next) => printer.setPower(next));

const offline = computed(() => printer.power?.online === false);
const locked = computed(() => on.value && printer.printing);

async function press() {
  try {
    await toggle();
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <PanelSwitch v-if="printer.power" icon="power" label="Power" :on="on" :disabled="pending || offline || locked" @click="press" />
</template>
