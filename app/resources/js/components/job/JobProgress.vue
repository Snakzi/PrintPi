<script setup>
import { computed } from 'vue';
import { activityLabel } from './activity';
import ProgressBar from '../ProgressBar.vue';

/* Percent (or what the start G-code is doing), layer and the bar of a job. */
const props = defineProps({
  job: { type: Object, required: true },
  preparing: { type: Boolean, default: false },
});

const TONES = { printing: 'emerald', paused: 'amber', cancelling: 'amber', finished: 'emerald', cancelled: 'zinc', error: 'red' };
// Heating, levelling and the purge line come before the first layer; the bar sweeps in its own colour until then.
const tone = computed(() => (props.preparing ? 'sky' : (TONES[props.job.state] ?? 'zinc')));
const percent = computed(() => Math.round((props.job.progress ?? 0) * 100));
const layer = computed(() => {
  if (!props.job.layer) return null;
  return props.job.total_layers ? `${props.job.layer} / ${props.job.total_layers}` : String(props.job.layer);
});
</script>

<template>
  <div>
    <div class="flex items-baseline justify-between gap-2">
      <span v-if="preparing" class="text-2xl leading-none font-semibold tracking-tight text-zinc-50">{{ activityLabel(job.activity) }}</span>
      <span v-else class="text-2xl leading-none font-semibold tracking-tight text-zinc-50 tabular-nums">
        {{ percent }}<span class="ml-0.5 text-sm font-normal text-zinc-500">%</span>
      </span>
      <span v-if="layer" class="text-xs text-zinc-500 tabular-nums">Layer {{ layer }}</span>
    </div>
    <ProgressBar :value="preparing ? null : job.progress" :tone="tone" size="sm" full class="mt-2" />
  </div>
</template>
