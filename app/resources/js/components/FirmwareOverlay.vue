<script setup>
import { computed } from 'vue';
import { useFirmwareStore } from '../stores/firmware';
import AppButton from './AppButton.vue';
import BlockingOverlay from './BlockingOverlay.vue';
import ProgressBar from './ProgressBar.vue';

const firmware = useFirmwareStore();
const LOG_LINES = 8;

const file = computed(() => firmware.status?.file);
const restart = computed(() => firmware.status?.method === 'restart');
const changed = computed(() => firmware.status?.firmware_before !== firmware.status?.firmware_after);
const title = computed(() => {
  if (firmware.failed) return restart.value ? 'Restart failed' : 'Firmware update failed';
  if (firmware.done) return changed.value ? 'Firmware updated' : 'Printer restarted';
  if (restart.value) return 'Restarting the printer';
  return file.value ? `Flashing ${file.value}` : 'Updating the printer firmware';
});
const detail = computed(() => {
  if (firmware.failed) return firmware.status?.error ?? 'The daemon reported no reason.';
  if (firmware.done) return firmware.status?.firmware_after ?? 'The printer is back';
  return `${firmware.progressLabel || 'Please wait'}…`;
});
const tone = computed(() => (firmware.failed ? 'error' : firmware.done ? 'success' : 'neutral'));
const progress = computed(() => (firmware.inProgress ? firmware.status?.progress ?? null : null));
const log = computed(() => (firmware.status?.log ?? []).slice(-LOG_LINES));
</script>

<template>
  <BlockingOverlay :title="title" :detail="detail" :tone="tone" :busy="firmware.inProgress">
    <ProgressBar v-if="progress !== null" :value="progress" />
    <p v-if="firmware.done && changed && firmware.status?.firmware_before" class="text-xs text-zinc-500">was {{ firmware.status.firmware_before }}</p>
    <pre v-if="log.length" class="max-h-40 w-full max-w-lg overflow-hidden rounded-md bg-zinc-900 p-3 text-left font-mono text-xs leading-5 text-zinc-400">{{ log.join('\n') }}</pre>
    <AppButton v-if="!firmware.inProgress" @click="firmware.dismiss()">Close</AppButton>
  </BlockingOverlay>
</template>
