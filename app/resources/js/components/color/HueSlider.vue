<script setup>
import { computed, ref } from 'vue';
import { usePointerDrag } from '../../composables/usePointerDrag';

/* The hue bar of the picker: the rainbow from red around to red, the knob in the hue it sits on.
   A drag or the arrow keys move it; the hue is in degrees. */
const props = defineProps({
  hue: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change']);

const track = ref(null);
const drag = usePointerDrag(track, ({ x }) => emit('change', x * 360), { disabled: () => props.disabled });

const knob = computed(() => ({ left: `${(props.hue / 360) * 100}%`, backgroundColor: `hsl(${props.hue} 100% 50%)` }));

function onKeydown(event) {
  const step = event.shiftKey ? 10 : 1;
  const move = { ArrowLeft: -step, ArrowDown: -step, ArrowRight: step, ArrowUp: step }[event.key];
  if (move === undefined || props.disabled) return;
  event.preventDefault();
  emit('change', Math.min(360, Math.max(0, props.hue + move)));
}
</script>

<template>
  <div
    ref="track"
    class="relative h-3 w-full touch-none rounded-full select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900"
    :class="disabled ? 'opacity-40' : 'cursor-pointer'"
    style="background: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)"
    role="slider"
    aria-label="Hue"
    :aria-valuenow="Math.round(hue)"
    aria-valuemin="0"
    aria-valuemax="360"
    :aria-disabled="disabled"
    :tabindex="disabled ? -1 : 0"
    @pointerdown="drag.onPointerDown"
    @pointermove="drag.onPointerMove"
    @pointerup="drag.onPointerUp"
    @pointercancel="drag.onPointerUp"
    @keydown="onKeydown"
  >
    <span
      class="pointer-events-none absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md ring-1 ring-black/40"
      :style="knob"
    />
  </div>
</template>
