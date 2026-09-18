<script setup>
import { computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import { inlineControls, panelControls } from '../pluginControls';
import Icon from '../components/Icon.vue';
import PluginHeader from '../components/PluginHeader.vue';
import PluginSettingsForm from '../components/PluginSettingsForm.vue';
import PluginPanel from '../components/PluginPanel.vue';

const route = useRoute();
const plugins = usePluginStore();
const toasts = useToastStore();

const plugin = computed(() => plugins.find(String(route.params.plugin)));
const running = computed(() => Boolean(plugin.value?.installed && plugin.value?.enabled));
const inline = computed(() => (running.value ? inlineControls(plugin.value) : []));
const panels = computed(() => (running.value ? panelControls(plugin.value) : []));

onMounted(async () => {
  try {
    await plugins.load();
  } catch (error) {
    toasts.error(error.message);
  }
  plugins.startPolling();
});
onUnmounted(() => plugins.stopPolling());

const card = 'rounded-lg border border-zinc-800 bg-zinc-900 p-6';
</script>

<template>
  <div class="mx-auto flex max-w-3xl flex-col gap-4">
    <RouterLink :to="{ name: 'plugins' }" class="flex w-fit items-center gap-1 text-sm text-zinc-400 hover:text-zinc-100">
      <Icon name="chevron" class="size-4 rotate-90" />
      Plugins
    </RouterLink>

    <template v-if="plugin">
      <PluginHeader :plugin="plugin" />

      <section v-for="control in panels" :key="control.key" :class="card">
        <h2 class="text-lg font-semibold">{{ control.label }}</h2>
        <div class="mt-4">
          <PluginPanel :plugin="plugin" :controls="[control]" embedded headless />
        </div>
      </section>

      <section v-if="plugin.installed && plugin.schema.length" :class="card">
        <h2 class="text-lg font-semibold">Settings</h2>
        <div class="mt-4">
          <PluginSettingsForm :key="plugin.id" :plugin="plugin" />
        </div>
      </section>

      <section v-if="inline.length" :class="card">
        <h2 class="text-lg font-semibold">Controls</h2>
        <div class="mt-4">
          <PluginPanel :plugin="plugin" :controls="inline" embedded headless />
        </div>
      </section>
    </template>

    <p v-else-if="plugins.loaded" class="text-sm text-zinc-500">There is no plugin named {{ route.params.plugin }}.</p>
  </div>
</template>
