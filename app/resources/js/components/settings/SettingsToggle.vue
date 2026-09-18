<script setup>
import ToggleSwitch from '../ToggleSwitch.vue';

/* One switch per row: the label on the left, the toggle on the right. */
defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
defineEmits(['update:modelValue']);
</script>

<template>
  <div class="flex items-center justify-between gap-4 py-2 text-sm" :class="disabled ? 'opacity-50' : ''">
    <span class="text-zinc-300">{{ label }}</span>
    <ToggleSwitch :model-value="modelValue" :label="label" :disabled="disabled" @update:model-value="$emit('update:modelValue', $event)" />
  </div>
</template>
