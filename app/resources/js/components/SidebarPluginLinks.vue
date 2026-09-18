<script setup>
import { onMounted } from 'vue';
import { usePluginStore } from '../stores/plugins';
import Icon from './Icon.vue';

/* touch: the taller rows of the drawer on a phone. */
defineProps({ touch: { type: Boolean, default: false } });

const plugins = usePluginStore();

onMounted(() => {
  if (!plugins.loaded) plugins.load().catch(() => {});
});
</script>

<template>
  <div v-if="plugins.installed.length" class="flex flex-col gap-0.5">
    <RouterLink
      v-for="plugin in plugins.installed"
      :key="plugin.id"
      :to="{ name: 'plugin', params: { plugin: plugin.id } }"
      class="flex items-center gap-2 rounded-md pr-3 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
      :class="touch ? 'py-2.5 pl-12 text-base' : 'py-1.5 pl-9 text-sm'"
      active-class=""
      exact-active-class="bg-zinc-800 text-zinc-100"
    >
      <Icon :name="plugin.icon || 'puzzle'" fallback="puzzle" :class="touch ? 'size-5' : 'size-4'" />
      <span class="truncate">{{ plugin.name }}</span>
    </RouterLink>
  </div>
</template>
