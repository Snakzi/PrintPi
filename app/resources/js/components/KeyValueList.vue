<script setup>
/* items: [{ label, value, mono?, title?, tone? }]; a null value prints as a dash. */
defineProps({ items: { type: Array, required: true } });

const TONES = {
  default: 'text-zinc-200',
  warn: 'text-amber-300',
  danger: 'text-red-400',
  muted: 'text-zinc-500',
};
</script>

<template>
  <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-xs">
    <template v-for="item in items" :key="item.label">
      <dt class="text-zinc-500">{{ item.label }}</dt>
      <dd class="truncate" :class="[TONES[item.tone] ?? TONES.default, item.mono ? 'font-mono' : '']" :title="item.title ?? (item.value == null ? '' : String(item.value))">
        {{ item.value ?? '–' }}
      </dd>
    </template>
  </dl>
</template>
