<script setup>
import { computed, watch } from 'vue';
import { usePluginStore } from '../stores/plugins';
import DeviceRow from './DeviceRow.vue';
import FoundDeviceRow from './FoundDeviceRow.vue';
import Icon from './Icon.vue';
import Spinner from './Spinner.vue';

/* A devices control: the plugin's status under the control key is { scanning, scanned_at,
   error, signed_in, found: [{ id, name, model, host, needs_auth }], devices: [{ id, name,
   plug_name, model, host, printer, online, on, power_w, energy_today_kwh, error }] }. The
   control's action scans the network; remove, turn_on, turn_off and set_printer take a device
   id (set_printer an empty one to clear the mark), add and rename take { id, name }. */
const props = defineProps({
  control: { type: Object, required: true },
  value: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change', 'act']);

const plugins = usePluginStore();

const report = computed(() => props.value ?? {});
const found = computed(() => report.value.found ?? []);
const devices = computed(() => report.value.devices ?? []);
const scanning = computed(() => Boolean(report.value.scanning));

// A scan takes a few seconds, so the page polls faster while one runs.
watch(scanning, (running) => plugins.startPolling(running ? 1000 : 3000));

const act = (action, id) => emit('act', { action, value: id });

const list = 'flex flex-col divide-y divide-zinc-800 rounded-md border border-zinc-800';
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        type="button"
        class="flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="disabled || scanning"
        @click="emit('change', null)"
      >
        <Icon name="refresh" class="size-4" />
        Scan network
      </button>
      <span v-if="scanning" class="flex items-center gap-2 text-sm text-zinc-300">
        <Spinner size="size-4" />
        Searching …
      </span>
      <p v-else-if="report.error" class="text-sm text-red-400">{{ report.error }}</p>
    </div>

    <div v-if="devices.length" :class="list">
      <DeviceRow
        v-for="device in devices"
        :key="device.id"
        :device="device"
        :disabled="disabled"
        removable
        @power="act($event ? 'turn_on' : 'turn_off', device.id)"
        @rename="act('rename', { id: device.id, name: $event })"
        @printer="act('set_printer', $event ? device.id : '')"
        @remove="act('remove', device.id)"
      />
    </div>
    <p v-else class="text-sm text-zinc-500">No plugs added.</p>

    <template v-if="found.length">
      <h3 class="text-sm font-semibold text-zinc-300">Found</h3>
      <div :class="list">
        <FoundDeviceRow
          v-for="device in found"
          :key="device.id"
          :device="device"
          :disabled="disabled"
          @add="act('add', { id: device.id, name: $event })"
        />
      </div>
    </template>
    <p v-else-if="!scanning && report.scanned_at" class="text-sm text-zinc-500">No other plugs on the network.</p>
  </div>
</template>
