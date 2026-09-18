<script setup>
defineProps({ source: { type: String, required: true } });
</script>

<template>
  <span class="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-400">
    {{ source === 'builtin' ? 'Built in' : 'Git' }}
  </span>
</template>
