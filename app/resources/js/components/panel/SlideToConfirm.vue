<script setup>
import { computed, ref } from 'vue';
import Icon from '../Icon.vue';

/* A knob to drag across a track; it confirms only at the far end and snaps back otherwise, so a
   stray touch never triggers what a button would. */
const props = defineProps({
  label: { type: String, required: true },
  icon: { type: String, default: 'arrow-right' },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['confirm']);

const KNOB = 56;
const track = ref(null);
const x = ref(0);
const dragging = ref(false);
let startX = 0;
let max = 0;

const fade = computed(() => (max ? Math.max(0, 1 - (x.value / max) * 1.6) : 1));

function down(event) {
  if (props.disabled) return;
  max = track.value.clientWidth - KNOB - 8;
  startX = event.clientX - x.value;
  dragging.value = true;
  event.currentTarget.setPointerCapture(event.pointerId);
}

function move(event) {
  if (!dragging.value) return;
  x.value = Math.min(max, Math.max(0, event.clientX - startX));
}

function up() {
  if (!dragging.value) return;
  dragging.value = false;
  if (x.value >= max - 2) emit('confirm');
  x.value = 0;
}
</script>

<template>
  <div
    ref="track"
    class="relative h-16 w-full overflow-hidden rounded-2xl bg-red-950/60 ring-1 ring-red-900/60 select-none"
    :class="{ 'opacity-40': disabled }"
    style="touch-action: none"
  >
    <span class="absolute inset-0 flex items-center justify-center text-base font-semibold text-red-200" :style="{ opacity: fade }">{{ label }}</span>
    <div
      class="absolute top-1 left-1 flex size-14 items-center justify-center rounded-xl bg-red-600 text-white shadow-lg"
      :class="dragging ? '' : 'transition-transform duration-200'"
      :style="{ transform: `translateX(${x}px)` }"
      @pointerdown="down"
      @pointermove="move"
      @pointerup="up"
      @pointercancel="up"
    >
      <Icon :name="icon" class="size-7" />
    </div>
  </div>
</template>
