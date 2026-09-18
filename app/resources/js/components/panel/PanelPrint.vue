<script setup>
import { computed, onMounted, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useFileStore } from '../../stores/files';
import { useFilamentStore } from '../../stores/filament';
import { useToastStore } from '../../stores/toasts';
import { activityLabel } from '../job/activity';
import { stripGcodeExtension } from '../../format';
import JobModel from '../job/JobModel.vue';
import JobStateBadge from '../job/JobStateBadge.vue';
import JobStats from '../job/JobStats.vue';
import PanelButton from './PanelButton.vue';
import ProgressRing from './ProgressRing.vue';
import SlideToConfirm from './SlideToConfirm.vue';

/* The running print: the part across the top, the ring with the percent, name and state, the
   clocks, pause and a slider to cancel. */
const emit = defineEmits(['navigate']);

const printer = usePrinterStore();
const files = useFileStore();
const filament = useFilamentStore();
const toasts = useToastStore();
const pending = ref(false);

onMounted(() => {
  if (!files.items.length) files.load().catch(() => {});
  filament.ensure().catch(() => {});
});

const job = computed(() => printer.job);
const file = computed(() => (job.value?.file_id == null ? null : (files.items.find((item) => item.id === job.value.file_id) ?? null)));
const spool = computed(() => filament.current);
const active = computed(() => ['printing', 'paused', 'cancelling'].includes(job.value?.state));
const preparing = computed(() => job.value?.state === 'printing' && Boolean(job.value?.activity));
const percent = computed(() => Math.round((job.value?.progress ?? 0) * 100));
const TONES = { printing: 'emerald', paused: 'amber', cancelling: 'amber', finished: 'emerald', cancelled: 'zinc', error: 'red' };
const tone = computed(() => (preparing.value ? 'sky' : (TONES[job.value?.state] ?? 'zinc')));
const layer = computed(() => {
  const j = job.value;
  if (!j?.layer) return null;
  return j.total_layers ? `${j.layer} / ${j.total_layers}` : String(j.layer);
});

async function run(action, message = null) {
  pending.value = true;
  try {
    await printer[action]();
    if (message) toasts.info(message);
  } catch (error) {
    toasts.error(error.message);
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <div v-if="!job" class="flex h-full flex-col items-center justify-center gap-5 text-zinc-500">
    <span class="text-2xl">No active print</span>
    <PanelButton icon="folder" @click="emit('navigate', 'files')">Choose a file</PanelButton>
  </div>

  <div v-else class="flex h-full flex-col gap-3">
    <JobModel v-if="file" :file="file" :color="spool?.color" still class="h-40 w-full shrink-0" />

    <div class="flex min-h-0 flex-1 items-center gap-5">
      <ProgressRing :value="preparing ? null : job.progress" :size="190" :stroke="12" :tone="tone">
        <span v-if="preparing" class="text-lg font-semibold text-sky-300">{{ activityLabel(job.activity) }}</span>
        <template v-else>
          <span class="text-5xl leading-none font-semibold tabular-nums">{{ percent }}<span class="text-2xl text-zinc-500">%</span></span>
          <span v-if="layer" class="mt-1.5 text-sm text-zinc-500 tabular-nums">Layer {{ layer }}</span>
        </template>
      </ProgressRing>

      <div class="flex h-full min-w-0 flex-1 flex-col justify-between py-1">
        <div class="flex items-center gap-3">
          <span class="min-w-0 flex-1 truncate text-xl font-semibold" :title="job.name">{{ stripGcodeExtension(job.name) }}</span>
          <JobStateBadge :state="job.state" :preparing="preparing" :activity="job.activity" />
        </div>

        <JobStats :job="job" :received-at="printer.receivedAt" size="lg" />

        <div class="flex flex-col gap-3">
          <template v-if="active">
            <div class="grid grid-cols-2 gap-3">
              <PanelButton v-if="job.state === 'paused'" variant="primary" icon="play" :disabled="pending" @click="run('resumeJob')">Resume</PanelButton>
              <PanelButton v-else icon="pause" :disabled="pending || job.state !== 'printing' || job.activity === 'pausing'" @click="run('pauseJob')">Pause</PanelButton>
              <PanelButton icon="camera" @click="emit('navigate', 'camera')">Camera</PanelButton>
            </div>
            <SlideToConfirm :label="job.state === 'cancelling' ? 'Cancelling…' : 'Slide to cancel'" icon="stop" :disabled="pending || job.state === 'cancelling'" @confirm="run('cancelJob', 'Cancelling the print')" />
          </template>
          <div v-else class="grid grid-cols-2 gap-3">
            <PanelButton variant="primary" icon="refresh" :disabled="pending || !printer.connected" @click="run('restartJob', `${job.name} started`)">Print again</PanelButton>
            <PanelButton icon="folder" @click="emit('navigate', 'files')">Files</PanelButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
