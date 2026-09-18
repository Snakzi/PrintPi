<script setup>
import { computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useFileStore } from '../../stores/files';
import { usePrinterStore } from '../../stores/printer';
import { useToastStore } from '../../stores/toasts';
import { useStartPrint } from '../../composables/useStartPrint';
import { formatBytes, formatDuration } from '../../format';
import AppButton from '../AppButton.vue';
import FileThumbnail from '../FileThumbnail.vue';
import IconButton from '../IconButton.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';

const files = useFileStore();
const printer = usePrinterStore();
const toasts = useToastStore();
const { startPrint } = useStartPrint();

onMounted(async () => {
  if (files.items.length) return;
  try {
    await files.load();
  } catch (error) {
    toasts.error(error.message);
  }
});

const recent = computed(() => files.items.slice(0, 8));
const canPrint = computed(() => printer.connected && !printer.printing);
</script>

<template>
  <div class="flex h-full flex-col">
    <WidgetActions>
      <IconButton icon="arrow-up-right" title="All files" :to="{ name: 'files' }" />
    </WidgetActions>

    <WidgetEmpty v-if="files.loading && !files.items.length" icon="folder" message="Loading…" />
    <WidgetEmpty v-else-if="!files.items.length" icon="folder" message="No files">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'files' }" custom>
        <AppButton size="sm" variant="ghost" icon="upload" @click="navigate">Upload</AppButton>
      </RouterLink>
    </WidgetEmpty>

    <ul v-else class="flex flex-col divide-y divide-zinc-800/80">
      <li v-for="file in recent" :key="file.id" class="flex items-center gap-3 py-2 first:pt-0 last:pb-0">
        <FileThumbnail :file="file" />
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm text-zinc-100" :title="file.name">{{ file.name }}</div>
          <div class="text-xs text-zinc-500 tabular-nums">{{ formatBytes(file.size) }} · {{ formatDuration(file.metadata?.estimated_seconds) }}</div>
        </div>
        <IconButton
          icon="play"
          title="Print"
          :disabled="!canPrint"
          class="text-emerald-500 hover:text-emerald-300"
          @click="startPrint(file)"
        />
      </li>
    </ul>
  </div>
</template>
