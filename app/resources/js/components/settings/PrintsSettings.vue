<script setup>
import { reactive } from 'vue';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import SettingsCard from './SettingsCard.vue';
import SettingsField from './SettingsField.vue';
import SettingsToggle from './SettingsToggle.vue';
import { inputClass } from './styles';

/* What happens around a print: the timelapse, the postcard, the cancel script and the history. */
const settings = useSettingsStore();
const toasts = useToastStore();

const DEFAULT_CANCEL_GCODE = 'M107\nM104 S0\nM140 S0\nG91\nG1 Z10 F600\nG90\nM84';

const form = reactive({
  timelapse: settings.values.timelapse !== false,
  timelapse_mp4: settings.values.timelapse_mp4 !== false,
  timelapse_gif: settings.values.timelapse_gif !== false,
  postcard: settings.values.postcard !== false,
  cancel_gcode: settings.values.cancel_gcode ?? '',
  history_keep: settings.values.history_keep ?? 0,
});

async function save(patch, message) {
  try {
    await settings.save(patch);
    toasts.success(message);
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="space-y-6">
    <SettingsCard
      title="Timelapse and postcard"
      :saving="settings.saving"
      @submit="save({ timelapse: form.timelapse, timelapse_mp4: form.timelapse_mp4, timelapse_gif: form.timelapse_gif, postcard: form.postcard }, 'Timelapse saved')"
    >
      <div class="divide-y divide-zinc-800">
        <SettingsToggle v-model="form.timelapse" label="Record a timelapse of every print" />
        <SettingsToggle v-model="form.timelapse_mp4" label="Make an MP4 video" :disabled="!form.timelapse" />
        <SettingsToggle v-model="form.timelapse_gif" label="Make a GIF" :disabled="!form.timelapse" />
        <SettingsToggle v-model="form.postcard" label="Offer a postcard after a print" />
      </div>
    </SettingsCard>

    <SettingsCard title="Cancelling a print" :saving="settings.saving" @submit="save({ cancel_gcode: form.cancel_gcode }, 'Cancel script saved')">
      <SettingsField label="G-code sent after a cancel">
        <textarea v-model="form.cancel_gcode" rows="7" spellcheck="false" :class="[inputClass, 'font-mono text-sm']" :placeholder="DEFAULT_CANCEL_GCODE" />
      </SettingsField>
    </SettingsCard>

    <SettingsCard title="History" :saving="settings.saving" @submit="save({ history_keep: Number(form.history_keep) || 0 }, 'History saved')">
      <SettingsField label="Prints to keep, 0 for all">
        <input v-model="form.history_keep" type="number" min="0" max="10000" step="1" inputmode="numeric" :class="[inputClass, 'w-32']">
      </SettingsField>
    </SettingsCard>
  </div>
</template>
