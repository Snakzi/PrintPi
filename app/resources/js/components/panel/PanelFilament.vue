<script setup>
import { computed, ref } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { useFilamentChangeStore } from '../../stores/filamentChange';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { formatTemp, formatWeight } from '../../format';
import { remainingFraction, spoolDetail } from '../../filament/spools';
import FilamentFlow from '../filament/flow/FilamentFlow.vue';
import Icon from '../Icon.vue';
import PanelButton from './PanelButton.vue';
import PanelFilamentPicker from './PanelFilamentPicker.vue';
import PanelStat from './PanelStat.vue';
import SpoolGraphic from '../filament/SpoolGraphic.vue';
import SpoolRemaining from '../filament/SpoolRemaining.vue';

/* The filament screen: the spool in the printer, the hotend, and Load, Change and Unload. A
   walkthrough that runs, started here or from the web app, takes the screen over. */
const printer = usePrinterStore();
const filament = useFilamentStore();
const change = useFilamentChangeStore();
const toasts = useToastStore();

filament.ensure().catch(() => {});

const picking = ref(false);
const spool = computed(() => filament.current);
const hotend = computed(() => printer.hotend);
const locked = computed(() => !change.available);

async function unload() {
  try {
    await change.unload();
  } catch (error) {
    toasts.error(error.message);
  }
}

function readout(reading) {
  if (!reading) return { value: null, sub: null, tone: 'muted' };
  const target = reading.target ?? 0;
  return { value: formatTemp(reading.actual, 0), sub: target ? `target ${formatTemp(target, 0)} °C` : 'off', tone: target ? 'warn' : 'default' };
}
</script>

<template>
  <FilamentFlow v-if="change.visible" touch />
  <PanelFilamentPicker v-else-if="picking" @close="picking = false" />
  <div v-else class="grid h-full grid-cols-[1fr_16rem] gap-4">
    <div class="flex min-h-0 flex-col items-center justify-center gap-4 rounded-2xl bg-zinc-900 p-6">
      <template v-if="spool">
        <SpoolGraphic :color="spool.color" :finish="spool.finish" :fraction="remainingFraction(spool)" :size="150" />
        <div class="flex w-full min-w-0 flex-col items-center gap-1">
          <div class="max-w-full truncate text-2xl font-semibold">{{ spool.name }}</div>
          <div class="max-w-full truncate text-base text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
        </div>
        <SpoolRemaining :spool="spool" class="w-64 max-w-full" />
      </template>
      <template v-else>
        <Icon name="spool" class="size-24 text-zinc-700" />
        <div class="text-2xl font-semibold text-zinc-400">No spool loaded</div>
      </template>
    </div>

    <div class="flex min-h-0 flex-col gap-3">
      <PanelStat label="Hotend" icon="nozzle" :value="readout(hotend).value" unit="°C" :sub="readout(hotend).sub" :tone="readout(hotend).tone" class="shrink-0" />
      <div class="mt-auto flex flex-col gap-3">
        <PanelButton variant="primary" icon="arrow-down" block :disabled="locked" @click="picking = true">{{ spool ? 'Change' : 'Load' }}</PanelButton>
        <PanelButton icon="arrow-up" block :disabled="locked" @click="unload">Unload</PanelButton>
      </div>
      <div v-if="printer.printing" class="shrink-0 text-center text-sm text-zinc-500">Printing</div>
      <div v-else-if="!printer.connected" class="shrink-0 text-center text-sm text-zinc-500">Not connected</div>
    </div>
  </div>
</template>
