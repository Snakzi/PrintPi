<script setup>
import { computed, onBeforeUnmount, watch } from 'vue';
import { useUpdatesStore } from '../stores/updates';
import AppButton from './AppButton.vue';
import BlockingOverlay from './BlockingOverlay.vue';

const updates = useUpdatesStore();
// The new release serves a new frontend bundle, so the page reloads once the helper reports done.
const RELOAD_DELAY_MS = 1500;
// Polls fail for a moment while php-fpm restarts; a minute of failures is something else.
const STUCK_POLLS = 30;

const version = computed(() => updates.status?.version ?? '');
const rollback = computed(() => updates.status?.action === 'rollback');
const title = computed(() => {
  if (updates.failed) return rollback.value ? 'Rollback failed' : 'Update failed';
  if (updates.done) return `PrintPi ${version.value} installed`;
  return rollback.value ? `Rolling back to PrintPi ${version.value}` : `Installing PrintPi ${version.value}`;
});
const detail = computed(() => {
  if (updates.failed) return updates.status?.error ?? 'See update.log on the Raspberry Pi.';
  if (updates.done) return 'Reloading…';
  return `${updates.progressLabel || 'Please wait'}…`;
});
const tone = computed(() => (updates.failed ? 'error' : updates.done ? 'success' : 'neutral'));
const stuck = computed(() => updates.failedPolls >= STUCK_POLLS);

let reloadTimer = null;
function reload() {
  window.location.reload();
}

watch(
  () => updates.done,
  (done) => {
    if (done && !reloadTimer) reloadTimer = setTimeout(reload, RELOAD_DELAY_MS);
  },
  { immediate: true },
);
onBeforeUnmount(() => clearTimeout(reloadTimer));
</script>

<template>
  <BlockingOverlay :title="title" :detail="detail" :tone="tone" :busy="!updates.failed">
    <AppButton v-if="updates.failed" @click="updates.dismiss()">Close</AppButton>
    <AppButton v-else-if="stuck && !updates.done" @click="reload">Reload</AppButton>
  </BlockingOverlay>
</template>
