<script setup>
import { computed } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { activityLabel } from '../job/activity';
import { formatHms, stripGcodeExtension } from '../../format';
import ProgressBar from '../ProgressBar.vue';

/* One line about the print at the bottom of the home screen; a tap opens the print screen. */
const emit = defineEmits(['open']);
const printer = usePrinterStore();

const job = computed(() => printer.job);
const preparing = computed(() => job.value?.state === 'printing' && Boolean(job.value?.activity));
const percent = computed(() => Math.round((job.value?.progress ?? 0) * 100));
const TONES = { printing: 'emerald', paused: 'amber', cancelling: 'amber', finished: 'emerald', cancelled: 'zinc', error: 'red' };
const LABELS = { printing: 'Printing', paused: 'Paused', cancelling: 'Cancelling', finished: 'Finished', cancelled: 'Cancelled', error: 'Failed' };
const state = computed(() => (preparing.value ? activityLabel(job.value.activity) : LABELS[job.value?.state] ?? ''));
const remaining = computed(() => (['printing', 'paused'].includes(job.value?.state) && job.value.remaining != null ? `${formatHms(job.value.remaining)} left` : null));
</script>

<template>
  <button v-if="job" type="button" class="flex w-full flex-col justify-center gap-2 rounded-2xl bg-zinc-900 px-4 py-3 text-left active:bg-zinc-800" @click="emit('open')">
    <div class="flex items-baseline justify-between gap-3">
      <span class="truncate text-base font-medium">{{ stripGcodeExtension(job.name) }}</span>
      <span class="shrink-0 text-sm text-zinc-400 tabular-nums">{{ state }} · {{ percent }} %<template v-if="remaining"> · {{ remaining }}</template></span>
    </div>
    <ProgressBar :value="preparing ? null : job.progress" :tone="preparing ? 'sky' : (TONES[job.state] ?? 'zinc')" size="sm" full />
  </button>
  <div v-else class="flex items-center gap-3 rounded-2xl bg-zinc-900 px-4 py-3 text-sm text-zinc-500">
    <span class="truncate">{{ printer.connected ? `${printer.machineType ?? 'Printer'} · ${printer.printer.port}` : 'No printer connected' }}</span>
  </div>
</template>
