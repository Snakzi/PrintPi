<script setup>
import { computed, ref, watch } from 'vue';
import { hexToHsv, hsvToHex, normalizeHex } from '../color/hsv';
import { DEFAULT_PRESETS } from '../color/presets';
import ColorField from './color/ColorField.vue';
import ColorSwatches from './color/ColorSwatches.vue';
import HexInput from './color/HexInput.vue';
import HueSlider from './color/HueSlider.vue';

/* The app's own colour picker: a saturation/value plane, the hue bar, preset swatches and the hex
   value, no native dialog. It keeps HSV rather than deriving it from the hex, because white and black
   carry no hue and the plane would snap to red after every such pick; a new modelValue is taken only
   when it names another colour. Emits update:modelValue on every move. */
const props = defineProps({
  modelValue: { type: String, default: '#ffffff' },
  presets: { type: Array, default: () => DEFAULT_PRESETS },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const hsv = ref(hexToHsv(props.modelValue) ?? { h: 0, s: 0, v: 1 });
const hex = computed(() => hsvToHex(hsv.value));

watch(
  () => props.modelValue,
  (next) => {
    const normalized = normalizeHex(next);
    if (normalized && normalized !== hex.value) hsv.value = hexToHsv(normalized);
  },
);

function set(patch) {
  hsv.value = { ...hsv.value, ...patch };
  emit('update:modelValue', hex.value);
}

/* A grey keeps the hue the plane is showing. */
function setHex(color) {
  const next = hexToHsv(color);
  set(next.s === 0 ? { ...next, h: hsv.value.h } : next);
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <ColorField :hue="hsv.h" :saturation="hsv.s" :value="hsv.v" :disabled="disabled" @change="set" />
    <HueSlider :hue="hsv.h" :disabled="disabled" @change="(h) => set({ h })" />
    <ColorSwatches :colors="presets" :selected="hex" :disabled="disabled" @pick="setHex" />
    <HexInput :model-value="hex" :disabled="disabled" @update:model-value="setHex" />
  </div>
</template>
