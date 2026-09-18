<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue';
import { usePrinterStore } from '../stores/printer';
import { formatTemp, formatTime, sensorLabel } from '../format';
import IconButton from './IconButton.vue';
import WidgetActions from './dashboard/WidgetActions.vue';
import WidgetEmpty from './dashboard/WidgetEmpty.vue';

/** embedded: rendered inside a dashboard widget frame that already provides card and title. */
defineProps({ embedded: { type: Boolean, default: false } });

const printer = usePrinterStore();
const container = ref(null);
const width = ref(640);
const height = ref(200);
const margin = { top: 10, right: 12, bottom: 22, left: 34 };
const WINDOW_MS = 10 * 60 * 1000;
const gradient = `chart-${useId()}`;

const SERIES = [
  { key: 'T0', color: 'var(--color-series-hotend)' },
  { key: 'B', color: 'var(--color-series-bed)' },
  { key: 'C', color: 'var(--color-series-chamber)' },
];

const hoverIndex = ref(null);
const showTable = ref(false);

// The plot fills its box, so the SVG follows the container in both directions.
let observer;
onMounted(() => {
  observer = new ResizeObserver((entries) => {
    const rect = entries[0].contentRect;
    width.value = Math.max(240, Math.floor(rect.width));
    height.value = Math.max(120, Math.floor(rect.height));
  });
  observer.observe(container.value);
});
onBeforeUnmount(() => observer?.disconnect());

const history = computed(() => printer.history);
const latest = computed(() => history.value[history.value.length - 1] ?? null);
const now = computed(() => latest.value?.t ?? Date.now());
const series = computed(() => SERIES.filter((entry) => history.value.some((sample) => sample.temps[entry.key])));

const yMax = computed(() => {
  let max = 0;
  for (const sample of history.value) {
    for (const entry of series.value) {
      const reading = sample.temps[entry.key];
      if (reading) max = Math.max(max, reading.actual ?? 0, reading.target ?? 0);
    }
  }
  return Math.max(100, Math.ceil((max + 15) / 50) * 50);
});

const plotWidth = computed(() => width.value - margin.left - margin.right);
const plotHeight = computed(() => height.value - margin.top - margin.bottom);
const baseline = computed(() => margin.top + plotHeight.value);
const x = (t) => margin.left + ((t - (now.value - WINDOW_MS)) / WINDOW_MS) * plotWidth.value;
const y = (value) => margin.top + plotHeight.value - (value / yMax.value) * plotHeight.value;

/** Continuous runs of points; a missing reading breaks the line instead of bridging the gap. */
function runs(key, field) {
  const result = [];
  let current = null;
  for (const sample of history.value) {
    const value = sample.temps[key]?.[field];
    if (value == null) {
      current = null;
      continue;
    }
    if (!current) result.push((current = []));
    current.push([x(sample.t), y(value)]);
  }
  return result;
}

function linePath(key, field) {
  return runs(key, field)
    .map((run) => run.map(([px, py], index) => `${index ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join(''))
    .join('');
}

function areaPath(key) {
  return runs(key, 'actual')
    .filter((run) => run.length > 1)
    .map((run) => {
      const line = run.map(([px, py], index) => `${index ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('');
      const [firstX] = run[0];
      const [lastX] = run[run.length - 1];
      return `${line}L${lastX.toFixed(1)},${baseline.value}L${firstX.toFixed(1)},${baseline.value}Z`;
    })
    .join('');
}

const yTicks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(yMax.value * fraction)));
const xTicks = computed(() =>
  [10, 8, 6, 4, 2, 0].map((minutes) => ({ t: now.value - minutes * 60000, label: minutes ? `−${minutes} min` : 'now' })),
);

function onMove(event) {
  if (!history.value.length) return;
  const rect = event.currentTarget.getBoundingClientRect();
  const t = now.value - WINDOW_MS + ((event.clientX - rect.left - margin.left) / plotWidth.value) * WINDOW_MS;
  let best = 0;
  let bestDistance = Infinity;
  history.value.forEach((sample, index) => {
    const distance = Math.abs(sample.t - t);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = index;
    }
  });
  hoverIndex.value = best;
}

const hovered = computed(() => (hoverIndex.value === null ? null : history.value[hoverIndex.value]));
const TOOLTIP_WIDTH = 156;
const tooltipX = computed(() => {
  if (!hovered.value) return 0;
  const px = x(hovered.value.t);
  return px + TOOLTIP_WIDTH + 12 > width.value ? px - TOOLTIP_WIDTH - 10 : px + 10;
});

const tableRows = computed(() => history.value.slice(-12).reverse());
</script>

