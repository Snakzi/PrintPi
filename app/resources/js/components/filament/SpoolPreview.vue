<script setup>
import { computed } from 'vue';
import { remainingFraction, remainingTone, spoolDetail } from '../../filament/spools';
import { formatFilament, formatLength } from '../../format';
import Icon from '../Icon.vue';
import ProgressBar from '../ProgressBar.vue';
import SpoolSwatch from './SpoolSwatch.vue';

/* The spool as the list will show it, drawn from a form's draft while it is typed. With
   `editable` the swatch is the colour picker and `color` is edited through it. */
const props = defineProps({
  spool: { type: Object, required: true },
  color: { type: String, default: null },
  editable: { type: Boolean, default: false },
});
const emit = defineEmits(['update:color']);

const fraction = computed(() => remainingFraction(props.spool));
const tone = computed(() => remainingTone(fraction.value));
const TEXT = { emerald: 'text-emerald-300', amber: 'text-amber-300', red: 'text-red-400' };
</script>

<template>
  <div class="flex flex-col gap-3 border-b border-zinc-800 bg-zinc-950/60 px-4 py-4">
    <div class="flex items-center gap-4">
      <label v-if="editable" class="relative shrink-0 cursor-pointer rounded-full ring-emerald-500 hover:ring-2" title="Colour">
        <SpoolSwatch :color="color" :finish="spool.finish" size="xl" />
        <span class="absolute -right-0.5 -bottom-0.5 flex size-5 items-center justify-center rounded-full border border-zinc-700 bg-zinc-900 text-zinc-300">
          <Icon name="pencil" class="size-3" />
        </span>
        <input type="color" class="sr-only" :value="color ?? '#a1a1aa'" @input="emit('update:color', $event.target.value)">
      </label>
      <SpoolSwatch v-else :color="color" :finish="spool.finish" size="xl" />
      <div class="min-w-0 flex-1">
        <div class="truncate text-base font-semibold" :class="spool.name ? 'text-zinc-50' : 'text-zinc-600'">{{ spool.name || 'Unnamed spool' }}</div>
        <div class="truncate text-sm text-zinc-500">{{ spoolDetail(spool) || '–' }}</div>
      </div>
      <div class="shrink-0 text-right tabular-nums">
        <div class="text-xl leading-none font-semibold" :class="TEXT[tone]">{{ formatFilament(spool.remaining, null) }}</div>
        <div class="mt-1 text-xs text-zinc-500">{{ formatLength(spool.remaining_mm) }} · {{ Math.round(fraction * 100) }} %</div>
      </div>
    </div>
    <ProgressBar :value="fraction" :tone="tone" size="sm" full />
  </div>
</template>
