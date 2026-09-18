<script setup>
defineProps({
  modelValue: { type: Number, default: 0 },
  count: { type: Number, default: 0 },
  z: { type: Number, default: null },
});
const emit = defineEmits(['update:modelValue']);
</script>

<template>
  <label class="flex min-w-0 items-center gap-3 text-xs text-zinc-400">
    <input
      type="range"
      :min="count ? 1 : 0"
      :max="count"
      :value="modelValue"
      :disabled="!count"
      class="min-w-0 flex-1 accent-emerald-500 disabled:opacity-40"
      @input="emit('update:modelValue', Number($event.target.value))"
    >
    <span class="whitespace-nowrap tabular-nums">
      Layer {{ modelValue }} / {{ count }}<template v-if="z != null"> · {{ z.toFixed(2) }} mm</template>
    </span>
  </label>
</template>
