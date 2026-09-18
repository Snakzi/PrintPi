<script setup>
import { ref } from 'vue';
import Icon from '../Icon.vue';

/* Fires only after the finger has stayed down for `duration` ms; a bar fills up meanwhile. */
const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  duration: { type: Number, default: 1500 },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['hold']);

const holding = ref(false);
let timer = null;

function start(event) {
  if (props.disabled) return;
  holding.value = true;
  event.currentTarget.setPointerCapture(event.pointerId);
  timer = setTimeout(() => {
    stop();
    emit('hold');
  }, props.duration);
}

function stop() {
  clearTimeout(timer);
  timer = null;
  holding.value = false;
}
</script>

<template>
  <button
    type="button"
    :disabled="disabled"
    :title="label"
    :aria-label="label"
    class="relative flex h-14 w-16 flex-col items-center justify-center gap-0.5 overflow-hidden rounded-xl bg-red-950/60 text-red-300 select-none disabled:opacity-30"
    style="touch-action: none"
    @pointerdown="start"
    @pointerup="stop"
    @pointercancel="stop"
    @contextmenu.prevent
  >
    <span
      class="absolute inset-x-0 bottom-0 bg-red-600/70"
      :class="holding ? 'transition-[height] ease-linear' : ''"
      :style="{ height: holding ? '100%' : '0%', transitionDuration: `${duration}ms` }"
    />
    <Icon :name="icon" class="relative size-6" />
    <span class="relative text-[10px] font-semibold tracking-wide uppercase">{{ label }}</span>
  </button>
</template>
