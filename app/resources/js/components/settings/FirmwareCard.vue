<script setup>
import { computed, onMounted, watch } from 'vue';
import { useFirmwareStore } from '../../stores/firmware';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { useUpdatesStore } from '../../stores/updates';
import AppButton from '../AppButton.vue';
import Spinner from '../Spinner.vue';
import FirmwareDriveFiles from './FirmwareDriveFiles.vue';
import FirmwareMethod from './FirmwareMethod.vue';
import FirmwareRelease from './FirmwareRelease.vue';
import FirmwareUpload from './FirmwareUpload.vue';
import InstalledVersion from './InstalledVersion.vue';
import SettingsCard from './SettingsCard.vue';
import { useConfirm } from '../../composables/useConfirm';
import UpdateStatus from './UpdateStatus.vue';

const firmware = useFirmwareStore();
const printer = usePrinterStore();
const toasts = useToastStore();
const confirm = useConfirm();
const updates = useUpdatesStore();

const disabled = computed(() => firmware.busy || firmware.inProgress || updates.inProgress || printer.printing);
const hasRelease = computed(() => firmware.profile?.firmware === 'buddy' || firmware.profile?.firmware === 'prusa');
// The version alone when M115 named one, else the whole firmware name; the model goes underneath.
const version = computed(() => firmware.installed.version ?? firmware.installed.name);
const detail = computed(() => {
  const parts = [firmware.installed.version ? firmware.installed.name : null, firmware.profile?.model];
  return parts.filter(Boolean).join(' · ');
});
const state = computed(() => {
  if (!hasRelease.value) return 'unknown';
  if (firmware.error) return 'error';
  if (firmware.upToDate === true) return 'current';
  if (firmware.upToDate === false) return 'available';
  return 'unknown';
});
// The release stays hidden once the printer reports it; without a version to compare it is offered anyway.
const showRelease = computed(() => firmware.latest && firmware.upToDate !== true);

async function load(check = false) {
  try {
    await firmware.load({ check });
    if (firmware.inProgress) firmware.track();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function flash(options, message) {
  if (disabled.value || !(await confirm('Flash the firmware?', { message, danger: true }))) return;
  try {
    await firmware.flash(options);
  } catch (error) {
    toasts.error(error.message);
  }
}

function flashDriveFile(name) {
  flash({ name }, `Flash ${name} from the USB drive? The printer restarts and is unavailable for a few minutes.`);
}

function flashUpload(file) {
  flash({ file }, `Flash ${file.name} with avrdude? The printer restarts afterwards.`);
}

function flashRelease(release) {
  flash({ source: 'release' }, `Download and flash firmware ${release.version}? The printer restarts afterwards.`);
}

function restart() {
  flash({}, 'Restart the printer to flash firmware.bin from its SD card?');
}

onMounted(() => load());
// The installed version and the drive come from the printer, so a connect or disconnect re-reads them.
watch(() => printer.connected, () => load());
</script>

<template>
  <SettingsCard title="Printer firmware" :form="false">
    <template v-if="firmware.method && hasRelease" #actions>
      <AppButton variant="secondary" :icon="firmware.checking ? null : 'refresh'" :disabled="firmware.checking || disabled" @click="load(true)">
        <Spinner v-if="firmware.checking" size="size-4" />
        Check for updates
      </AppButton>
    </template>
    <p v-if="firmware.loaded && !firmware.profile" class="text-sm text-zinc-400">No printer profile selected</p>
    <p v-else-if="firmware.loaded && !firmware.method" class="text-sm text-zinc-400">{{ firmware.profile.model }} is updated through its own app</p>
    <div v-else-if="firmware.loaded" class="flex flex-col gap-4">
      <div class="flex flex-col gap-1.5">
        <InstalledVersion :version="version" :detail="detail" placeholder="Printer not connected" />
        <UpdateStatus v-if="hasRelease" :state="state" :message="firmware.error" :checked-at="firmware.checkedAt" />
      </div>
      <FirmwareRelease
        v-if="showRelease"
        :release="firmware.latest"
        :method="firmware.method"
        :disabled="disabled || !firmware.status?.avrdude_available"
        @flash="flashRelease"
      />
      <p v-if="firmware.failed" class="text-sm text-red-400" role="alert">{{ firmware.status.error ?? 'The last firmware update failed.' }}</p>

      <div class="flex flex-col gap-4 border-t border-zinc-800 pt-4">
        <FirmwareMethod :disabled="disabled" />
        <FirmwareDriveFiles
          v-if="firmware.method === 'buddy'"
          :files="firmware.driveFirmware"
          :listed-at="firmware.files.listed_at"
          :error="firmware.files.error"
          :listing="firmware.listing"
          :connected="firmware.connected"
          :disabled="disabled"
          @refresh="firmware.refreshFiles().catch((error) => toasts.error(error.message))"
          @flash="flashDriveFile"
        />
        <FirmwareUpload
          v-else-if="firmware.method === 'avrdude'"
          :disabled="disabled"
          :available="firmware.status?.avrdude_available ?? false"
          @flash="flashUpload"
        />
        <div v-else>
          <AppButton variant="primary" icon="power" :disabled="disabled || !firmware.connected" @click="restart">Restart printer</AppButton>
        </div>
      </div>
    </div>
  </SettingsCard>
</template>
