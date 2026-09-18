<script setup>
import { computed, onMounted } from 'vue';
import { useFileStore } from '../../stores/files';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { useStartPrint } from '../../composables/useStartPrint';
import Icon from '../Icon.vue';
import PanelFileTile from './PanelFileTile.vue';

/* The library as tiles, newest first; a tap opens the spool dialog and starts the print. */
const files = useFileStore();
const printer = usePrinterStore();
const toasts = useToastStore();
const { startPrint } = useStartPrint();

onMounted(async () => {
  try {
    await files.load();
  } catch (error) {
    toasts.error(error.message);
  }
});

const items = computed(() => [...files.items].sort((a, b) => (b.uploaded_at ?? '').localeCompare(a.uploaded_at ?? '')));
const canPrint = computed(() => printer.connected && !printer.printing);

function pick(file) {
  if (!canPrint.value) {
    toasts.info(printer.printing ? 'A print is running' : 'Printer not connected');
    return;
  }
  startPrint(file);
}
</script>

<template>
  <div class="flex h-full flex-col">
    <div v-if="!items.length" class="flex flex-1 flex-col items-center justify-center gap-3 text-zinc-500">
      <Icon name="folder" class="size-10" />
      <span class="text-xl">{{ files.loading ? 'Loading…' : 'No files' }}</span>
    </div>
    <div v-else class="grid flex-1 auto-rows-max grid-cols-3 gap-4 overflow-y-auto overscroll-contain pr-1" style="touch-action: pan-y">
      <PanelFileTile v-for="file in items" :key="file.id" :file="file" :class="{ 'opacity-50': !canPrint }" @click="pick(file)" />
    </div>
  </div>
</template>
