<script setup>
import { onMounted, ref } from 'vue';
import { useSessionStore } from '../../stores/session';
import { useToastStore } from '../../stores/toasts';
import AppButton from '../AppButton.vue';
import CopyField from '../CopyField.vue';
import SettingsCard from './SettingsCard.vue';
import { useConfirm } from '../../composables/useConfirm';
import SettingsField from './SettingsField.vue';

/* What a slicer's print host needs: this address, the host type and the user's API key. */
const session = useSessionStore();
const toasts = useToastStore();
const confirm = useConfirm();
const busy = ref(false);
const host = window.location.origin;

async function regenerate() {
  if (session.apiKey && !(await confirm('Generate a new API key?', { message: 'Slicers set up with the current one stop working.', danger: true }))) return;
  busy.value = true;
  try {
    await session.regenerateApiKey();
    toasts.success('API key generated');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  try {
    await session.loadApiKey();
  } catch (error) {
    toasts.error(error.message);
  }
});
</script>

<template>
  <SettingsCard title="Print host" :form="false">
    <div class="grid gap-4 sm:grid-cols-2">
      <SettingsField label="Host">
        <CopyField :value="host" mono />
      </SettingsField>
      <SettingsField label="Host type">
        <CopyField value="OctoPrint" />
      </SettingsField>
      <SettingsField label="API key" class="sm:col-span-2">
        <div class="flex gap-2">
          <CopyField :value="session.apiKey" placeholder="None yet" mono class="flex-1" />
          <AppButton :disabled="busy" @click="regenerate">{{ session.apiKey ? 'Regenerate' : 'Generate' }}</AppButton>
        </div>
      </SettingsField>
    </div>
  </SettingsCard>
</template>
