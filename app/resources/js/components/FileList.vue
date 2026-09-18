<script setup>
import { ref } from 'vue';
import { useFileStore } from '../stores/files';
import { useToastStore } from '../stores/toasts';
import { useStartPrint } from '../composables/useStartPrint';
import { formatBytes, formatDateTime, formatDuration } from '../format';
import FileThumbnail from './FileThumbnail.vue';
import { useConfirm } from '../composables/useConfirm';
import GcodePreviewModal from './GcodePreviewModal.vue';
import Icon from './Icon.vue';

const files = useFileStore();
const toasts = useToastStore();
const confirm = useConfirm();
const { startPrint } = useStartPrint();
const previewed = ref(null);

async function remove(file) {
  if (!(await confirm(`Delete ${file.name}?`, { danger: true }))) return;
  try {
    await files.remove(file);
    toasts.info(`${file.name} deleted`);
  } catch (error) {
    toasts.error(error.message);
  }
}

function filament(metadata) {
  if (metadata?.filament_g) return `${metadata.filament_g.toFixed(1)} g`;
  if (metadata?.filament_mm) return `${(metadata.filament_mm / 1000).toFixed(2)} m`;
  return '–';
}
</script>

<template>
  <div class="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-900">
    <table class="w-full text-left text-sm">
      <thead class="text-xs uppercase tracking-wide text-zinc-500">
        <tr>
          <th class="w-16 px-2 py-3" />
          <th class="px-4 py-3 font-medium">File</th>
          <th class="px-4 py-3 font-medium">Size</th>
          <th class="hidden px-4 py-3 font-medium md:table-cell">Duration</th>
          <th class="hidden px-4 py-3 font-medium md:table-cell">Filament</th>
          <th class="hidden px-4 py-3 font-medium lg:table-cell">Slicer</th>
          <th class="hidden px-4 py-3 font-medium lg:table-cell">Uploaded</th>
          <th class="px-4 py-3" />
        </tr>
      </thead>
      <tbody>
        <tr v-if="files.loading && !files.items.length">
          <td colspan="8" class="px-4 py-6 text-center text-zinc-500">Loading …</td>
        </tr>
        <tr v-else-if="!files.items.length">
          <td colspan="8" class="px-4 py-6 text-center text-zinc-500">No files uploaded yet.</td>
        </tr>
        <tr v-for="file in files.items" :key="file.id" class="border-t border-zinc-800 hover:bg-zinc-800/50">
          <td class="px-2 py-2">
            <button type="button" class="block rounded ring-emerald-500 hover:ring-2" title="3D preview" @click="previewed = file">
              <FileThumbnail :file="file" />
            </button>
          </td>
          <td class="max-w-xs truncate px-4 py-2 font-medium" :title="file.name">{{ file.name }}</td>
          <td class="px-4 py-2 tabular-nums text-zinc-300">{{ formatBytes(file.size) }}</td>
          <td class="hidden px-4 py-2 tabular-nums text-zinc-300 md:table-cell">{{ formatDuration(file.metadata?.estimated_seconds) }}</td>
          <td class="hidden px-4 py-2 tabular-nums text-zinc-300 md:table-cell">{{ filament(file.metadata) }}</td>
          <td class="hidden px-4 py-2 text-zinc-400 lg:table-cell">{{ file.metadata?.slicer ?? '–' }}</td>
          <td class="hidden px-4 py-2 text-zinc-400 lg:table-cell">{{ formatDateTime(file.uploaded_at) }}</td>
          <td class="px-4 py-2">
            <div class="flex justify-end gap-1">
              <button
                type="button"
                class="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                title="3D preview"
                @click="previewed = file"
              >
                <Icon name="cube" />
              </button>
              <button
                type="button"
                class="rounded-md p-1.5 text-emerald-400 hover:bg-zinc-800"
                title="Print"
                @click="startPrint(file)"
              >
                <Icon name="play" />
              </button>
              <button
                type="button"
                class="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-red-400"
                title="Delete"
                @click="remove(file)"
              >
                <Icon name="trash" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <GcodePreviewModal v-if="previewed" :file="previewed" @close="previewed = null" />
  </div>
</template>
