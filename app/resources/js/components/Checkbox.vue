<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <label class="inline-flex items-center gap-2 text-sm" :class="disabled ? 'opacity-40' : 'cursor-pointer'">
    <input
      type="checkbox"
      class="size-4 accent-emerald-500"
      :checked="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', $event.target.checked)"
    >
    <span class="text-zinc-300">{{ label }}</span>
  </label>
</template>
