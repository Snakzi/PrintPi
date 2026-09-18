<script setup>
import Icon from '../Icon.vue';

/* The Pi firmware's verdict on power and temperature: a green check, or the issues in order. */
defineProps({ issues: { type: Array, required: true } });

const TONES = { danger: 'text-red-400', warn: 'text-amber-300', muted: 'text-zinc-500' };
</script>

<template>
  <span v-if="!issues.length" class="inline-flex items-center gap-1.5 text-emerald-400">
    <Icon name="check-circle" class="size-4" /> OK
  </span>
  <ul v-else class="flex flex-col gap-0.5">
    <li v-for="issue in issues" :key="issue.label" class="inline-flex items-center gap-1.5" :class="TONES[issue.tone]">
      <Icon :name="issue.tone === 'muted' ? 'info' : 'exclamation-circle'" class="size-4" /> {{ issue.label }}
    </li>
  </ul>
</template>
