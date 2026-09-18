<script setup>
import { computed } from 'vue';
import { useNow } from '../../composables/useNow';

/* Time and date, ticking. */
const now = useNow(1000);
const time = computed(() => new Date(now.value).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }));
const date = computed(() => new Date(now.value).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }));
</script>

<template>
  <div>
    <div class="flex items-baseline gap-3">
      <span class="text-4xl leading-none font-semibold tracking-tight tabular-nums">{{ time }}</span>
      <span class="text-base whitespace-nowrap text-zinc-400">{{ date }}</span>
    </div>
  </div>
</template>
