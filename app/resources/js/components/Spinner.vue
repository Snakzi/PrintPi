<script setup>
defineProps({
  size: { type: String, default: 'size-5' },
});
</script>

<template>
  <div class="animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" :class="size" role="status" aria-label="Loading" />
</template>
