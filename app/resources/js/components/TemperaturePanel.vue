<script setup>
import { usePrinterStore } from '../stores/printer';
import { useToastStore } from '../stores/toasts';
import { sensorLabel } from '../format';
import HeaterCard from './temperature/HeaterCard.vue';
import SensorChip from './temperature/SensorChip.vue';
import TemperaturePresets from './temperature/TemperaturePresets.vue';

/** embedded: rendered inside a dashboard widget frame that already provides card and title. */
defineProps({ embedded: { type: Boolean, default: false } });

const printer = usePrinterStore();
const toasts = useToastStore();

const heaters = [
  { key: 'T0', label: 'Hotend', icon: 'nozzle', gcode: 'M104', max: 300 },
  { key: 'B', label: 'Bed', icon: 'bed', gcode: 'M140', max: 130 },
];

const presets = [
  { label: 'PLA', hotend: 215, bed: 60 },
  { label: 'PETG', hotend: 240, bed: 85 },
  { label: 'ABS', hotend: 250, bed: 100 },
];

// Rethrows after the toast so the button that sent the command can show the failure too.
async function run(commands) {
  try {
    await printer.sendAll(commands);
  } catch (error) {
    toasts.error(error.message);
    throw error;
  }
}

const setTarget = (heater, target) => run([`${heater.gcode} S${target}`]);
const applyPreset = (preset) => run([`M104 S${preset.hotend}`, `M140 S${preset.bed}`]);
const coolDown = () => run(['M104 S0', 'M140 S0']);
</script>

<template>
  <section class="flex flex-col gap-3" :class="embedded ? 'h-full' : '@container rounded-lg border border-zinc-800 bg-zinc-900 p-4'">
    <h2 v-if="!embedded" class="text-sm font-semibold tracking-wide text-zinc-400 uppercase">Temperatures</h2>

    <div class="grid gap-3 @sm:grid-cols-2">
      <HeaterCard
        v-for="heater in heaters"
        :key="heater.key"
        :label="heater.label"
        :icon="heater.icon"
        :max="heater.max"
        :reading="printer.temperatures[heater.key] ?? null"
        @set="setTarget(heater, $event)"
      />
    </div>

    <div v-if="printer.extraSensors.length" class="flex flex-wrap gap-1.5">
      <SensorChip v-for="[key, value] in printer.extraSensors" :key="key" :label="sensorLabel(key)" :actual="value.actual" :target="value.target" />
    </div>

    <TemperaturePresets :presets="presets" :apply="applyPreset" :cool="coolDown" class="mt-auto" />
  </section>
</template>
