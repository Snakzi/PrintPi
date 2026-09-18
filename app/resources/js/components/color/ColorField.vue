<script setup>
import { computed, ref } from 'vue';
import { usePointerDrag } from '../../composables/usePointerDrag';

/* The saturation/value plane of the picker for one hue: white to the hue from left to right,
   black rising from the bottom. A drag or the arrow keys move the knob; s and v are 0–1. */
const props = defineProps({
  hue: { type: Number, required: true },
  saturation: { type: Number, required: true },
  value: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change']);

const plane = ref(null);
const drag = usePointerDrag(plane, ({ x, y }) => emit('change', { s: x, v: 1 - y }), { disabled: () => props.disabled });

const background = computed(
  () => `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, hsl(${props.hue} 100% 50%))`,
);
const knob = computed(() => ({ left: `${props.saturation * 100}%`, top: `${(1 - props.value) * 100}%` }));

const clamp = (value) => Math.min(1, Math.max(0, value));

function onKeydown(event) {
  const step = event.shiftKey ? 0.1 : 0.01;
  const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] };
  const move = moves[event.key];
  if (!move || props.disabled) return;
  event.preventDefault();
  emit('change', { s: clamp(props.saturation + move[0]), v: clamp(props.value + move[1]) });
}
</script>

<template>
  <div
    ref="plane"
    class="relative h-36 w-full touch-none rounded-md border border-zinc-700 select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
    :class="disabled ? 'opacity-40' : 'cursor-crosshair'"
    :style="{ background }"
    :tabindex="disabled ? -1 : 0"
    aria-label="Saturation and brightness"
    @pointerdown="drag.onPointerDown"
    @pointermove="drag.onPointerMove"
    @pointerup="drag.onPointerUp"
    @pointercancel="drag.onPointerUp"
    @keydown="onKeydown"
  >
    <span
      class="pointer-events-none absolute size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md ring-1 ring-black/40"
      :style="knob"
    />
  </div>
</template>
