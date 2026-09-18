<script setup>
import { computed, defineAsyncComponent, onMounted, watch } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { usePrinterStore } from '../stores/printer';
import { usePrinterProfileStore } from '../stores/printerProfiles';
import { useSettingsStore } from '../stores/settings';
import { formatDateTime } from '../format';
import { formatMm, meshStats } from '../bedmesh';
import BedMeshGrid from './BedMeshGrid.vue';
import Icon from './Icon.vue';
import ProgressBar from './ProgressBar.vue';
import Spinner from './Spinner.vue';

// three.js only loads once there is a mesh to draw.
const BedMeshViewer = defineAsyncComponent(() => import('./BedMeshViewer.vue'));

/* A mesh control: the plugin's status under the control key is the bed mesh report
   { probing, error, tolerance, measured_at, source, step, step_index, step_count, points,
   points_total, rows?, cols?, z?, x?, y? } and the action probes the bed. */
const props = defineProps({
  control: { type: Object, required: true },
  value: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change']);

const plugins = usePluginStore();
const printer = usePrinterStore();
const settings = useSettingsStore();
const profiles = usePrinterProfileStore();

const report = computed(() => props.value ?? {});
const mesh = computed(() => (report.value.z ? report.value : null));
const stats = computed(() => (mesh.value ? meshStats(mesh.value) : null));
const tolerance = computed(() => Number(report.value.tolerance) || 0.1);
const probing = computed(() => Boolean(report.value.probing));
const progress = computed(() => (report.value.points_total ? Math.min(report.value.points / report.value.points_total, 1) : null));
const pointsLabel = computed(() => {
  if (!report.value.points) return null;
  return report.value.points_total ? `Point ${report.value.points} of ${report.value.points_total}` : `Point ${report.value.points}`;
});

// A probe changes by the second, so the page polls faster while one runs.
watch(probing, (running) => plugins.startPolling(running ? 1000 : 3000));
const measured = computed(() => {
  if (!report.value.measured_at) return null;
  const when = formatDateTime(new Date(report.value.measured_at * 1000).toISOString());
  return report.value.source === 'probe' ? `Probed ${when}` : `Reported by the printer ${when}`;
});
const bed = computed(() => {
  const profile = profiles.find(settings.values.printer_profile);
  return profile?.bed ? { ...profile.bed, centered: profile.type === 'delta' } : null;
});

onMounted(async () => {
  try {
    await Promise.all([settings.loaded ? null : settings.load(), profiles.load()]);
  } catch {
    // Without a profile the view spreads the mesh over its own extent.
  }
});

const figures = computed(() =>
  stats.value
    ? [
        ['Min', formatMm(stats.value.min)],
        ['Max', formatMm(stats.value.max)],
        ['Range', stats.value.range.toFixed(3)],
      ]
    : [],
);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        type="button"
        class="flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="disabled || !printer.connected || printer.printing || probing"
        @click="emit('change', null)"
      >
        <Icon name="play" class="size-4" />
        Probe bed
      </button>
      <span v-if="probing" class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-300">
        <Spinner size="size-4" />
        <span class="font-mono">{{ report.step }}</span>
        <span class="tabular-nums text-zinc-500">{{ report.step_index }} / {{ report.step_count }}</span>
        <span v-if="pointsLabel" class="tabular-nums">{{ pointsLabel }}</span>
      </span>
      <p v-else-if="report.error" class="text-sm text-red-400">{{ report.error }}</p>
      <p v-else-if="measured" class="text-sm text-zinc-400">{{ measured }}</p>
      <dl v-if="figures.length" class="ml-auto flex gap-4 text-sm tabular-nums">
        <div v-for="[label, value] in figures" :key="label" class="flex gap-1.5">
          <dt class="text-zinc-500">{{ label }}</dt>
          <dd class="text-zinc-200">{{ value }} mm</dd>
        </div>
      </dl>
    </div>
    <ProgressBar v-if="probing" :value="progress" class="w-full" />

    <template v-if="mesh">
      <BedMeshViewer :mesh="mesh" :tolerance="tolerance" :bed="bed" class="h-96 overflow-hidden rounded-md border border-zinc-800" />
      <BedMeshGrid :mesh="mesh" :tolerance="tolerance" :bed="bed" />
    </template>
    <p v-else class="text-sm text-zinc-500">No mesh yet.</p>
  </div>
</template>
