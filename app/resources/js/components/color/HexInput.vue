<script setup>
import { ref, watch } from 'vue';
import { normalizeHex } from '../../color/hsv';

/* The colour as `#rrggbb` next to a swatch of it; a typed value is taken once it is a colour and
   reverted otherwise. */
const props = defineProps({
  modelValue: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const draft = ref(props.modelValue);
watch(
  () => props.modelValue,
  (hex) => {
    draft.value = hex;
  },
);

function commit() {
  const hex = normalizeHex(draft.value);
  if (hex && hex !== props.modelValue) emit('update:modelValue', hex);
  else draft.value = props.modelValue;
}
</script>

<template>
  <label class="flex items-center gap-2">
    <span class="size-7 shrink-0 rounded-md border border-zinc-700" :style="{ backgroundColor: modelValue }" />
    <input
      v-model="draft"
      type="text"
      maxlength="7"
      spellcheck="false"
      autocomplete="off"
      aria-label="Hex colour"
      :disabled="disabled"
      class="w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 py-1 font-mono text-sm uppercase text-zinc-200 focus:border-emerald-500 focus:outline-none disabled:opacity-40"
      @change="commit"
      @keydown.enter.prevent="commit"
    >
  </label>
</template>
