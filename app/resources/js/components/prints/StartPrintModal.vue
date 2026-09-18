<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useSpoolChoice } from '../../composables/useSpoolChoice';
import AppButton from '../AppButton.vue';
import FileThumbnail from '../FileThumbnail.vue';
import Icon from '../Icon.vue';
import Modal from '../Modal.vue';
import SpoolOption from '../filament/SpoolOption.vue';
import { inputClass } from '../settings/styles';

/* Asks which spool a print runs on before it starts. The spool in the printer is preselected;
   choosing another one loads it, "No spool" unloads, then the print is sent. Every spool shows
   why the file would not fit it, the print may still go ahead. From a handful of spools on a
   search over name, vendor and material narrows the cards. */
const { printStart, filament, file, selected, issues, issuesFor, summary, busy, start } = useSpoolChoice();
const router = useRouter();
const query = ref('');

const SEARCH_FROM = 4;
const searchable = computed(() => filament.active.length >= SEARCH_FROM);
const shown = computed(() => {
  const needle = query.value.trim().toLowerCase();
  if (!needle) return filament.active;
  return filament.active.filter((spool) => [spool.name, spool.vendor, spool.material].some((text) => text?.toLowerCase().includes(needle)));
});

function addSpool() {
  printStart.dismiss();
  router.push({ name: 'filament' });
}
</script>

<template>
  <Modal size="lg" @close="printStart.dismiss()">
    <template #title>
      <h2 class="font-medium">Start print</h2>
    </template>
    <div class="flex max-h-[85vh] flex-col">
      <div class="flex items-center gap-3 border-b border-zinc-800 bg-zinc-950/60 px-4 py-3">
        <FileThumbnail :file="file" />
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-zinc-100" :title="file.name">{{ file.name }}</div>
          <div class="truncate text-xs text-zinc-500 tabular-nums">{{ summary || '–' }}</div>
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto p-4">
        <label v-if="searchable" class="relative mb-3 block">
          <Icon name="search" class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-zinc-500" />
          <input v-model="query" type="search" placeholder="Search spools" aria-label="Search spools" class="w-full pl-9" :class="inputClass">
        </label>
        <div role="radiogroup" aria-label="Spool" class="grid gap-3 sm:grid-cols-2">
          <SpoolOption
            v-for="spool in shown"
            :key="spool.id"
            :spool="spool"
            :selected="selected === spool.id"
            :issues="issuesFor(spool)"
            @select="selected = spool.id"
          />
          <SpoolOption v-if="!query.trim()" :selected="selected === null" @select="selected = null" />
          <p v-if="query.trim() && !shown.length" class="text-sm text-zinc-500 sm:col-span-2">No spool matches.</p>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2 border-t border-zinc-800 px-4 py-3">
        <AppButton v-if="!filament.active.length" variant="ghost" icon="plus" @click="addSpool">Add spool</AppButton>
        <span class="flex-1" />
        <AppButton variant="ghost" @click="printStart.dismiss()">Cancel</AppButton>
        <AppButton variant="primary" icon="play" :disabled="busy" @click="start">{{ issues.length ? 'Print anyway' : 'Print' }}</AppButton>
      </div>
    </div>
  </Modal>
</template>
