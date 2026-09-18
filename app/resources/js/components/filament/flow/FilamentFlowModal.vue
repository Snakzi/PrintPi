<script setup>
import { computed } from 'vue';
import { useFilamentChangeStore } from '../../../stores/filamentChange';
import { ACTION_LABELS } from '../../../filament/walkthrough';
import FilamentFlow from './FilamentFlow.vue';
import Modal from '../../Modal.vue';
import SpoolSwatch from '../SpoolSwatch.vue';

/* The walkthrough in the web app: a modal that stays up while the daemon works and closes on
   the result. Closing it early does not stop anything; Cancel inside does. */
const change = useFilamentChangeStore();
const state = computed(() => change.current);
const subject = computed(() => state.value?.spool?.name || state.value?.material || null);

function close() {
  change.dismiss();
}
</script>

<template>
  <Modal size="lg" @close="close">
    <template #title>
      <div class="flex min-w-0 items-center gap-3">
        <SpoolSwatch v-if="state?.spool" :color="state.spool.color" size="md" />
        <h2 class="truncate text-base font-semibold">{{ ACTION_LABELS[state?.action] ?? 'Filament' }}<span v-if="subject" class="font-normal text-zinc-500"> · {{ subject }}</span></h2>
      </div>
    </template>
    <div class="p-4">
      <FilamentFlow @close="close" />
    </div>
  </Modal>
</template>
