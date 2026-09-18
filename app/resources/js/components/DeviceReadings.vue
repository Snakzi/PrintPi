<script setup>
import { computed } from 'vue';

/* What a plug reports next to its name: power draw and today's energy when it has a meter,
   otherwise its connection state. */
const props = defineProps({ device: { type: Object, required: true } });

const text = computed(() => {
  const { online, error, power_w: power, energy_today_kwh: energy } = props.device;
  if (online === null || online === undefined) return 'Connecting …';
  if (!online) return error || 'Offline';
  const parts = [];
  if (power !== null && power !== undefined) parts.push(`${power < 10 ? power.toFixed(1) : Math.round(power)} W`);
  if (energy !== null && energy !== undefined) parts.push(`${energy.toFixed(2)} kWh today`);
  return parts.join(' · ');
});
const offline = computed(() => props.device.online === false);
</script>

<template>
  <span v-if="text" class="text-xs tabular-nums" :class="offline ? 'text-red-400' : 'text-zinc-500'">{{ text }}</span>
</template>
