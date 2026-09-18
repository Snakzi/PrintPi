<script setup>
import ActionButton from '../ActionButton.vue';

/* presets: [{ label, hotend, bed }]. apply(preset) and cool() return the promise of the
   G-code send, so each button can show whether it went through. */
defineProps({
  presets: { type: Array, required: true },
  apply: { type: Function, required: true },
  cool: { type: Function, required: true },
  disabled: { type: Boolean, default: false },
});
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <ActionButton
      v-for="preset in presets"
      :key="preset.label"
      size="sm"
      :disabled="disabled"
      :title="`Hotend ${preset.hotend} °C, bed ${preset.bed} °C`"
      :action="() => apply(preset)"
    >
      {{ preset.label }}
      <span class="font-normal text-zinc-500 tabular-nums">{{ preset.hotend }} / {{ preset.bed }}</span>
    </ActionButton>
    <ActionButton size="sm" icon="power" class="ml-auto" :disabled="disabled" :action="cool">Cool down</ActionButton>
  </div>
</template>
