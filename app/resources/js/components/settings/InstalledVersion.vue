<script setup>
/* The version a card is about, with what it belongs to underneath; the placeholder stands in while none is known. */
defineProps({
  version: { type: String, default: null },
  detail: { type: String, default: null },
  placeholder: { type: String, default: '–' },
});
</script>

<template>
  <div class="flex flex-col gap-0.5">
    <div v-if="version" class="text-xl font-semibold tracking-tight wrap-anywhere">{{ version }}</div>
    <div v-else class="text-zinc-400">{{ placeholder }}</div>
    <div v-if="detail" class="text-sm wrap-anywhere text-zinc-500">{{ detail }}</div>
  </div>
</template>
