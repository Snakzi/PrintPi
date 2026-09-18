<script setup>
import { computed } from 'vue';
import { formatFilament, formatLength } from '../../format';
import { remainingFraction, remainingTone } from '../../filament/spools';
import ProgressBar from '../ProgressBar.vue';

/* What is left of a spool: grams and metres over a bar that turns amber and red as it empties. */
const props = defineProps({ spool: { type: Object, required: true } });

const fraction = computed(() => remainingFraction(props.spool));
const tone = computed(() => remainingTone(fraction.value));
</script>

<template>
  <div class="flex min-w-0 flex-col gap-1">
    <div class="flex items-baseline justify-between gap-3 text-sm whitespace-nowrap tabular-nums">
      <span class="font-medium text-zinc-100">{{ formatFilament(spool.remaining, null) }}</span>
      <span class="text-xs text-zinc-500">{{ formatLength(spool.remaining_mm) }}</span>
    </div>
    <ProgressBar :value="fraction" :tone="tone" size="sm" full />
  </div>
</template>
