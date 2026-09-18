<script setup>
import Icon from '../Icon.vue';

/* A tile with one big figure: label on top, value, an optional line underneath. */
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
  unit: { type: String, default: null },
  sub: { type: String, default: null },
  icon: { type: String, default: null },
  tone: { type: String, default: 'default' },
});

const TONES = { default: 'text-zinc-50', warn: 'text-amber-300', danger: 'text-red-400', muted: 'text-zinc-500', accent: 'text-emerald-400' };
</script>

<template>
  <div class="flex min-w-0 flex-col justify-between rounded-2xl bg-zinc-900 p-3">
    <div class="flex items-center gap-1 text-[11px] font-medium tracking-wide text-zinc-500 uppercase">
      <Icon v-if="icon" :name="icon" class="size-4" />
      <span class="truncate">{{ label }}</span>
    </div>
    <div class="mt-2 truncate text-2xl leading-none font-semibold tabular-nums" :class="TONES[tone] ?? TONES.default">
      <slot>
        {{ value ?? '–' }}<span v-if="unit && value != null" class="ml-1 text-sm font-normal text-zinc-500">{{ unit }}</span>
      </slot>
    </div>
    <div v-if="sub || $slots.sub" class="mt-1.5 truncate text-sm text-zinc-500">
      <slot name="sub">{{ sub }}</slot>
    </div>
  </div>
</template>
