<script setup>
/* A small labelled figure. tone colours the value: default | warn | danger | muted. The default slot
   replaces the value, the footer slot sits under it (a bar, a hint). */
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
  unit: { type: String, default: null },
  tone: { type: String, default: 'default' },
  mono: { type: Boolean, default: false },
});

const TONES = {
  default: 'text-zinc-100',
  warn: 'text-amber-300',
  danger: 'text-red-400',
  muted: 'text-zinc-400',
};
</script>

<template>
  <div class="flex min-w-0 flex-col gap-1 rounded-md bg-zinc-950/70 px-3 py-2">
    <span class="truncate text-[11px] font-medium tracking-wide text-zinc-500 uppercase">{{ label }}</span>
    <span class="truncate text-sm leading-tight font-semibold tabular-nums" :class="[TONES[tone] ?? TONES.default, mono ? 'font-mono' : '']">
      <slot>
        {{ value ?? '–' }}<span v-if="unit && value != null" class="ml-0.5 text-xs font-normal text-zinc-500">{{ unit }}</span>
      </slot>
    </span>
    <slot name="footer" />
  </div>
</template>