<template>
  <section class="flex flex-col" :class="embedded ? 'h-full' : 'min-h-80 rounded-lg border border-zinc-800 bg-zinc-900 p-4'">
    <div :class="embedded ? 'contents' : 'mb-2 flex items-center gap-3'">
      <h2 v-if="!embedded" class="text-sm font-semibold tracking-wide text-zinc-400 uppercase">Temperature history</h2>
      <WidgetActions>
        <IconButton icon="trending" title="Chart" :active="!showTable" @click="showTable = false" />
        <IconButton icon="list" title="Table" :active="showTable" @click="showTable = true" />
      </WidgetActions>
    </div>

    <div ref="container" class="relative min-h-36 flex-1">
      <WidgetEmpty v-if="history.length < 2" icon="trending" message="No data yet" class="absolute inset-0" />

      <div v-else-if="showTable" class="absolute inset-0 overflow-auto">
        <table class="w-full text-left font-mono text-xs">
          <thead class="sticky top-0 bg-zinc-900 text-zinc-500">
            <tr>
              <th class="py-1 font-normal">Time</th>
              <th v-for="entry in series" :key="entry.key" class="py-1 text-right font-normal">{{ sensorLabel(entry.key) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sample in tableRows" :key="sample.t" class="border-t border-zinc-800">
              <td class="py-1 text-zinc-400">{{ formatTime(sample.t) }}</td>
              <td v-for="entry in series" :key="entry.key" class="py-1 text-right tabular-nums">
                {{ formatTemp(sample.temps[entry.key]?.actual) }}<span class="text-zinc-500"> / {{ formatTemp(sample.temps[entry.key]?.target, 0) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <svg
        v-else
        :width="width"
        :height="height"
        :viewBox="`0 0 ${width} ${height}`"
        class="absolute inset-0"
        role="img"
        aria-label="Temperature history"
        @mousemove="onMove"
        @mouseleave="hoverIndex = null"
      >
        <defs>
          <linearGradient v-for="entry in series" :id="`${gradient}-${entry.key}`" :key="entry.key" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" :stop-color="entry.color" stop-opacity="0.22" />
            <stop offset="1" :stop-color="entry.color" stop-opacity="0" />
          </linearGradient>
        </defs>

        <g v-for="tick in yTicks" :key="tick">
          <line :x1="margin.left" :x2="width - margin.right" :y1="y(tick)" :y2="y(tick)" class="stroke-zinc-800" />
          <text :x="margin.left - 6" :y="y(tick) + 3" text-anchor="end" class="fill-zinc-500 text-[10px] tabular-nums">{{ tick }}</text>
        </g>
        <text v-for="tick in xTicks" :key="tick.label" :x="x(tick.t)" :y="height - 6" text-anchor="middle" class="fill-zinc-500 text-[10px]">
          {{ tick.label }}
        </text>

        <g v-for="entry in series" :key="entry.key">
          <path :d="areaPath(entry.key)" :fill="`url(#${gradient}-${entry.key})`" />
          <path :d="linePath(entry.key, 'target')" fill="none" :stroke="entry.color" stroke-width="1.5" stroke-dasharray="3 4" opacity="0.55" stroke-linecap="round" />
          <path :d="linePath(entry.key, 'actual')" fill="none" :stroke="entry.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        </g>

        <g v-if="hovered">
          <line :x1="x(hovered.t)" :x2="x(hovered.t)" :y1="margin.top" :y2="baseline" class="stroke-zinc-600" stroke-dasharray="2 3" />
          <circle
            v-for="entry in series"
            :key="entry.key"
            :cx="x(hovered.t)"
            :cy="y(hovered.temps[entry.key]?.actual ?? 0)"
            r="3.5"
            :fill="entry.color"
            class="stroke-zinc-900"
            stroke-width="2"
          />
          <g :transform="`translate(${tooltipX}, ${margin.top})`">
            <rect :width="TOOLTIP_WIDTH" :height="18 + series.length * 15" rx="6" class="fill-zinc-950/95 stroke-zinc-700" />
            <text x="10" y="13" class="fill-zinc-400 text-[10px]">{{ formatTime(hovered.t) }}</text>
            <template v-for="(entry, index) in series" :key="entry.key">
              <circle cx="13" :cy="25 + index * 15" r="3" :fill="entry.color" />
              <text x="21" :y="28 + index * 15" class="fill-zinc-100 text-[11px] tabular-nums">
                {{ sensorLabel(entry.key) }} {{ formatTemp(hovered.temps[entry.key]?.actual) }} / {{ formatTemp(hovered.temps[entry.key]?.target, 0) }} °C
              </text>
            </template>
          </g>
        </g>
      </svg>
    </div>

    <div v-if="series.length" class="mt-2 flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 text-xs">
      <span v-for="entry in series" :key="entry.key" class="flex items-center gap-1.5">
        <span class="size-2 rounded-full" :style="{ background: entry.color }" />
        <span class="text-zinc-400">{{ sensorLabel(entry.key) }}</span>
        <span class="font-mono text-zinc-200 tabular-nums">{{ formatTemp(latest?.temps[entry.key]?.actual) }}</span>
        <span class="font-mono text-zinc-500 tabular-nums">/ {{ formatTemp(latest?.temps[entry.key]?.target, 0) }} °C</span>
      </span>
      <span class="ml-auto flex items-center gap-1.5 text-zinc-500">
        <span class="inline-block w-4 border-t border-dashed border-zinc-500" />
        Target
      </span>
    </div>
  </section>
</template>
