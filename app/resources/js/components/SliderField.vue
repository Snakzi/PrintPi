<script setup>
import { computed } from 'vue';

/* A range input with its label and current value in one row above the track. `input` fires while
   dragging, `change` once the handle settles. */
const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },
  unit: { type: String, default: '%' },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'change']);

const fill = computed(() => `${((props.modelValue - props.min) / (props.max - props.min)) * 100}%`);
</script>

<template>
  <label class="flex flex-col gap-1.5">
    <span class="flex items-baseline justify-between text-xs">
      <span class="text-zinc-400">{{ label }}</span>
      <span class="font-mono tabular-nums text-zinc-200">{{ modelValue }}{{ unit }}</span>
    </span>
    <input
      :value="modelValue"
      type="range"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      class="slider w-full"
      :style="{ '--fill': fill }"
      @input="emit('update:modelValue', Number($event.target.value))"
      @change="emit('change', Number($event.target.value))"
    >
  </label>
</template>
