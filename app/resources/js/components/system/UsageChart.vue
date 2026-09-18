<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue';
import { DAY, nearestIndex, panWindow, resolveWindow, timeTicks, visibleRuns, zoomWindow } from '../../charts/timeWindow';
import { useNow } from '../../composables/useNow';
import { formatClock } from '../../format';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';
import UsageLegend from './UsageLegend.vue';

/* CPU and memory over time with a zoomable window: the wheel zooms around the pointer, a horizontal
   wheel or a drag pans, two fingers pinch, a double click returns to the full day. `span` is the
   preset window in ms; it becomes null once the user zooms or pans on their own. */
const props = defineProps({
  points: { type: Array, required: true },
  interval: { type: Number, required: true },
  span: { type: Number, default: null },
});
const emit = defineEmits(['update:span']);

const SERIES = [
  { key: 'cpu', label: 'CPU', color: 'var(--color-series-cpu)' },
  { key: 'memory', label: 'Memory', color: 'var(--color-series-memory)' },
];
const margin = { top: 10, right: 12, bottom: 22, left: 40 };
const TOOLTIP_WIDTH = 132;
const clipId = `usage-clip-${useId()}`;
const gradientId = `usage-fill-${useId()}`;

const container = ref(null);
const width = ref(640);
const height = ref(200);
const now = useNow(15_000);
const window_ = ref({ span: props.span ?? DAY, to: null });
const hoverIndex = ref(null);

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

watch(
  () => props.span,
  (span) => {
    if (span != null) window_.value = { span, to: null };
  },
);

const plotWidth = computed(() => width.value - margin.left - margin.right);
const plotHeight = computed(() => height.value - margin.top - margin.bottom);
const baseline = computed(() => margin.top + plotHeight.value);
const range = computed(() => resolveWindow(window_.value, now.value));
const x = (t) => margin.left + ((t - range.value.from) / window_.value.span) * plotWidth.value;
const y = (value) => margin.top + plotHeight.value - (value / 100) * plotHeight.value;

const runs = computed(() =>
  Object.fromEntries(SERIES.map((entry) => [entry.key, visibleRuns(props.points, entry.key, range.value.from, range.value.to, props.interval)])),
);

const toPath = (run) => run.map(([t, value], index) => `${index ? 'L' : 'M'}${x(t).toFixed(1)},${y(value).toFixed(1)}`).join('');

function linePath(key) {
  return runs.value[key].map(toPath).join('');
}

function areaPath(key) {
  return runs.value[key]
    .filter((run) => run.length > 1)
    .map((run) => `${toPath(run)}L${x(run[run.length - 1][0]).toFixed(1)},${baseline.value}L${x(run[0][0]).toFixed(1)},${baseline.value}Z`)
    .join('');
}

const yTicks = [0, 25, 50, 75, 100];
const xTicks = computed(() => timeTicks(range.value.from, range.value.to, Math.floor(plotWidth.value / 72)));

function tickLabel(tick) {
  const date = new Date(tick.t);
  if (tick.midnight) return date.toLocaleDateString(undefined, { weekday: 'short' });
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

const latest = computed(() => props.points[props.points.length - 1] ?? null);
const rangeLabel = computed(() => `${formatClock(range.value.from)} – ${window_.value.to == null ? 'now' : formatClock(range.value.to)}`);

// ---- zoom and pan -------------------------------------------------------------------------

function fractionAt(clientX) {
  const rect = container.value.getBoundingClientRect();
  return (clientX - rect.left - margin.left) / plotWidth.value;
}

function apply(next) {
  window_.value = next;
  emit('update:span', null);
}

function onWheel(event) {
  event.preventDefault();
  const scale = event.deltaMode === 1 ? 16 : 1;
  if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
    apply(panWindow(window_.value, (event.deltaX * scale) / plotWidth.value, now.value));
  } else {
    apply(zoomWindow(window_.value, Math.exp(event.deltaY * scale * 0.002), fractionAt(event.clientX), now.value));
  }
}

const pointers = new Map();

function onPointerDown(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return;
  container.value.setPointerCapture(event.pointerId);
  pointers.set(event.pointerId, event.clientX);
}

function onPointerMove(event) {
  if (!pointers.has(event.pointerId)) {
    hover(event.clientX);
    return;
  }
  const previous = pointers.get(event.pointerId);
  pointers.set(event.pointerId, event.clientX);
  if (pointers.size === 1) {
    apply(panWindow(window_.value, -(event.clientX - previous) / plotWidth.value, now.value));
    hover(event.clientX);
    return;
  }
  // Two fingers: the distance between them scales the span, their midpoint drags it.
  const [a, b] = [...pointers.values()];
  const other = a === event.clientX ? b : a;
  const before = Math.abs(other - previous);
  const after = Math.abs(other - event.clientX);
  if (before < 1 || after < 1) return;
  const zoomed = zoomWindow(window_.value, before / after, fractionAt((other + event.clientX) / 2), now.value);
  apply(panWindow(zoomed, -((event.clientX - previous) / 2) / plotWidth.value, now.value));
}

