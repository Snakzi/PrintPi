<script setup>
import { computed, ref } from 'vue';
import { formatDuration, stripGcodeExtension } from '../../format';
import Icon from '../Icon.vue';

/* One file as a tappable tile: the slicer's thumbnail, the name, time and filament. */
const props = defineProps({ file: { type: Object, required: true } });

const failed = ref(false);
const detail = computed(() => {
  const m = props.file.metadata ?? {};
  const parts = [];
  if (m.estimated_seconds) parts.push(formatDuration(m.estimated_seconds));
  if (m.filament_g) parts.push(`${Math.round(m.filament_g)} g`);
  else if (m.filament_mm) parts.push(`${(m.filament_mm / 1000).toFixed(1)} m`);
  if (m.filament_type) parts.push(m.filament_type);
  return parts.join(' · ');
});
</script>

<template>
  <button type="button" class="flex min-w-0 flex-col overflow-hidden rounded-2xl bg-zinc-900 text-left transition-colors active:bg-zinc-800">
    <div class="flex h-28 w-full items-center justify-center bg-zinc-950">
      <img v-if="file.thumbnail_url && !failed" :src="file.thumbnail_url" :alt="file.name" loading="lazy" class="size-full object-contain" @error="failed = true">
      <Icon v-else name="cube" class="size-10 text-zinc-700" />
    </div>
    <div class="min-w-0 p-3">
      <div class="truncate text-base font-medium" :title="file.name">{{ stripGcodeExtension(file.name) }}</div>
      <div class="truncate text-sm text-zinc-500">{{ detail || '–' }}</div>
    </div>
  </button>
</template>
