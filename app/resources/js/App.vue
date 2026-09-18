<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { usePrinterStore } from './stores/printer';
import { useSessionStore } from './stores/session';
import { useSystemStore } from './stores/system';
import { useUpdatesStore } from './stores/updates';
import { useSettingsStore } from './stores/settings';
import { useFirmwareStore } from './stores/firmware';
import { usePrintStartStore } from './stores/printStart';
import { useFilamentChangeStore } from './stores/filamentChange';
import { useTabProgress } from './composables/useTabProgress';
import { useToastStore } from './stores/toasts';
import AppSidebar from './components/AppSidebar.vue';
import FilamentFlowModal from './components/filament/flow/FilamentFlowModal.vue';
import FirmwareOverlay from './components/FirmwareOverlay.vue';
import RestartOverlay from './components/RestartOverlay.vue';
import StartPrintModal from './components/prints/StartPrintModal.vue';
import StatusBar from './components/StatusBar.vue';
import ConfirmModal from './components/ConfirmModal.vue';
import ToastList from './components/ToastList.vue';
import UpdateOverlay from './components/UpdateOverlay.vue';

const route = useRoute();
const router = useRouter();
const printer = usePrinterStore();
const session = useSessionStore();
const system = useSystemStore();
const updates = useUpdatesStore();
const settings = useSettingsStore();
const firmware = useFirmwareStore();
const printStart = usePrintStartStore();
const filamentChange = useFilamentChangeStore();
const toasts = useToastStore();

const bare = computed(() => Boolean(route.meta.bare));
useTabProgress(() => printer.job);

watch(
  () => session.authenticated && !system.pending,
  (active, previous, onCleanup) => {
    let cancelled = false;
    onCleanup(() => {
      cancelled = true;
      updates.stop();
      firmware.stop();
    });
    if (!active) {
      updates.stop();
      firmware.stop();
      return;
    }
    updates.load().then(() => {
      if (!cancelled && updates.inProgress) updates.track();
    }).catch(() => {});
    // The switches for toasts, the tab and the postcard live in the settings.
    settings.load().catch(() => {});
    // A firmware flash that runs on while the page loads gets its overlay back.
    firmware.load().then(() => {
      if (!cancelled && firmware.inProgress) firmware.track();
    }).catch(() => {});
  },
  { immediate: true },
);

// No printer polling while the host restarts or updates; the overlay reloads the page once it is back.
watch(
  () => session.authenticated && !system.pending && !updates.tracking,
  (poll) => (poll ? printer.startPolling() : printer.stopPolling()),
  { immediate: true },
);

const ENDINGS = { finished: 'finished', cancelled: 'was cancelled', error: 'failed' };
watch(
  () => [printer.job?.id, printer.job?.state],
  ([id, state], [previousId, previousState]) => {
    if (id !== previousId || !ENDINGS[state] || ENDINGS[previousState] || settings.values.notify_print_end === false) return;
    const message = `${printer.job.name} ${ENDINGS[state]}`;
    if (state === 'finished') toasts.success(message);
    else toasts.error(message);
  },
);

function onUnauthenticated() {
  if (!session.user) return;
  session.clear();
  toasts.info('Session expired, please sign in again.');
  router.push({ name: 'login' });
}

onMounted(() => window.addEventListener('printpi:unauthenticated', onUnauthenticated));
onUnmounted(() => {
  window.removeEventListener('printpi:unauthenticated', onUnauthenticated);
  printer.stopPolling();
  updates.stop();
  firmware.stop();
});
</script>

<template>
  <RouterView v-if="bare" />
  <div v-else class="flex min-h-screen">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <StatusBar />
      <main class="flex-1 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        <RouterView />
      </main>
    </div>
  </div>
  <ToastList />
  <ConfirmModal />
  <StartPrintModal v-if="printStart.file && !route.meta.panel" />
  <FilamentFlowModal v-if="filamentChange.visible && !route.meta.panel" />
  <RestartOverlay v-if="system.pending" :action="system.pending" />
  <UpdateOverlay v-else-if="updates.tracking" />
  <FirmwareOverlay v-else-if="firmware.tracking" />
</template>
