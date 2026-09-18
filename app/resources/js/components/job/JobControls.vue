<script setup>
import { computed, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import { useConfirm } from '../../composables/useConfirm';
import AppButton from '../AppButton.vue';

const props = defineProps({ job: { type: Object, required: true } });
const emit = defineEmits(['postcard']);

const printer = usePrinterStore();
const settings = useSettingsStore();
const toasts = useToastStore();
const confirm = useConfirm();
const pending = ref(false);

const active = computed(() => ['printing', 'paused', 'cancelling'].includes(props.job.state));

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

async function cancel() {
  if (!(await confirm(`Cancel ${props.job.name}?`, { danger: true }))) return;
  run('cancelJob', 'Cancelling the print');
}
</script>

<template>
  <div class="grid auto-cols-fr grid-flow-col gap-2">
    <template v-if="active">
      <AppButton v-if="job.state === 'printing'" size="sm" icon="pause" block :disabled="pending || job.activity === 'pausing'" @click="run('pauseJob')">Pause</AppButton>
      <AppButton v-else-if="job.state === 'paused'" size="sm" variant="primary" icon="play" block :disabled="pending" @click="run('resumeJob')">
        Resume
      </AppButton>
      <AppButton size="sm" variant="danger" icon="stop" block :disabled="pending || job.state === 'cancelling'" @click="cancel">
        {{ job.state === 'cancelling' ? 'Cancelling…' : 'Cancel' }}
      </AppButton>
    </template>
    <template v-else>
      <AppButton
        size="sm"
        variant="primary"
        icon="refresh"
        block
        :disabled="pending || !printer.connected"
        :title="printer.connected ? '' : 'Printer not connected'"
        @click="run('restartJob', `${job.name} started`)"
      >
        Print again
      </AppButton>
      <AppButton v-if="settings.values.postcard !== false" size="sm" icon="photo" block @click="emit('postcard')">Postcard</AppButton>
    </template>
  </div>
</template>
