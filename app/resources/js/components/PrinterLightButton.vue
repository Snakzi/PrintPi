<script setup>
import { computed, ref, watch } from 'vue';
import { usePanel } from '../composables/usePanel';
import { usePrinterStore } from '../stores/printer';
import { useToastStore } from '../stores/toasts';
import ColorPicker from './ColorPicker.vue';
import SwitchButton from './SwitchButton.vue';

/* The printer's light in the status bar, backed by whichever plugin reports one, such as the
   LED strip. The requested state and colour show until the plugin confirms them or clearly did
   not. A light that reports a colour gets the chevron with the picker underneath; while the
   knob is dragged one colour request is in flight at a time and the newest waits for it. */
const printer = usePrinterStore();
const toasts = useToastStore();
const { root, panel, hovering, visible, align, toggle: togglePanel, pin } = usePanel();

const requested = ref(null);
const requestedColor = ref(null);
let timer = null;
let colorTimer = null;
let inflight = false;
let queued = null;

watch(
  () => printer.light?.on,
  (on) => {
    if (requested.value !== null && on === requested.value) settle();
  },
);
watch(
  () => printer.light?.color,
  (color) => {
    if (requestedColor.value !== null && color === requestedColor.value) settleColor();
  },
);

function settle() {
  clearTimeout(timer);
  requested.value = null;
}

function settleColor() {
  clearTimeout(colorTimer);
  requestedColor.value = null;
}

const on = computed(() => requested.value ?? Boolean(printer.light?.on));
const hasColor = computed(() => typeof printer.light?.color === 'string');
const color = computed(() => requestedColor.value ?? printer.light?.color ?? null);
const title = computed(() => `Turn the ${printer.light?.name || 'light'} ${on.value ? 'off' : 'on'}`);

async function toggle() {
  const next = !on.value;
  requested.value = next;
  clearTimeout(timer);
  timer = setTimeout(settle, 5000);
  try {
    await printer.setLight(next);
  } catch (error) {
    settle();
    toasts.error(error.message);
  }
}

function pickColor(hex) {
  requestedColor.value = hex;
  clearTimeout(colorTimer);
  colorTimer = setTimeout(settleColor, 5000);
  push(hex);
}

async function push(hex) {
  if (inflight) {
    queued = hex;
    return;
  }
  inflight = true;
  try {
    await printer.setLightColor(hex);
  } catch (error) {
    queued = null;
    settleColor();
    toasts.error(error.message);
  } finally {
    inflight = false;
    if (queued !== null) {
      const next = queued;
      queued = null;
      push(next);
    }
  }
}
</script>

<template>
  <div ref="root" class="relative" @mouseenter="hovering = true" @mouseleave="hovering = false">
    <SwitchButton
      icon="bulb"
      label="Light"
      :on="on"
      :disabled="requested !== null"
      :title="title"
      :dot-color="color"
      :expandable="hasColor"
      :expanded="visible"
      panel-title="Light colour"
      @click="toggle"
      @toggle="togglePanel"
    />

    <div
      v-if="hasColor"
      v-show="visible"
      ref="panel"
      class="absolute top-full z-30 pt-1.5"
      :class="align === 'left' ? 'left-0' : 'right-0'"
      @pointerdown="pin"
    >
      <div class="w-72 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl">
        <ColorPicker :model-value="color" @update:model-value="pickColor" />
      </div>
    </div>
  </div>
</template>
