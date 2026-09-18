<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { useCameraStore } from '../../stores/camera';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import CameraPicker from '../CameraPicker.vue';
import SettingsCard from './SettingsCard.vue';

const camera = useCameraStore();
const settings = useSettingsStore();
const toasts = useToastStore();

const form = ref({ device: settings.values.camera_device, url: settings.values.camera_url });
const busy = ref(false);
let timer = null;

onMounted(() => {
  camera.load().catch(() => {});
  timer = setInterval(() => camera.load().catch(() => {}), 4000);
});
onUnmounted(() => clearInterval(timer));

async function start(device) {
  busy.value = true;
  try {
    await camera.start(device);
    // ustreamer needs a moment to open the device; poll until it reports running or an error.
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      await camera.load();
      if ((camera.status.running && camera.status.device === device) || camera.status.error) break;
    }
    if (!camera.status.running) toasts.error(camera.status.error || 'The stream did not start');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function stop() {
  try {
    await camera.stop();
    await camera.load();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function save() {
  try {
    await settings.save({ camera_device: form.value.device, camera_url: form.value.url || null });
    toasts.success('Camera saved');
  } catch (error) {
    toasts.error(error.message);
    return;
  }
  if (form.value.device) await start(form.value.device);
  else if (camera.status.running) await stop();
}
</script>

<template>
  <SettingsCard title="Camera" :saving="settings.saving" @submit="save">
    <CameraPicker
      v-model="form"
      :cameras="camera.cameras"
      :status="camera.status"
      :stream-url="camera.streamUrl"
      :busy="busy"
      @start="start"
      @stop="stop"
    />
  </SettingsCard>
</template>
