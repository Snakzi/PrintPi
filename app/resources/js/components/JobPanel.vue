<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useFileStore } from '../stores/files';
import { useFilamentStore } from '../stores/filament';
import { usePrinterStore } from '../stores/printer';
import { usePrintStore } from '../stores/prints';
import { useToastStore } from '../stores/toasts';
import { gramsNeeded } from '../filament/spools';
import AppButton from './AppButton.vue';
import JobControls from './job/JobControls.vue';
import JobHeader from './job/JobHeader.vue';
import JobModel from './job/JobModel.vue';
import JobProgress from './job/JobProgress.vue';
import JobSpool from './job/JobSpool.vue';
import JobStats from './job/JobStats.vue';
import PostcardModal from './prints/PostcardModal.vue';
import WidgetEmpty from './dashboard/WidgetEmpty.vue';

/** embedded: rendered inside a dashboard widget frame that already provides card and title. */
defineProps({ embedded: { type: Boolean, default: false } });

const printer = usePrinterStore();
const files = useFileStore();
const filament = useFilamentStore();
const prints = usePrintStore();
const toasts = useToastStore();
const job = computed(() => printer.job);
const postcard = ref(null);

// The daemon files the record once the timelapse is assembled, a moment after the job ended.
async function openPostcard() {
  try {
    const print = await prints.find(job.value.id);
    if (print) postcard.value = print;
    else toasts.info('The postcard is still being prepared');
  } catch (error) {
    toasts.error(error.message);
  }
}

// The thumbnail comes from the file row; a missing list only costs the picture.
onMounted(() => {
  if (!files.items.length) files.load().catch(() => {});
  filament.ensure().catch(() => {});
});
const file = computed(() => (job.value?.file_id == null ? null : (files.items.find((item) => item.id === job.value.file_id) ?? null)));

// The spool counts down from what the file needs; once the job has ended the history books it
// on the spool a moment later, so the inventory is fetched again then.
const spool = computed(() => filament.current);
const needed = computed(() => gramsNeeded(file.value?.metadata ?? null, spool.value));
watch(
  () => job.value?.state,
  (state, previous) => {
    if (!previous || !['finished', 'cancelled', 'error'].includes(state)) return;
    [6000, 20000].forEach((delay) => setTimeout(() => filament.load().catch(() => {}), delay));
  },
);

// Heating, levelling and the purge line come before the first layer.
const preparing = computed(() => job.value?.state === 'printing' && Boolean(job.value.activity));
</script>

<template>
  <section class="flex h-full flex-col" :class="embedded ? '' : 'rounded-lg border border-zinc-800 bg-zinc-900 p-4'">
    <h2 v-if="!embedded" class="mb-3 text-sm font-semibold tracking-wide text-zinc-400 uppercase">Print job</h2>

    <div v-if="job" class="flex min-h-0 flex-1 flex-col gap-3">
      <!-- The part sits beside name and progress, centred on them; a widget too narrow for both stacks it on top. -->
      <div class="flex flex-1 flex-col gap-3 @min-[14rem]:flex-row @min-[14rem]:items-center">
        <JobModel
          :file="file"
          :color="spool?.color"
          class="min-h-24 flex-1 @min-[14rem]:aspect-square @min-[14rem]:min-h-0 @min-[14rem]:w-[min(40%,9rem)] @min-[14rem]:max-h-full @min-[14rem]:flex-none"
        />
        <div class="flex min-w-0 flex-col gap-3 @min-[14rem]:flex-1">
          <JobHeader :job="job" :preparing="preparing" />
          <JobProgress :job="job" :preparing="preparing" />
        </div>
      </div>

      <JobStats :job="job" :received-at="printer.receivedAt" />

      <JobSpool v-if="spool" :job="job" :spool="spool" :needed="needed" />

      <p v-if="job.error" class="text-xs text-red-400">{{ job.error }}</p>

      <JobControls :job="job" class="mt-auto" @postcard="openPostcard" />
    </div>

    <WidgetEmpty v-else icon="layers" message="No active print">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'files' }" custom>
        <AppButton size="sm" variant="ghost" icon="folder" @click="navigate">Files</AppButton>
      </RouterLink>
    </WidgetEmpty>

    <PostcardModal v-if="postcard" :print="postcard" @close="postcard = null" />
  </section>
</template>
