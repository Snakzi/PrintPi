<script setup>
import { usePrinterStore } from '../../stores/printer';
import { useFilamentChangeStore } from '../../stores/filamentChange';
import { useToastStore } from '../../stores/toasts';
import HoldButton from './HoldButton.vue';
import Logo from '../Logo.vue';
import PanelRailButton from './PanelRailButton.vue';

/* The column on the left: logo with the printer's status dot, one button per screen, the
   emergency stop at the bottom behind a long press. */
defineProps({
  screens: { type: Array, required: true },
  current: { type: String, required: true },
});
const emit = defineEmits(['select']);

const printer = usePrinterStore();
const change = useFilamentChangeStore();
const toasts = useToastStore();

async function emergencyStop() {
  try {
    await printer.emergencyStop();
    toasts.error('Emergency stop sent');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <nav class="flex w-20 shrink-0 flex-col items-center gap-1 border-r border-zinc-900 py-3">
    <div class="relative mb-2">
      <Logo size="size-10" />
      <span class="absolute -right-1 -bottom-1 size-3 rounded-full ring-2 ring-zinc-950" :class="printer.statusDotClass" :title="printer.statusLabel" />
    </div>
    <PanelRailButton
      v-for="screen in screens"
      :key="screen.id"
      :icon="screen.icon"
      :label="screen.label"
      :active="screen.id === current"
      :badge="(screen.id === 'print' && printer.printing) || (screen.id === 'filament' && change.active)"
      @click="emit('select', screen.id)"
    />
    <div class="mt-auto">
      <HoldButton icon="warning" label="Stop" :disabled="!printer.connected" @hold="emergencyStop" />
    </div>
  </nav>
</template>
