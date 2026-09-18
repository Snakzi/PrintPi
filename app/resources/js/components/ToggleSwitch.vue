<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-40"
    :class="modelValue ? 'bg-emerald-600' : 'bg-zinc-700'"
    @click="emit('update:modelValue', !modelValue)"
  >
    <span v-if="label" class="sr-only">{{ label }}</span>
    <span
      class="inline-block size-5 rounded-full bg-white shadow transition-transform"
      :class="modelValue ? 'translate-x-5.5' : 'translate-x-0.5'"
    />
  </button>
</template>
