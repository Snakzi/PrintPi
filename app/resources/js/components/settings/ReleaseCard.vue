<script setup>
import ReleaseNotes from './ReleaseNotes.vue';

/* A published release with its notes; the buttons that install or download it come from the parent. */
defineProps({
  title: { type: String, required: true },
  meta: { type: String, default: null },
  notes: { type: String, default: null },
});
</script>

<template>
  <div class="flex flex-col items-start gap-3 rounded-md border border-zinc-800 bg-zinc-950/40 p-4">
    <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h3 class="font-semibold">{{ title }}</h3>
      <span v-if="meta" class="text-sm text-zinc-400">{{ meta }}</span>
    </div>
    <ReleaseNotes v-if="notes" :key="title" :notes="notes" />
    <div class="flex flex-wrap gap-2">
      <slot />
    </div>
  </div>
</template>
