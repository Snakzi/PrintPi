<script setup>
/* A row of pills to pick one value, sized for a finger. options: [{ value, label }]. */
defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number], default: null },
  unit: { type: String, default: null },
});
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <div class="inline-flex items-center gap-1 rounded-xl bg-zinc-900 p-1" role="group">
    <button
      v-for="option in options"
      :key="String(option.value)"
      type="button"
      :aria-pressed="option.value === modelValue"
      class="h-10 min-w-12 rounded-lg px-3 text-base font-medium tabular-nums transition-colors"
      :class="option.value === modelValue ? 'bg-zinc-700 text-zinc-50' : 'text-zinc-400'"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
    <span v-if="unit" class="px-2 text-sm text-zinc-500">{{ unit }}</span>
  </div>
</template>
