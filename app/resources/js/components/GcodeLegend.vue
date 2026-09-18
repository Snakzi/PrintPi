<script setup>
defineProps({ features: { type: Array, default: () => [] } });
</script>

<template>
  <ul class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-300">
    <li v-for="feature in features" :key="feature.id" class="flex items-center gap-1.5">
      <span class="size-2.5 rounded-full" :style="{ backgroundColor: feature.color }" />
      {{ feature.label }}
    </li>
  </ul>
</template>
