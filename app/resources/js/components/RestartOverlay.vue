<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from '../api';
import BlockingOverlay from './BlockingOverlay.vue';

const props = defineProps({
  action: { type: String, required: true, validator: (value) => ['reboot', 'restart'].includes(value) },
});

const TITLES = { reboot: 'Rebooting the Raspberry Pi', restart: 'Restarting the web server' };
// Probing too early would still reach the old processes and reload before anything restarted.
const GRACE_MS = { reboot: 15000, restart: 8000 };
const POLL_MS = 2000;
const STUCK_MS = 120000;

const reconnecting = ref(false);
const stuck = ref(false);
let pollTimer = null;
let stuckTimer = null;

function reload() {
  window.location.reload();
}

async function probe() {
  try {
    await api('session');
    reload();
  } catch {
    pollTimer = setTimeout(probe, POLL_MS);
  }
}

onMounted(() => {
  pollTimer = setTimeout(() => {
    reconnecting.value = true;
    probe();
  }, GRACE_MS[props.action]);
  stuckTimer = setTimeout(() => (stuck.value = true), STUCK_MS);
});
onBeforeUnmount(() => {
  clearTimeout(pollTimer);
  clearTimeout(stuckTimer);
});
</script>

<template>
  <BlockingOverlay :title="TITLES[action]" :detail="reconnecting ? 'Reconnecting…' : 'Please wait…'">
    <button v-if="stuck" type="button" class="rounded-md border border-zinc-700 px-3 py-1.5 text-sm hover:bg-zinc-800" @click="reload">
      Reload
    </button>
  </BlockingOverlay>
</template>
