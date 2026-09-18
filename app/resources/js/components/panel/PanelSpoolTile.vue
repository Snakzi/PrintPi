<script setup>
import { computed } from 'vue';
import { remainingFraction, spoolDetail } from '../../filament/spools';
import Icon from '../Icon.vue';
import SpoolGraphic from '../filament/SpoolGraphic.vue';
import SpoolRemaining from '../filament/SpoolRemaining.vue';

/* A spool as a finger-sized radio tile for the panel's start screen; without a spool it stands for "no spool". */
const props = defineProps({
  spool: { type: Object, default: null },
  selected: { type: Boolean, default: false },
  issues: { type: Array, default: () => [] },
});
defineEmits(['select']);

const fraction = computed(() => (props.spool ? remainingFraction(props.spool) : 0));
</script>

<template>
  <button
    type="button"
    role="radio"
    :aria-checked="selected"
    class="relative flex min-h-24 w-full items-center gap-4 rounded-2xl border-2 p-4 text-left transition-colors"
    :class="[
      selected ? 'border-emerald-500 bg-emerald-500/10' : 'border-transparent bg-zinc-900 active:bg-zinc-800',
      !selected && !spool ? 'border-dashed border-zinc-700 bg-transparent' : '',
    ]"
    @click="$emit('select')"
  >
    <SpoolGraphic :color="spool?.color ?? null" :finish="spool?.finish ?? null" :fraction="fraction" :size="60" :class="spool ? '' : 'opacity-40'" />
    <div class="min-w-0 flex-1 pr-6">
      <div class="truncate text-lg font-medium" :class="spool ? 'text-zinc-100' : 'text-zinc-400'">{{ spool?.name ?? 'No spool' }}</div>
      <div v-if="spool" class="truncate text-sm text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
      <SpoolRemaining v-if="spool" :spool="spool" class="mt-2" />
      <div v-for="issue in issues" :key="issue" class="mt-1 flex items-center gap-1.5 text-sm text-amber-300">
        <Icon name="warning" class="size-4" />
        <span class="truncate">{{ issue }}</span>
      </div>
    </div>
    <span v-if="selected" class="absolute top-3 right-3 flex size-7 items-center justify-center rounded-full bg-emerald-500 text-zinc-950">
      <Icon name="check" class="size-5" />
    </span>
  </button>
</template>
