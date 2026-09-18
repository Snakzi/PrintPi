<script setup>
import { computed, useId } from 'vue';
import GlitterPattern from './GlitterPattern.vue';

/* A spool seen from the front: the winding grows from the hub outward with `fraction` of the
   filament left, in the spool's colour and sparkling when its finish is glitter. A spool without
   a colour winds in grey. */
const props = defineProps({
  color: { type: String, default: null },
  finish: { type: String, default: null },
  fraction: { type: Number, default: 1 },
  size: { type: Number, default: 48 },
});

const HUB = 8;
const FULL = 20.5;
const LAST = 1.5;
// Whatever is left shows as at least a thin ring; only an empty spool bares its hub.
const radius = computed(() => {
  const fraction = Math.min(1, Math.max(0, props.fraction));
  return fraction > 0 ? HUB + LAST + (FULL - HUB - LAST) * fraction : HUB;
});
// Thin rings suggest the wound layers; only those inside the winding are drawn.
const layers = computed(() => [11, 14, 17].filter((r) => r < radius.value - 0.5));
const shine = useId();
const glitter = useId();
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 48 48" aria-hidden="true" class="shrink-0">
    <defs>
      <radialGradient :id="shine" cx="35%" cy="30%" r="70%">
        <stop offset="0" stop-color="#fff" stop-opacity="0.22" />
        <stop offset="1" stop-color="#fff" stop-opacity="0" />
      </radialGradient>
      <GlitterPattern v-if="finish === 'glitter'" :id="glitter" />
    </defs>
    <circle cx="24" cy="24" r="22" fill="#27272a" stroke="#3f3f46" />
    <circle cx="24" cy="24" :r="radius" :fill="color ?? '#52525b'" stroke="rgba(0,0,0,0.35)" stroke-width="0.75" style="transition: r 600ms ease" />
    <circle v-for="r in layers" :key="r" cx="24" cy="24" :r="r" fill="none" stroke="rgba(0,0,0,0.18)" stroke-width="0.75" />
    <circle v-if="finish === 'glitter'" cx="24" cy="24" :r="radius" :fill="`url(#${glitter})`" style="transition: r 600ms ease" />
    <circle cx="24" cy="24" r="22" :fill="`url(#${shine})`" />
    <circle cx="24" cy="24" :r="HUB" fill="#18181b" stroke="#3f3f46" />
    <circle cx="24" cy="24" r="3.5" fill="#09090b" />
  </svg>
</template>
