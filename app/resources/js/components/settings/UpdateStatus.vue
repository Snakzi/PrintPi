<script setup>
import { computed } from 'vue';
import { formatDateTime } from '../../format';
import Icon from '../Icon.vue';

/* The line under a version: whether it is current, and when that was last checked. */
const props = defineProps({
  state: { type: String, default: 'unknown' }, // current | available | error | unknown
  message: { type: String, default: null },
  checkedAt: { type: String, default: null },
});

const STATES = {
  current: { icon: 'check-circle', tone: 'text-emerald-400', text: 'text-zinc-200', label: 'Up to date' },
  available: { icon: 'arrow-down-circle', tone: 'text-amber-400', text: 'text-amber-300', label: 'Update available' },
  error: { icon: 'exclamation-circle', tone: 'text-amber-400', text: 'text-amber-300', label: 'Check failed' },
  unknown: { icon: null, tone: '', text: 'text-zinc-400', label: null },
};

const current = computed(() => STATES[props.state] ?? STATES.unknown);
const label = computed(() => props.message ?? current.value.label);
</script>

<template>
  <p class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm" role="status">
    <span v-if="label" class="flex items-center gap-1.5" :class="current.text">
      <Icon v-if="current.icon" :name="current.icon" class="size-4 shrink-0" :class="current.tone" />
      {{ label }}
    </span>
    <span v-if="checkedAt" class="text-zinc-500">Checked {{ formatDateTime(checkedAt) }}</span>
  </p>
</template>
