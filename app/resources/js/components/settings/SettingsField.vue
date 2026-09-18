<script setup>
/* A labelled control; `inline` puts the label to the left for a single short row. */
defineProps({
  label: { type: String, required: true },
  inline: { type: Boolean, default: false },
});
</script>

<template>
  <label class="flex text-sm" :class="inline ? 'flex-wrap items-center gap-x-4 gap-y-1' : 'flex-col gap-1'">
    <span class="text-zinc-400" :class="{ 'w-20 shrink-0': inline }">{{ label }}</span>
    <slot />
  </label>
</template>
