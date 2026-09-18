<script setup>
import { computed } from 'vue';
import DeviceRow from './DeviceRow.vue';

/* The dashboard form of a devices control: one switch per added plug, nothing to add or remove. */
const props = defineProps({
  control: { type: Object, required: true },
  value: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change', 'act']);

const devices = computed(() => props.value?.devices ?? []);
</script>

<template>
  <DeviceRow
    v-for="device in devices"
    :key="device.id"
    :device="device"
    :disabled="disabled"
    compact
    @power="emit('act', { action: $event ? 'turn_on' : 'turn_off', value: device.id })"
  />
  <div v-if="!devices.length" class="flex items-center justify-between gap-4 text-sm">
    <span class="text-zinc-400">{{ control.label }}</span>
    <span class="text-zinc-500">None</span>
  </div>
</template>
