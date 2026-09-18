<script setup>
import { computed } from 'vue';
import { remainingFraction, spoolDetail } from '../../filament/spools';
import Icon from '../Icon.vue';
import SpoolGraphic from './SpoolGraphic.vue';
import SpoolRemaining from './SpoolRemaining.vue';

/* One choice of the spool picker, a radio drawn as a card: the spool with what is left on it
   and, in `issues`, why the file does not fit it. Without a spool it stands for "no spool". */
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
    class="relative flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500"
    :class="[
      selected ? 'border-emerald-500 bg-emerald-500/10' : 'bg-zinc-950/40 hover:border-zinc-600',
      !selected && !spool ? 'border-dashed border-zinc-700' : '',
      !selected && spool ? 'border-zinc-800' : '',
    ]"
    @click="$emit('select')"
  >
    <SpoolGraphic :color="spool?.color ?? null" :finish="spool?.finish ?? null" :fraction="fraction" :size="52" :class="spool ? '' : 'opacity-40'" />
    <div class="min-w-0 flex-1 pr-4">
      <div class="truncate text-sm font-medium" :class="spool ? 'text-zinc-100' : 'text-zinc-400'">{{ spool?.name ?? 'No spool' }}</div>
      <div v-if="spool" class="truncate text-xs text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
      <SpoolRemaining v-if="spool" :spool="spool" class="mt-1.5" />
      <div v-for="issue in issues" :key="issue" class="mt-0.5 flex items-center gap-1 text-xs text-amber-300">
        <Icon name="warning" class="size-3.5" />
        <span class="truncate">{{ issue }}</span>
      </div>
    </div>
    <span
      v-if="selected"
      class="absolute top-2 right-2 flex size-5 items-center justify-center rounded-full bg-emerald-500 text-zinc-950"
    >
      <Icon name="check" class="size-3.5" />
    </span>
  </button>
</template>
