<script setup>
import { RouterLink } from 'vue-router';
import Icon from './Icon.vue';

/* A square ghost button with only an icon; title doubles as the accessible name. `to` renders a router link. */
defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  to: { type: [String, Object], default: null },
  active: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
});
</script>

<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to ?? undefined"
    :type="to ? undefined : 'button'"
    :disabled="to ? undefined : disabled"
    :title="title"
    :aria-label="title"
    :aria-pressed="active || undefined"
    class="inline-flex shrink-0 items-center justify-center rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-emerald-500 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
    :class="[
      size === 'sm' ? 'size-6' : 'size-7',
      active ? 'bg-zinc-800 text-emerald-400' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 disabled:hover:text-zinc-400',
    ]"
  >
    <Icon :name="icon" :class="size === 'sm' ? 'size-3.5' : 'size-4'" />
  </component>
</template>
