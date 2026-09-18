<script setup>
import { formatBytes, formatDateTime } from '../../format';
import AppButton from '../AppButton.vue';
import Spinner from '../Spinner.vue';

/* Firmware files on the printer's USB drive, read with M20; a Buddy board flashes one of them with M997. */
defineProps({
  files: { type: Array, required: true },
  listedAt: { type: Number, default: null },
  error: { type: String, default: null },
  listing: { type: Boolean, default: false },
  connected: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
defineEmits(['refresh', 'flash']);
</script>

<template>
  <div class="flex flex-col gap-3 rounded-md border border-zinc-800 p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="font-semibold">Firmware on the USB drive</h3>
      <AppButton variant="secondary" size="sm" :icon="listing ? null : 'refresh'" :disabled="listing || disabled || !connected" @click="$emit('refresh')">
        <Spinner v-if="listing" size="size-3.5" />
        {{ listedAt ? 'Refresh' : 'Read the drive' }}
      </AppButton>
    </div>
    <p v-if="error" class="text-sm text-red-400" role="alert">{{ error }}</p>
    <ul v-else-if="files.length" class="divide-y divide-zinc-800">
      <li v-for="file in files" :key="file.name" class="flex items-center justify-between gap-3 py-2">
        <div class="min-w-0">
          <div class="truncate font-mono text-sm text-zinc-200" :title="file.long_name ?? file.name">{{ file.long_name ?? file.name }}</div>
          <div v-if="file.size != null" class="text-xs text-zinc-500">{{ formatBytes(file.size) }}</div>
        </div>
        <AppButton variant="primary" size="sm" icon="bolt" :disabled="disabled || !connected" @click="$emit('flash', file.name)">Flash</AppButton>
      </li>
    </ul>
    <p v-else-if="listedAt" class="text-sm text-zinc-400">No .bbf file on the USB drive</p>
    <p v-if="listedAt" class="text-xs text-zinc-500">Read {{ formatDateTime(new Date(listedAt * 1000).toISOString()) }}</p>
  </div>
</template>
