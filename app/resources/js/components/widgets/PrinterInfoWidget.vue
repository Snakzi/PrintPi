<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { usePrinterStore } from '../../stores/printer';
import { usePrinterProfileStore } from '../../stores/printerProfiles';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import Icon from '../Icon.vue';
import IconButton from '../IconButton.vue';
import KeyValueList from '../KeyValueList.vue';
import { useConfirm } from '../../composables/useConfirm';
import WidgetActions from '../dashboard/WidgetActions.vue';

const printer = usePrinterStore();
const profiles = usePrinterProfileStore();
const settings = useSettingsStore();
const toasts = useToastStore();
const confirm = useConfirm();

onMounted(() => {
  if (!settings.loaded) settings.load().catch(() => {});
  profiles.load().catch(() => {});
});

const profile = computed(() => profiles.find(settings.values.printer_profile));
const profileName = computed(() => (profile.value ? `${profile.value.manufacturer} ${profile.value.model}` : null));
const name = computed(() => settings.values.printer_name || profileName.value);

// The catalog picture, else the outline drawing for the printer type.
const image = ref(null);
watch(profile, (next) => (image.value = next?.image ?? null), { immediate: true });
function fallbackImage() {
  image.value = profile.value?.type ? `/images/printers/${profile.value.type}.svg` : null;
}

const rows = computed(() => [
  { label: 'Machine', value: printer.machineType },
  { label: 'Firmware', value: printer.firmwareName },
  { label: 'Port', value: printer.connected ? `${printer.printer.port} @ ${printer.printer.baudrate}` : null, mono: true },
  { label: 'Daemon', value: printer.daemonAlive ? 'Running' : 'Unreachable', tone: printer.daemonAlive ? 'default' : 'danger' },
]);

async function disconnect() {
  if (printer.printing && !(await confirm('Disconnect during the print?', { message: 'The running print would fail.', danger: true }))) return;
  try {
    await printer.disconnect();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function connect() {
  try {
    const ok = await printer.reconnect();
    if (!ok) toasts.error(printer.printer.last_error || 'Connection failed');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <WidgetActions>
      <IconButton v-if="printer.connected" icon="power" title="Disconnect" @click="disconnect" />
      <IconButton v-else icon="link" title="Connect" :disabled="!printer.daemonAlive || printer.connecting" @click="connect" />
    </WidgetActions>

    <div class="flex items-center gap-3">
      <div class="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-md bg-zinc-950/70 p-1.5">
        <img v-if="image" :src="image" alt="" class="size-full object-contain" @error="fallbackImage">
        <Icon v-else name="printer" class="size-7 text-zinc-600" />
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 text-sm font-medium text-zinc-100">
          <span class="inline-block size-2 shrink-0 rounded-full" :class="printer.statusDotClass" />
          <span class="truncate">{{ printer.statusLabel }}</span>
        </div>
        <div class="mt-0.5 truncate text-xs text-zinc-400" :title="name ?? ''">{{ name ?? '–' }}</div>
        <div v-if="profileName && profileName !== name" class="truncate text-xs text-zinc-500">{{ profileName }}</div>
      </div>
    </div>

    <KeyValueList :items="rows" />

    <p v-if="printer.printer.last_error" class="text-xs text-red-400">{{ printer.printer.last_error }}</p>
  </div>
</template>
