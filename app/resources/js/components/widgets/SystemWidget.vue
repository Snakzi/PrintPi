<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { formatBytes } from '../../format';
import { formatUptime } from '../../system/host';
import ProgressBar from '../ProgressBar.vue';
import StatTile from '../StatTile.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';

const printer = usePrinterStore();
const system = computed(() => printer.system);

const cores = computed(() => system.value?.cpu_count || 1);

const loadTone = computed(() => {
  const load = system.value?.load?.[0];
  if (load == null) return 'muted';
  if (load > cores.value) return 'danger';
  if (load > cores.value * 0.7) return 'warn';
  return 'default';
});

const cpuTone = computed(() => {
  const temperature = system.value?.cpu_temperature;
  if (temperature == null) return 'muted';
  if (temperature > 75) return 'danger';
  if (temperature > 65) return 'warn';
  return 'default';
});

function barTone(percent) {
  if (percent == null) return 'zinc';
  if (percent > 90) return 'red';
  if (percent > 75) return 'amber';
  return 'emerald';
}
</script>

<template>
  <WidgetEmpty v-if="!system" icon="chip" message="No data" />
  <div v-else class="flex h-full flex-col gap-2">
    <div class="grid grid-cols-2 gap-2">
      <StatTile label="CPU" :value="system.cpu_temperature != null ? system.cpu_temperature.toFixed(1) : null" unit="°C" :tone="cpuTone" />
      <StatTile label="Load" :tone="loadTone" :title="system.load ? `${system.load.map((value) => value.toFixed(2)).join(' · ')} on ${cores} cores` : ''">
        <template v-if="system.load">
          {{ system.load[0].toFixed(2) }}<span class="ml-1 text-xs font-normal text-zinc-500">/ {{ cores }}</span>
        </template>
        <template v-else>–</template>
      </StatTile>
    </div>

    <StatTile v-if="system.memory" label="Memory" :value="`${system.memory.used_percent} %`">
      <template #default>{{ system.memory.used_percent }} %<span class="ml-1 text-xs font-normal text-zinc-500">of {{ formatBytes(system.memory.total) }}</span></template>
      <template #footer>
        <ProgressBar :value="system.memory.used_percent / 100" :tone="barTone(system.memory.used_percent)" size="sm" full class="mt-1" />
      </template>
    </StatTile>

    <StatTile v-if="system.disk" label="Storage">
      <template #default>{{ formatBytes(system.disk.free) }}<span class="ml-1 text-xs font-normal text-zinc-500">free</span></template>
      <template #footer>
        <ProgressBar :value="system.disk.used_percent / 100" :tone="barTone(system.disk.used_percent)" size="sm" full class="mt-1" />
      </template>
    </StatTile>

    <div class="mt-auto flex items-center justify-between gap-3 text-xs text-zinc-500">
      <span class="truncate font-mono" :title="system.hostname">{{ system.hostname }}</span>
      <span class="shrink-0 tabular-nums">up {{ formatUptime(system.uptime_seconds) ?? '–' }}</span>
    </div>
  </div>
</template>
