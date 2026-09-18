<script setup>
import { ref, watch } from 'vue';
import ToggleSwitch from './ToggleSwitch.vue';

const props = defineProps({
  control: { type: Object, required: true },
  value: { type: [String, Number, Boolean], default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['change']);

/* A slider or colour picker fires many events while dragging; the local copy keeps the
   handle where the user put it and one request goes out per settled value. */
const local = ref(props.value);
let pending = null;
watch(
  () => props.value,
  (next) => {
    if (pending === null) local.value = next;
  },
);

function settle(next) {
  local.value = next;
  clearTimeout(pending);
  pending = setTimeout(() => {
    pending = null;
    emit('change', next);
  }, 150);
}

const input = 'rounded-md border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm';
</script>

<template>
  <label class="flex items-center justify-between gap-4 text-sm">
    <span class="text-zinc-400">{{ control.label }}</span>

    <ToggleSwitch
      v-if="control.type === 'toggle'"
      :model-value="Boolean(value)"
      :disabled="disabled"
      :label="control.label"
      @update:model-value="emit('change', $event)"
    />

    <input
      v-else-if="control.type === 'color'"
      :value="local ?? '#ffffff'"
      type="color"
      :disabled="disabled"
      class="h-8 w-14 cursor-pointer rounded-md border border-zinc-700 bg-zinc-950 p-0.5 disabled:opacity-40"
      @input="settle($event.target.value)"
    >

    <span v-else-if="control.type === 'range'" class="flex flex-1 items-center justify-end gap-3">
      <input
        :value="local ?? control.min ?? 0"
        type="range"
        :min="control.min ?? 0"
        :max="control.max ?? 100"
        :step="control.step ?? 1"
        :disabled="disabled"
        class="w-full max-w-48 accent-emerald-500 disabled:opacity-40"
        @input="settle(Number($event.target.value))"
      >
      <span class="w-12 text-right tabular-nums text-zinc-300">{{ local ?? '–' }}{{ control.unit ?? '' }}</span>
    </span>

    <button
      v-else-if="control.type === 'button'"
      type="button"
      class="rounded-md border border-zinc-700 px-3 py-1 hover:bg-zinc-800 disabled:opacity-40"
      :disabled="disabled"
      @click="emit('change', null)"
    >
      {{ control.label }}
    </button>

    <select
      v-else-if="control.type === 'select'"
      :value="value"
      :disabled="disabled"
      :class="input"
      @change="emit('change', $event.target.value)"
    >
      <option v-for="option in control.options" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
    </select>

    <input
      v-else
      :value="value ?? ''"
      type="text"
      :disabled="disabled"
      :class="input"
      @change="emit('change', $event.target.value)"
    >
  </label>
</template>
