<script setup>
import { computed, onMounted, ref } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import { useUpdatesStore } from '../../stores/updates';
import AppButton from '../AppButton.vue';
import Spinner from '../Spinner.vue';
import AvailableRelease from './AvailableRelease.vue';
import InstalledVersion from './InstalledVersion.vue';
import SettingsCard from './SettingsCard.vue';
import SettingsField from './SettingsField.vue';
import UpdateStatus from './UpdateStatus.vue';
import { channelLabel } from '../../updates/format.js';
import { useConfirm } from '../../composables/useConfirm';
import { inputClass } from './styles';

const printer = usePrinterStore();
const settings = useSettingsStore();
const toasts = useToastStore();
const confirm = useConfirm();
const updates = useUpdatesStore();
const changingChannel = ref(false);
const channel = computed(() => updates.channel);
const busy = computed(() => updates.checking || updates.busy || updates.inProgress || changingChannel.value);
const disabled = computed(() => !updates.systemControl || busy.value || printer.printing);
const state = computed(() => {
  if (updates.error) return 'error';
  if (!updates.loaded) return 'unknown';
  return updates.available ? 'available' : 'current';
});

async function load(check = false) {
  try {
    await updates.load({ check });
    if (updates.inProgress) updates.track();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function changeChannel(event) {
  changingChannel.value = true;
  try {
    await settings.save({ update_channel: event.target.value });
    await load(true);
  } catch (error) {
    toasts.error(error.message);
  } finally {
    event.target.value = channel.value;
    changingChannel.value = false;
  }
}

async function install(version) {
  if (disabled.value || !(await confirm(`Install PrintPi ${version}?`, { message: 'The web app restarts afterwards.' }))) return;
  try {
    await updates.install(version);
  } catch (error) {
    toasts.error(error.message);
  }
}

onMounted(() => load());
</script>

<template>
  <SettingsCard title="PrintPi" :form="false">
    <template #actions>
      <AppButton variant="secondary" :icon="updates.checking ? null : 'refresh'" :disabled="busy" @click="load(true)">
        <Spinner v-if="updates.checking" size="size-4" />
        Check for updates
      </AppButton>
    </template>
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-1.5">
        <InstalledVersion :version="updates.installed" />
        <UpdateStatus :state="state" :message="updates.error" :checked-at="updates.checkedAt" />
      </div>
      <AvailableRelease v-if="updates.available" :release="updates.available" :disabled="disabled" @install="install" />
      <p v-if="updates.failed" class="text-sm text-red-400" role="alert">{{ updates.status.error ?? 'The last update failed.' }}</p>
      <SettingsField v-if="updates.channels.length > 1" label="Channel" inline class="border-t border-zinc-800 pt-4">
        <select
          :value="channel"
          :class="inputClass"
          :disabled="!settings.loaded || settings.saving || busy"
          @change="changeChannel"
        >
          <option v-for="option in updates.channels" :key="option" :value="option">{{ channelLabel(option) }}</option>
        </select>
      </SettingsField>
    </div>
  </SettingsCard>
</template>
