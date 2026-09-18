<script setup>
import { ref } from 'vue';
import { usePluginStore } from '../stores/plugins';
import { useToastStore } from '../stores/toasts';
import Icon from './Icon.vue';

const plugins = usePluginStore();
const toasts = useToastStore();

const url = ref('');
const busy = ref(false);

async function submit() {
  busy.value = true;
  try {
    const plugin = await plugins.install({ url: url.value.trim() });
    toasts.success(`${plugin.name} installed`);
    url.value = '';
  } catch (error) {
    toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <form class="rounded-lg border border-zinc-800 bg-zinc-900 p-6" @submit.prevent="submit">
    <h2 class="text-lg font-semibold">Install from Git</h2>
    <div class="mt-4 flex flex-col gap-3 sm:flex-row">
      <input
        v-model="url"
        type="url"
        required
        placeholder="https://github.com/user/printpi-plugin"
        autocapitalize="off"
        spellcheck="false"
        class="flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-base"
      >
      <button
        type="submit"
        class="flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-2 font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="busy || !url"
      >
        <Icon name="download" class="size-4" />
        {{ busy ? 'Installing …' : 'Install' }}
      </button>
    </div>
  </form>
</template>
