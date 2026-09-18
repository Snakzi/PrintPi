<script setup>
import { computed } from 'vue';
import { useNow } from '../../composables/useNow';
import { formatClock, formatHms } from '../../format';

/** receivedAt: when the job snapshot was fetched, so the clocks keep running between polls. */
const props = defineProps({
  job: { type: Object, required: true },
  receivedAt: { type: Number, default: null },
  size: { type: String, default: 'md' },
});

const now = useNow();

// Only a running print advances between polls; paused and finished jobs stand still.
const drift = computed(() => {
  if (props.job.state !== 'printing' || !props.receivedAt) return 0;
  return Math.max(0, (now.value - props.receivedAt) / 1000);
});

const elapsed = computed(() => props.job.elapsed + drift.value);
const active = computed(() => ['printing', 'paused', 'cancelling'].includes(props.job.state));
// The daemon holds the remaining time while the start G-code runs, so the clock must not run it down either.
const remaining = computed(() => (props.job.remaining == null ? null : Math.max(0, props.job.remaining - (props.job.activity ? 0 : drift.value))));
const finishAt = computed(() => (active.value && remaining.value != null ? formatClock(now.value + remaining.value * 1000) : null));
const endedAt = computed(() => (props.job.finished_at ? formatClock(props.job.finished_at * 1000) : null));

const cells = computed(() => {
  if (active.value) {
    return [
      ['Elapsed', formatHms(elapsed.value)],
      ['Remaining', formatHms(remaining.value)],
      ['Finish', finishAt.value ?? '–'],
    ];
  }
  return [
    ['Elapsed', formatHms(elapsed.value)],
    ['Started', formatClock(props.job.started_at * 1000)],
    [props.job.state === 'finished' ? 'Finished' : 'Stopped', endedAt.value ?? '–'],
  ];
});
</script>

<template>
  <dl class="grid grid-cols-[repeat(auto-fit,minmax(4.5rem,1fr))] gap-2">
    <div v-for="[label, value] in cells" :key="label" class="min-w-0">
      <dt class="truncate text-[11px] font-medium tracking-wide text-zinc-500 uppercase">{{ label }}</dt>
      <dd class="truncate font-medium text-zinc-100 tabular-nums" :class="size === 'lg' ? 'text-2xl' : 'text-sm'">{{ value }}</dd>
    </div>
  </dl>
</template>
