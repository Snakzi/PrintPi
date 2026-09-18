<script setup>
import { RAMP, cssColor } from '../bedmesh';

defineProps({ tolerance: { type: Number, required: true } });

const gradient = `linear-gradient(to right, ${RAMP.map((rgb) => cssColor(rgb)).join(', ')})`;
</script>

<template>
  <div class="flex items-center gap-2 text-xs tabular-nums text-zinc-300">
    <span>Flat</span>
    <span class="h-2 w-28 rounded-full" :style="{ background: gradient }" />
    <span>±{{ tolerance.toFixed(2) }} mm</span>
  </div>
</template>
