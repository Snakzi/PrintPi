<script setup>
import { computed, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { formatTemp } from '../../format';
import JogPad from '../motion/JogPad.vue';
import PanelCameraSpot from './PanelCameraSpot.vue';
import PanelButton from './PanelButton.vue';
import PanelChips from './PanelChips.vue';
import PanelStat from './PanelStat.vue';

/* Jog, home, preheat and extrude with finger-sized controls; a camera spot between the jog pad
   and the distance shows the head on request. The controls are off while a print runs. */
const printer = usePrinterStore();
const toasts = useToastStore();

const step = ref(10);
const steps = [0.1, 1, 10, 50].map((value) => ({ value, label: String(value) }));
const FEED_XY = 3000;
const FEED_Z = 600;
const FEED_E = 300;
const MIN_EXTRUDE_TEMP = 170;
const PRESETS = [
  { label: 'PLA', hotend: 215, bed: 60 },
  { label: 'PETG', hotend: 240, bed: 85 },
  { label: 'ABS', hotend: 250, bed: 100 },
];

const locked = computed(() => !printer.connected || printer.printing);
// The controls go inert while a print runs; the camera stays bright and tappable.
const lock = computed(() => (locked.value ? 'pointer-events-none opacity-40' : ''));
const hotend = computed(() => printer.hotend);
const bed = computed(() => printer.bed);
const hot = computed(() => (hotend.value?.actual ?? 0) >= MIN_EXTRUDE_TEMP);

async function run(commands) {
  try {
    await printer.sendAll(commands);
  } catch (error) {
    toasts.error(error.message);
  }
}

const jog = (axis, direction) => run(['G91', `G1 ${axis}${(direction * step.value).toFixed(2)} F${axis === 'Z' ? FEED_Z : FEED_XY}`, 'G90']);
const home = (axes = '') => run([`G28 ${axes}`.trim()]);
const preheat = (preset) => run([`M104 S${preset.hotend}`, `M140 S${preset.bed}`]);
const coolDown = () => run(['M104 S0', 'M140 S0']);
const extrude = (direction) => run(['M83', `G1 E${(direction * 10).toFixed(1)} F${FEED_E}`, 'M82']);

function readout(reading) {
  if (!reading) return '–';
  const target = reading.target ? ` / ${formatTemp(reading.target, 0)}` : '';
  return `${formatTemp(reading.actual, 0)}${target}`;
}
</script>

<template>
  <!-- One definite row, or a picture in the camera spot would grow the row past the screen. -->
  <div class="grid h-full grid-cols-[17.25rem_1fr] grid-rows-1 gap-5">
    <div class="flex min-h-0 flex-col gap-3">
      <JogPad size="lg" :class="lock" @jog="jog" @home="home" />
      <PanelCameraSpot class="flex-1" />
      <PanelChips v-model="step" :options="steps" unit="mm" :class="lock" />
    </div>

    <div class="grid grid-rows-[auto_1fr_auto] gap-3" :class="lock">
      <div class="grid grid-cols-2 gap-4">
        <PanelStat label="Hotend" icon="nozzle" :value="readout(hotend)" unit="°C" :tone="hotend?.target ? 'warn' : 'default'" />
        <PanelStat label="Bed" icon="bed" :value="readout(bed)" unit="°C" :tone="bed?.target ? 'warn' : 'default'" />
      </div>

      <div class="grid grid-cols-4 gap-3 self-center">
        <PanelButton v-for="preset in PRESETS" :key="preset.label" icon="fire" @click="preheat(preset)">{{ preset.label }}</PanelButton>
        <PanelButton icon="power" @click="coolDown">Cool</PanelButton>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <PanelButton icon="arrow-down" :disabled="!hot" @click="extrude(1)">Extrude 10 mm</PanelButton>
        <PanelButton icon="arrow-up" :disabled="!hot" @click="extrude(-1)">Retract 10 mm</PanelButton>
        <PanelButton icon="home" @click="home()">Home all</PanelButton>
        <PanelButton icon="stop" @click="run(['M84'])">Motors off</PanelButton>
      </div>
    </div>
  </div>
</template>
