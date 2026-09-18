<script setup>
import { computed } from 'vue';
import { BAUD_RATES, portLabel } from '../format';

const props = defineProps({
  modelValue: { type: Object, required: true },
  ports: { type: Array, default: () => [] },
  profile: { type: Object, default: null },
  compact: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
});
const emit = defineEmits(['update:modelValue']);

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value });
}

const field = computed(() => props.compact
  ? 'h-9 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-zinc-100 focus:border-emerald-500 focus:outline-none disabled:opacity-40'
  : 'w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-base');
const label = computed(() => props.compact ? 'flex flex-col gap-1 text-xs' : 'flex flex-col gap-1 text-sm');
</script>

<template>
  <div :class="compact ? 'flex flex-col gap-3' : 'grid gap-4 sm:grid-cols-2'">
    <label :class="label">
      <span class="text-zinc-400">Port</span>
      <select :value="modelValue.serial_port" :class="field" :disabled="compact && !ports.length" @change="update('serial_port', $event.target.value)">
        <option v-if="!compact" value="">Select later</option>
        <option v-else-if="!ports.length" value="">None found</option>
        <option v-if="!compact && modelValue.serial_port && !ports.some((port) => port.device === modelValue.serial_port)" :value="modelValue.serial_port">{{ modelValue.serial_port }}</option>
        <option v-for="port in ports" :key="port.device" :value="port.device">{{ portLabel(port) }}</option>
      </select>
      <span v-if="errors.serial_port" class="text-xs text-red-400">{{ errors.serial_port[0] }}</span>
    </label>
    <label :class="label">
      <span class="text-zinc-400">Baud rate</span>
      <select :value="modelValue.baud_rate" :class="field" @change="update('baud_rate', Number($event.target.value))">
        <option v-for="rate in BAUD_RATES" :key="rate" :value="rate">{{ rate }}</option>
      </select>
      <span v-if="errors.baud_rate" class="text-xs text-red-400">{{ errors.baud_rate[0] }}</span>
      <span v-if="profile" class="text-xs text-zinc-500">Profile {{ profile.model }}: {{ profile.baud_rate }}</span>
    </label>
  </div>
</template>
