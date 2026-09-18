<script setup>
import { reactive } from 'vue';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import { browserTimezone, timezones } from '../../format';
import SettingsCard from './SettingsCard.vue';
import SettingsField from './SettingsField.vue';
import { inputClass } from './styles';

const settings = useSettingsStore();
const toasts = useToastStore();
const zones = timezones();

const form = reactive({
  hostname: settings.values.hostname ?? '',
  timezone: settings.values.timezone ?? browserTimezone(),
});

async function save() {
  try {
    await settings.save({ hostname: form.hostname, timezone: form.timezone });
    toasts.success('Device saved');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <SettingsCard title="Device" :saving="settings.saving" :disabled="!form.hostname" @submit="save">
    <div class="grid gap-4 sm:grid-cols-2">
      <SettingsField label="Hostname">
        <input v-model="form.hostname" :class="inputClass" autocapitalize="off" spellcheck="false">
        <span class="text-xs text-zinc-500">http://{{ form.hostname || 'printpi' }}.local</span>
      </SettingsField>
      <SettingsField label="Time zone">
        <select v-model="form.timezone" :class="inputClass">
          <option v-for="zone in zones" :key="zone" :value="zone">{{ zone }}</option>
        </select>
      </SettingsField>
    </div>
  </SettingsCard>
</template>
