<script setup>
import { computed, defineAsyncComponent, onMounted, watch } from 'vue';
import { usePrinterBed } from '../../composables/usePrinterBed';
import { useFileStore } from '../../stores/files';
import { usePrinterStore } from '../../stores/printer';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';
import LivePreviewSummary from './LivePreviewSummary.vue';

// three.js only loads once a print exists.
const GcodeViewer = defineAsyncComponent(() => import('../GcodeViewer.vue'));

const printer = usePrinterStore();
const files = useFileStore();
const bed = usePrinterBed();

const job = computed(() => printer.job);
const file = computed(() => {
  const id = job.value?.file_id;
  return id == null ? null : (files.items.find((item) => item.id === id) ?? null);
});
// A new print of the same file starts at line 0 again, so the viewer is keyed by the start time.
const viewerKey = computed(() => `${job.value?.file_id}:${job.value?.started_at}`);

async function loadFiles() {
  try {
    await files.load();
  } catch {
    // The placeholder below covers a missing file list.
  }
}

onMounted(() => {
  if (!files.items.length) loadFiles();
});
watch(
  () => job.value?.file_id,
  (id) => {
    if (id != null && !files.items.some((item) => item.id === id)) loadFiles();
  },
);
</script>

<template>
  <WidgetEmpty v-if="!job" icon="cube" message="No active print" />
  <WidgetEmpty v-else-if="!file" icon="cube" message="File not available" />
  <div v-else class="flex h-full flex-col gap-2">
    <LivePreviewSummary :job="job" />
    <GcodeViewer
      :key="viewerKey"
      :file="file"
      :bed="bed"
      :printed-line="job.line"
      live
      class="min-h-56 flex-1 overflow-hidden rounded-md border border-zinc-800 bg-zinc-950"
    />
  </div>
</template>
