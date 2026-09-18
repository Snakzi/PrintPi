<script setup>
import { computed, ref, watch } from 'vue';
import { useTween } from '../../composables/useTween';
import { spoolDetail } from '../../filament/spools';
import { formatFilament, formatLength } from '../../format';
import SpoolGraphic from '../filament/SpoolGraphic.vue';

/* The spool a job prints from, with what is left on it counting down as the print advances:
   the stored remainder minus `needed` grams times the progress. The count-down stays after the
   job has ended until the stored remainder moves, which is the history booking the print. */
const props = defineProps({
  job: { type: Object, required: true },
  spool: { type: Object, required: true },
  needed: { type: Number, default: null },
});

const active = computed(() => ['printing', 'paused', 'cancelling'].includes(props.job.state));
// The stored remainder at the moment the job ended; null once it has changed or when the job was over already.
const baseline = ref(null);
watch(active, (isActive) => {
  baseline.value = isActive ? null : props.spool.remaining;
});
watch(
  () => props.spool.remaining,
  (value) => {
    if (baseline.value !== null && value !== baseline.value) baseline.value = null;
  },
);
const live = computed(() => active.value || baseline.value !== null);
const used = computed(() => (live.value && props.needed != null ? props.needed * (props.job.progress ?? 0) : null));
const remaining = computed(() => Math.max(0, props.spool.remaining - (used.value ?? 0)));
const shown = useTween(remaining);
const fraction = computed(() => (props.spool.weight ? Math.min(1, Math.max(0, shown.value / props.spool.weight)) : 0));
const millimetres = computed(() =>
  props.spool.remaining > 0 ? (props.spool.remaining_mm * shown.value) / props.spool.remaining : 0,
);
</script>

<template>
  <div class="flex items-center gap-3 rounded-md bg-zinc-950/60 px-3 py-2">
    <SpoolGraphic :color="spool.color" :finish="spool.finish" :fraction="fraction" :size="40" />
    <div class="min-w-0 flex-1">
      <div class="truncate text-sm font-medium text-zinc-100" :title="spool.name">{{ spool.name }}</div>
      <div class="truncate text-xs text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
    </div>
    <div class="shrink-0 text-right tabular-nums">
      <div class="text-sm font-semibold text-zinc-100">{{ formatFilament(shown, null) }}</div>
      <div class="text-xs" :class="used != null ? 'text-amber-300' : 'text-zinc-500'">
        {{ used != null ? `−${formatFilament(used, null)}` : formatLength(millimetres) }}
      </div>
    </div>
  </div>
</template>
