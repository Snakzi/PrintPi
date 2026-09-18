<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import Icon from './Icon.vue';
import ToggleSwitch from './ToggleSwitch.vue';
import { useConfirm } from '../composables/useConfirm';
import PluginSourceBadge from './PluginSourceBadge.vue';
import PluginStatusBadge from './PluginStatusBadge.vue';

const props = defineProps({ plugin: { type: Object, required: true } });
const router = useRouter();
const plugins = usePluginStore();
const toasts = useToastStore();
const confirm = useConfirm();

const busy = ref(false);

const link = computed(() => props.plugin.homepage || props.plugin.url || null);
const linkLabel = computed(() => {
  try {
    return link.value ? new URL(link.value).host + new URL(link.value).pathname.replace(/\/$/, '') : null;
  } catch {
    return link.value;
  }
});

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
const upgrade = () => run(() => plugins.upgrade(props.plugin.id), `${props.plugin.name} updated`);
const toggle = (enabled) => run(() => plugins.setEnabled(props.plugin.id, enabled));

async function uninstall() {
  if (!(await confirm(`Uninstall ${props.plugin.name}?`, { danger: true }))) return;
  run(async () => {
    await plugins.uninstall(props.plugin.id);
    router.push({ name: 'plugins' });
  }, `${props.plugin.name} uninstalled`);
}

const action = 'flex items-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-sm hover:bg-zinc-800 disabled:opacity-40';
</script>

<template>
  <header class="rounded-lg border border-zinc-800 bg-zinc-900">
    <div class="flex items-start gap-4 p-6">
      <span class="flex size-12 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-emerald-400">
        <Icon :name="plugin.icon || 'puzzle'" fallback="puzzle" class="size-7" />
      </span>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h1 class="text-lg font-semibold">{{ plugin.name }}</h1>
          <span class="text-xs text-zinc-500">{{ plugin.version }}</span>
          <PluginSourceBadge :source="plugin.source" />
          <PluginStatusBadge v-if="plugin.installed" :plugin="plugin" />
        </div>
        <p v-if="plugin.description" class="mt-1 text-sm text-zinc-400">{{ plugin.description }}</p>
        <p v-if="plugin.author || link" class="mt-1 text-xs text-zinc-500">
          <span v-if="plugin.author">{{ plugin.author }}</span>
          <span v-if="plugin.author && link"> · </span>
          <a v-if="link" :href="link" target="_blank" rel="noopener" class="hover:text-zinc-300 hover:underline">{{ linkLabel }}</a>
        </p>
        <p v-if="plugin.daemon?.error" class="mt-2 text-sm text-red-400">{{ plugin.daemon.error }}</p>
        <p v-else-if="plugin.daemon?.status?.hint" class="mt-2 text-sm text-amber-300">{{ plugin.daemon.status.hint }}</p>
      </div>
      <ToggleSwitch
        v-if="plugin.installed"
        :model-value="plugin.enabled"
        :disabled="busy"
        label="Enabled"
        @update:model-value="toggle"
      />
      <button
        v-else
        type="button"
        class="flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="busy"
        @click="install"
      >
        <Icon name="download" class="size-4" />
        {{ busy ? 'Installing …' : 'Install' }}
      </button>
    </div>

    <div v-if="plugin.installed" class="flex flex-wrap gap-2 border-t border-zinc-800 px-6 py-3">
      <button v-if="plugin.source === 'git'" type="button" :class="action" :disabled="busy" @click="upgrade">
        <Icon name="refresh" class="size-4" />
        Update
      </button>
      <button type="button" :class="action" class="ml-auto hover:text-red-400" :disabled="busy" @click="uninstall">
        <Icon name="trash" class="size-4" />
        Uninstall
      </button>
    </div>
  </header>
</template>
