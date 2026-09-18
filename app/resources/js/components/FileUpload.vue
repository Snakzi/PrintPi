<script setup>
import { ref } from 'vue';
import { useFileStore } from '../stores/files';
import { useToastStore } from '../stores/toasts';
import Icon from './Icon.vue';

const files = useFileStore();
const toasts = useToastStore();
const dragging = ref(false);
const input = ref(null);

async function handle(list) {
  for (const file of Array.from(list ?? [])) {
    try {
      await files.upload(file);
      toasts.success(`${file.name} hochgeladen`);
    } catch (error) {
      toasts.error(`${file.name}: ${error.message}`);
    }
  }
}

function onDrop(event) {
  dragging.value = false;
  handle(event.dataTransfer?.files);
}

function onPick(event) {
  handle(event.target.files);
  event.target.value = '';
}
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center text-sm transition-colors"
    :class="dragging ? 'border-emerald-500 bg-emerald-950/30' : 'border-zinc-700 bg-zinc-900'"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
  >
    <template v-if="files.uploading">
      <span class="text-zinc-300">Lade hoch … {{ Math.round(files.progress * 100) }} %</span>
      <div class="h-2 w-64 max-w-full overflow-hidden rounded-full bg-zinc-800">
        <div class="h-full bg-emerald-500 transition-all" :style="{ width: `${Math.round(files.progress * 100)}%` }" />
      </div>
    </template>
    <template v-else>
      <Icon name="upload" class="size-6 text-zinc-500" />
      <span class="text-zinc-300">Drop G-code here</span>
      <button class="rounded-md border border-zinc-700 px-3 py-1.5 hover:bg-zinc-800" @click="input.click()">
        or choose a file
      </button>
      <span class="text-xs text-zinc-500">.gcode, .gco, .g up to 500 MB</span>
      <input ref="input" type="file" accept=".gcode,.gco,.g" multiple class="hidden" @change="onPick">
    </template>
  </div>
</template>
