<script setup>
import StatTile from '../StatTile.vue';

/* The last reported position; position is the printer state's { X, Y, Z } in mm. */
defineProps({ position: { type: Object, default: () => ({}) } });

const AXES = ['X', 'Y', 'Z'];
const format = (value) => (value == null ? null : value.toFixed(2));
</script>

<template>
  <div class="grid grid-cols-3 gap-2">
    <StatTile v-for="axis in AXES" :key="axis" :label="axis" :value="format(position?.[axis])" unit="mm" mono />
  </div>
</template>
