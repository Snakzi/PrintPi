<script setup>
import { useSpoolChoice } from '../../composables/useSpoolChoice';
import { stripGcodeExtension } from '../../format';
import Icon from '../Icon.vue';
import PanelButton from './PanelButton.vue';
import PanelSpoolTile from './PanelSpoolTile.vue';

/* The spool question on the touch screen: the file on top, the spools as tiles to scroll
   through, Cancel and Print at the bottom. No search, there is no keyboard. */
const { printStart, filament, file, selected, issues, issuesFor, summary, busy, start } = useSpoolChoice();
</script>

<template>
  <div class="flex h-full flex-col gap-3">
    <div class="flex shrink-0 items-center gap-4">
      <div class="flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-zinc-900">
        <img v-if="file.thumbnail_url" :src="file.thumbnail_url" :alt="file.name" class="size-full object-contain">
        <Icon v-else name="cube" class="size-8 text-zinc-700" />
      </div>
      <div class="min-w-0 flex-1">
        <div class="truncate text-xl font-semibold" :title="file.name">{{ stripGcodeExtension(file.name) }}</div>
        <div class="truncate text-base text-zinc-500 tabular-nums">{{ summary || '–' }}</div>
      </div>
    </div>

    <div role="radiogroup" aria-label="Spool" class="grid min-h-0 flex-1 auto-rows-max grid-cols-2 gap-3 overflow-y-auto overscroll-contain pr-1" style="touch-action: pan-y">
      <PanelSpoolTile v-for="spool in filament.active" :key="spool.id" :spool="spool" :selected="selected === spool.id" :issues="issuesFor(spool)" @select="selected = spool.id" />
      <PanelSpoolTile :selected="selected === null" @select="selected = null" />
    </div>

    <div class="grid shrink-0 grid-cols-2 gap-3">
      <PanelButton icon="x" @click="printStart.dismiss()">Cancel</PanelButton>
      <PanelButton variant="primary" icon="play" :disabled="busy" @click="start">{{ issues.length ? 'Print anyway' : 'Print' }}</PanelButton>
    </div>
  </div>
</template>
