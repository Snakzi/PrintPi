<script setup>
import Icon from '../Icon.vue';

defineProps({
  tabs: { type: Array, required: true },
  current: { type: String, required: true },
});
</script>

<template>
  <nav class="flex shrink-0 gap-1 overflow-x-auto [scrollbar-width:none] md:w-48 md:flex-col md:overflow-visible" aria-label="Settings">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.id"
      :to="{ name: 'settings', params: { tab: tab.id } }"
      class="flex shrink-0 items-center gap-3 rounded-md px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
      :class="{ 'bg-zinc-800 text-zinc-100': tab.id === current }"
      :aria-current="tab.id === current ? 'page' : null"
    >
      <Icon :name="tab.icon" class="size-5 shrink-0" />
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>
