<script setup>
/* One round swatch per preset colour in a single row, the picked one ringed. */
defineProps({
  colors: { type: Array, required: true },
  selected: { type: String, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['pick']);
</script>

<template>
  <div class="grid gap-1.5" :style="{ gridTemplateColumns: `repeat(${colors.length}, minmax(0, 1fr))` }">
    <button
      v-for="color in colors"
      :key="color"
      type="button"
      class="aspect-square w-full rounded-full border border-white/15 transition-transform hover:scale-110 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
      :class="selected === color ? 'ring-2 ring-white ring-offset-2 ring-offset-zinc-900' : ''"
      :style="{ backgroundColor: color }"
      :title="color"
      :aria-pressed="selected === color"
      :disabled="disabled"
      @click="emit('pick', color)"
    />
  </div>
</template>
