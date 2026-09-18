<script setup>
import { computed } from 'vue';

/* A ring that fills clockwise from the top; value null spins a short arc instead. The slot sits in the middle. */
const props = defineProps({
  value: { type: Number, default: null },
  size: { type: Number, default: 200 },
  stroke: { type: Number, default: 14 },
  tone: { type: String, default: 'emerald' },
});

const TONES = { emerald: 'stroke-emerald-500', amber: 'stroke-amber-400', red: 'stroke-red-500', zinc: 'stroke-zinc-600', sky: 'stroke-sky-500' };

const radius = computed(() => (props.size - props.stroke) / 2);
const circumference = computed(() => 2 * Math.PI * radius.value);
const offset = computed(() => {
  const fraction = props.value === null ? 0.25 : Math.min(1, Math.max(0, props.value));
  return circumference.value * (1 - fraction);
});
</script>

<template>
  <div class="relative shrink-0" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :viewBox="`0 0 ${size} ${size}`" class="size-full -rotate-90" :class="{ 'animate-spin': value === null }" style="animation-duration: 1.6s">
      <circle :cx="size / 2" :cy="size / 2" :r="radius" fill="none" class="stroke-zinc-800" :stroke-width="stroke" />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :class="TONES[tone] ?? TONES.emerald"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        class="transition-[stroke-dashoffset] duration-700"
      />
    </svg>
    <div class="absolute inset-0 flex flex-col items-center justify-center">
      <slot />
    </div>
  </div>
</template>
