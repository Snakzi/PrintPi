<script setup>
import { reactive } from 'vue';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import SettingsCard from './SettingsCard.vue';
import SettingsToggle from './SettingsToggle.vue';

/* What the browser tells about: the end of a print, plugin messages and the job in the tab. */
const settings = useSettingsStore();
const toasts = useToastStore();

const form = reactive({
  notify_print_end: settings.values.notify_print_end !== false,
  notify_plugins: settings.values.notify_plugins !== false,
  tab_progress: settings.values.tab_progress !== false,
});

async function save() {
  try {
    await settings.save({ ...form });
    toasts.success('Notifications saved');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <SettingsCard title="Notifications" :saving="settings.saving" @submit="save">
    <div class="divide-y divide-zinc-800">
      <SettingsToggle v-model="form.notify_print_end" label="Message when a print ends" />
      <SettingsToggle v-model="form.notify_plugins" label="Messages from plugins" />
      <SettingsToggle v-model="form.tab_progress" label="Progress in the browser tab" />
    </div>
  </SettingsCard>
</template>
