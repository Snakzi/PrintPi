<script setup>
/* options: [{ value, label, title? }]. block stretches the segments across the container. */
defineProps({
  options: { type: Array, required: true },
  modelValue: { type: [String, Number, Boolean], default: null },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <div class="rounded-md bg-zinc-950 p-0.5" :class="block ? 'flex' : 'inline-flex'" role="group">
    <button
      v-for="option in options"
      :key="String(option.value)"
      type="button"
      :aria-pressed="option.value === modelValue"
      :title="option.title"
      :disabled="disabled"
      class="h-6 rounded px-2 text-xs font-medium whitespace-nowrap tabular-nums transition-colors disabled:cursor-not-allowed disabled:opacity-40"
      :class="[
        block ? 'flex-1' : '',
        option.value === modelValue ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200',
      ]"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>
