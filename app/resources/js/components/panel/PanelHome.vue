<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useFilamentStore } from '../../stores/filament';
import { useCameraSource } from '../../composables/useCameraSource';
import { formatTemp, formatWeight } from '../../format';
import { remainingFraction, spoolDetail } from '../../filament/spools';
import CameraSnapshot from '../camera/CameraSnapshot.vue';
import CameraStream from '../camera/CameraStream.vue';
import Icon from '../Icon.vue';
import PanelClock from './PanelClock.vue';
import PanelJobStrip from './PanelJobStrip.vue';
import PanelLightSwitch from './PanelLightSwitch.vue';
import PanelPowerSwitch from './PanelPowerSwitch.vue';
import PanelStatusPill from './PanelStatusPill.vue';
import PanelStat from './PanelStat.vue';
import SpoolGraphic from '../filament/SpoolGraphic.vue';

/* The screen at rest: the time, what the printer is doing, both heaters, the loaded spool and the camera. */
const emit = defineEmits(['navigate']);

const printer = usePrinterStore();
const filament = useFilamentStore();
const { src, snapshot } = useCameraSource();

filament.ensure().catch(() => {});

const spool = computed(() => filament.current);

function heater(reading) {
  if (!reading) return { value: null, sub: null, tone: 'muted' };
  const target = reading.target ?? 0;
  return {
    value: formatTemp(reading.actual, 0),
    sub: target ? `target ${formatTemp(target, 0)} °C` : 'off',
    tone: target ? 'warn' : 'default',
  };
}
const hotend = computed(() => heater(printer.hotend));
const bed = computed(() => heater(printer.bed));
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <div class="flex shrink-0 items-center justify-between gap-3">
      <PanelClock />
      <div class="flex items-center gap-2">
        <PanelLightSwitch />
        <PanelPowerSwitch />
        <PanelStatusPill />
      </div>
    </div>

    <div class="grid shrink-0 grid-cols-3 gap-3">
      <PanelStat label="Hotend" icon="nozzle" :value="hotend.value" unit="°C" :sub="hotend.sub" :tone="hotend.tone" />
      <PanelStat label="Bed" icon="bed" :value="bed.value" unit="°C" :sub="bed.sub" :tone="bed.tone" />
      <button type="button" class="min-w-0 text-left active:opacity-80" @click="emit('navigate', 'filament')">
        <PanelStat label="Spool" icon="spool" :sub="spool ? spoolDetail(spool) : null" :tone="spool ? 'default' : 'muted'" class="h-full">
          <div v-if="spool" class="flex items-center gap-3">
            <SpoolGraphic :color="spool.color" :finish="spool.finish" :fraction="remainingFraction(spool)" :size="40" />
            <span class="truncate text-2xl">{{ formatWeight(spool.remaining) }}</span>
          </div>
          <span v-else class="text-2xl">None</span>
          <template v-if="spool" #sub>{{ spool.name }}</template>
        </PanelStat>
      </button>
    </div>

    <button
      type="button"
      class="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-2xl bg-zinc-900"
      :class="{ 'active:bg-zinc-800': src }"
      @click="src && emit('navigate', 'camera')"
    >
      <CameraSnapshot v-if="snapshot" :src="snapshot" :interval="1000" />
      <CameraStream v-else-if="src" :src="src" />
      <span v-else class="flex items-center gap-2 text-zinc-600"><Icon name="camera" class="size-8" /> No camera</span>
    </button>

    <PanelJobStrip class="shrink-0" @open="emit('navigate', 'print')" />
  </div>
</template>
