<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { usePrinterStore } from '../stores/printer';
import { usePrintStartStore } from '../stores/printStart';
import { useFilamentChangeStore } from '../stores/filamentChange';
import PanelCamera from '../components/panel/PanelCamera.vue';
import PanelFilament from '../components/panel/PanelFilament.vue';
import PanelFiles from '../components/panel/PanelFiles.vue';
import PanelHome from '../components/panel/PanelHome.vue';
import PanelMove from '../components/panel/PanelMove.vue';
import PanelPrint from '../components/panel/PanelPrint.vue';
import PanelRail from '../components/panel/PanelRail.vue';
import PanelStartPrint from '../components/panel/PanelStartPrint.vue';

/* The touch screen at the printer: one screen at a time, chosen on the rail, nothing scrolls
   but the file grid. Made for 800×480 in landscape, a Pi's 7" display. */
const SCREENS = [
  { id: 'home', label: 'Home', icon: 'home', component: PanelHome },
  { id: 'print', label: 'Print', icon: 'layers', component: PanelPrint },
  { id: 'files', label: 'Files', icon: 'folder', component: PanelFiles },
  { id: 'filament', label: 'Filament', icon: 'spool', component: PanelFilament },
  { id: 'move', label: 'Move', icon: 'move', component: PanelMove },
  { id: 'camera', label: 'Camera', icon: 'camera', component: PanelCamera },
];

const printer = usePrinterStore();
const printStart = usePrintStartStore();
const change = useFilamentChangeStore();
const screen = ref('home');

// No terminal here, so the poll skips the serial log; the Pi's browser has little to spare.
printer.withSerial = false;
onBeforeUnmount(() => {
  printer.withSerial = true;
});
const current = computed(() => SCREENS.find((entry) => entry.id === screen.value) ?? SCREENS[0]);

// A print that starts pulls the panel onto its screen, a filament walkthrough onto its own.
watch(
  () => printer.job?.id,
  (id, previous) => {
    if (id && id !== previous && printer.printing) screen.value = 'print';
  },
);
watch(
  () => change.current?.id,
  (id, previous) => {
    if (id && id !== previous && change.active) screen.value = 'filament';
  },
);
</script>

<template>
  <div class="panel flex h-dvh w-screen overflow-hidden overscroll-none bg-zinc-950 text-zinc-100" style="touch-action: manipulation" @contextmenu.prevent>
    <PanelRail :screens="SCREENS" :current="screen" @select="screen = $event" />
    <main class="min-w-0 flex-1 overflow-hidden p-4">
      <!-- The spool question takes the screen over instead of opening the web app's modal. -->
      <PanelStartPrint v-if="printStart.file" />
      <component :is="current.component" v-else @navigate="screen = $event" />
    </main>
  </div>
</template>
