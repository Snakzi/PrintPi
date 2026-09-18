<script setup>
import { onMounted, onUnmounted } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import PluginCard from '../components/PluginCard.vue';
import PluginInstallForm from '../components/PluginInstallForm.vue';

const plugins = usePluginStore();
const toasts = useToastStore();

onMounted(async () => {
  try {
    await plugins.load();
  } catch (error) {
    toasts.error(error.message);
  }
  plugins.startPolling();
});
onUnmounted(() => plugins.stopPolling());

const grid = 'grid gap-3 sm:grid-cols-2 xl:grid-cols-3';
</script>

<template>
  <div class="mx-auto flex max-w-5xl flex-col gap-6">
    <section v-if="plugins.installed.length" class="flex flex-col gap-3">
      <h2 class="text-lg font-semibold">Installed</h2>
      <div :class="grid">
        <PluginCard v-for="plugin in plugins.installed" :key="plugin.id" :plugin="plugin" />
      </div>
    </section>

    <section class="flex flex-col gap-3">
      <h2 class="text-lg font-semibold">Available</h2>
      <div v-if="plugins.available.length" :class="grid">
        <PluginCard v-for="plugin in plugins.available" :key="plugin.id" :plugin="plugin" />
      </div>
      <p v-else-if="plugins.loaded" class="text-sm text-zinc-500">Every built-in plugin is installed.</p>
    </section>

    <PluginInstallForm />
  </div>
</template>