function onPointerUp(event) {
  pointers.delete(event.pointerId);
  if (container.value?.hasPointerCapture(event.pointerId)) container.value.releasePointerCapture(event.pointerId);
  if (event.pointerType !== 'mouse') hoverIndex.value = null;
}

function hover(clientX) {
  if (!props.points.length) return;
  const t = range.value.from + fractionAt(clientX) * window_.value.span;
  const index = nearestIndex(props.points, t);
  const point = props.points[index];
  hoverIndex.value = point && point.t >= range.value.from && point.t <= range.value.to ? index : null;
}

function reset() {
  window_.value = { span: DAY, to: null };
  emit('update:span', DAY);
}

const hovered = computed(() => (hoverIndex.value === null ? null : props.points[hoverIndex.value]));
const tooltipX = computed(() => {
  if (!hovered.value) return 0;
  const px = x(hovered.value.t);
  return px + TOOLTIP_WIDTH + 12 > width.value ? px - TOOLTIP_WIDTH - 10 : px + 10;
});
const formatPercent = (value) => (value == null ? '–' : `${value.toFixed(1)} %`);
</script>

<template>
  <div class="flex h-full flex-col gap-2">
    <div ref="container" class="relative min-h-36 flex-1 touch-none select-none">
      <WidgetEmpty v-if="points.length < 2" icon="trending" message="No data yet" class="absolute inset-0" />
      <svg
        v-else
        :width="width"
        :height="height"
        :viewBox="`0 0 ${width} ${height}`"
        class="absolute inset-0 cursor-crosshair"
        role="img"
        aria-label="CPU and memory usage"
        @wheel="onWheel"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @pointerleave="hoverIndex = null"
        @dblclick="reset"
      >
        <defs>
          <clipPath :id="clipId">
            <rect :x="margin.left" :y="margin.top" :width="plotWidth" :height="plotHeight" />
          </clipPath>
          <linearGradient v-for="entry in SERIES" :id="`${gradientId}-${entry.key}`" :key="entry.key" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" :stop-color="entry.color" stop-opacity="0.2" />
            <stop offset="1" :stop-color="entry.color" stop-opacity="0" />
          </linearGradient>
        </defs>

        <g v-for="tick in yTicks" :key="tick">
          <line :x1="margin.left" :x2="width - margin.right" :y1="y(tick)" :y2="y(tick)" class="stroke-zinc-800" />
          <text :x="margin.left - 6" :y="y(tick) + 3" text-anchor="end" class="fill-zinc-500 text-[10px] tabular-nums">{{ tick }} %</text>
        </g>
        <g v-for="tick in xTicks" :key="tick.t">
          <line :x1="x(tick.t)" :x2="x(tick.t)" :y1="baseline" :y2="baseline + 4" class="stroke-zinc-700" />
          <text :x="x(tick.t)" :y="height - 6" text-anchor="middle" class="fill-zinc-500 text-[10px] tabular-nums" :class="{ 'fill-zinc-300': tick.midnight }">
            {{ tickLabel(tick) }}
          </text>
        </g>

        <g :clip-path="`url(#${clipId})`">
          <g v-for="entry in SERIES" :key="entry.key">
            <path :d="areaPath(entry.key)" :fill="`url(#${gradientId}-${entry.key})`" />
            <path :d="linePath(entry.key)" fill="none" :stroke="entry.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          </g>
        </g>

        <g v-if="hovered">
          <line :x1="x(hovered.t)" :x2="x(hovered.t)" :y1="margin.top" :y2="baseline" class="stroke-zinc-600" stroke-dasharray="2 3" />
          <template v-for="entry in SERIES" :key="entry.key">
            <circle v-if="hovered[entry.key] != null" :cx="x(hovered.t)" :cy="y(hovered[entry.key])" r="3.5" :fill="entry.color" class="stroke-zinc-900" stroke-width="2" />
          </template>
          <g :transform="`translate(${tooltipX}, ${margin.top})`">
            <rect :width="TOOLTIP_WIDTH" :height="18 + SERIES.length * 15" rx="6" class="fill-zinc-950/95 stroke-zinc-700" />
            <text x="10" y="13" class="fill-zinc-400 text-[10px]">{{ formatClock(hovered.t) }}</text>
            <template v-for="(entry, index) in SERIES" :key="entry.key">
              <line x1="10" x2="18" :y1="25 + index * 15" :y2="25 + index * 15" :stroke="entry.color" stroke-width="2" stroke-linecap="round" />
              <text x="24" :y="28 + index * 15" class="fill-zinc-100 text-[11px] tabular-nums">
                {{ formatPercent(hovered[entry.key]) }} <tspan class="fill-zinc-400">{{ entry.label }}</tspan>
              </text>
            </template>
          </g>
        </g>
      </svg>
    </div>
    <UsageLegend :series="SERIES" :latest="latest" :range="points.length > 1 ? rangeLabel : ''" />
  </div>
</template>
