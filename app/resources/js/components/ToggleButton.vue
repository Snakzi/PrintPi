<script setup>
defineProps({ modelValue: { type: Boolean, default: false } });
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <button
    type="button"
    :aria-pressed="modelValue"
    class="rounded-md border px-2.5 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
    :class="modelValue ? 'border-emerald-500 bg-emerald-950/40 text-emerald-300' : 'border-zinc-700 text-zinc-300 hover:bg-zinc-800'"
    @click="emit('update:modelValue', !modelValue)"
  >
    <slot />
  </button>
</template>
