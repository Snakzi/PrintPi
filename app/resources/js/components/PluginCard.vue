<script setup>
import { ref } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import Icon from './Icon.vue';
import ToggleSwitch from './ToggleSwitch.vue';
import PluginSourceBadge from './PluginSourceBadge.vue';
import PluginStatusBadge from './PluginStatusBadge.vue';

const props = defineProps({ plugin: { type: Object, required: true } });
const plugins = usePluginStore();
const toasts = useToastStore();

const busy = ref(false);

async function run(task, message = null) {
  busy.value = true;
  try {
    await task();
    if (message) toasts.success(message);
  } catch (error) {
    toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}

const install = () => run(() => plugins.install({ id: props.plugin.id }), `${props.plugin.name} installed`);
const toggle = (enabled) => run(() => plugins.setEnabled(props.plugin.id, enabled));
</script>

<template>
  <article class="flex flex-col rounded-lg border border-zinc-800 bg-zinc-900 p-4">
    <div class="flex items-start gap-3">
      <span class="flex size-9 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-emerald-400">
        <Icon :name="plugin.icon || 'puzzle'" fallback="puzzle" class="size-5" />
      </span>
      <div class="min-w-0 flex-1">
        <RouterLink
          v-if="plugin.installed"
          :to="{ name: 'plugin', params: { plugin: plugin.id } }"
          class="block truncate font-semibold hover:text-emerald-400"
        >
          {{ plugin.name }}
        </RouterLink>
        <span v-else class="block truncate font-semibold">{{ plugin.name }}</span>
        <div class="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-zinc-500">
          <span>{{ plugin.version }}</span>
          <PluginSourceBadge :source="plugin.source" />
          <PluginStatusBadge v-if="plugin.installed" :plugin="plugin" />
        </div>
      </div>
      <ToggleSwitch
        v-if="plugin.installed"
        :model-value="plugin.enabled"
        :disabled="busy"
        label="Enabled"
        @update:model-value="toggle"
      />
    </div>

    <p v-if="plugin.description" class="mt-3 line-clamp-2 text-sm text-zinc-400">{{ plugin.description }}</p>

    <div class="mt-auto pt-4">
      <button
        v-if="!plugin.installed"
        type="button"
        class="flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="busy"
        @click="install"
      >
        <Icon name="download" class="size-4" />
        {{ busy ? 'Installing …' : 'Install' }}
      </button>
      <RouterLink
        v-else
        :to="{ name: 'plugin', params: { plugin: plugin.id } }"
        class="flex w-fit items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-100"
      >
        <Icon name="settings" class="size-4" />
        Settings
      </RouterLink>
    </div>
  </article>
</template>
