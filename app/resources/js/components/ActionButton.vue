<script setup>
import { onBeforeUnmount, ref } from 'vue';
import AppButton from './AppButton.vue';

/* A button that runs `action` on click and shows the outcome on itself for a moment: green with
   a check and the `done` label when the promise resolved, red when it threw. The width is held
   during the feedback so a shorter label does not shift the row. */
const props = defineProps({
  action: { type: Function, required: true },
  done: { type: String, default: 'Sent' },
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: 'md' },
  icon: { type: String, default: null },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
});

const FEEDBACK_MS = 1500;
const button = ref(null);
const state = ref('idle'); // idle | busy | done | failed
const minWidth = ref(null);
let timer = null;

async function click() {
  if (state.value === 'busy') return;
  clearTimeout(timer);
  minWidth.value = button.value?.$el ? `${button.value.$el.offsetWidth}px` : null;
  state.value = 'busy';
  try {
    await props.action();
    state.value = 'done';
  } catch {
    state.value = 'failed';
  }
  timer = setTimeout(() => {
    state.value = 'idle';
    minWidth.value = null;
  }, FEEDBACK_MS);
}

onBeforeUnmount(() => clearTimeout(timer));
</script>

<template>
  <AppButton
    ref="button"
    :variant="state === 'done' ? 'success' : state === 'failed' ? 'danger' : variant"
    :size="size"
    :icon="state === 'done' ? 'check' : state === 'failed' ? 'x' : icon"
    :disabled="disabled || state === 'busy'"
    :block="block"
    :style="minWidth ? { minWidth } : null"
    @click="click"
  >
    <slot v-if="state === 'idle' || state === 'busy'" />
    <template v-else-if="state === 'done'">{{ done }}</template>
    <template v-else>Failed</template>
  </AppButton>
</template>
