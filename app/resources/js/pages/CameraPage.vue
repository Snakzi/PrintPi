<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useCameraStore } from '../stores/camera';
import { useToastStore } from '../stores/toasts';
import AppButton from '../components/AppButton.vue';
import CameraStream from '../components/camera/CameraStream.vue';
import WidgetEmpty from '../components/dashboard/WidgetEmpty.vue';

const camera = useCameraStore();
const toasts = useToastStore();

const nonce = ref(Date.now());
const failed = ref(false);
const busy = ref(false);

onMounted(async () => {
  try {
    await camera.load();
    if (camera.settings.camera_device && !camera.status.running && camera.status.available) await start();
  } catch (error) {
    toasts.error(error.message);
  }
});

const usbActive = computed(
  () => camera.settings.camera_device && camera.status.running && camera.status.device === camera.settings.camera_device,
);
const streamUrl = computed(() => (usbActive.value ? camera.streamUrl : camera.settings.camera_url) || null);

// A fresh query string makes the browser reopen the MJPEG stream instead of reusing a stalled one.
const src = computed(() => {
  const base = streamUrl.value;
  return base ? `${base}${base.includes('?') ? '&' : '?'}_=${nonce.value}` : null;
});

async function start() {
  busy.value = true;
  failed.value = false;
  try {
    await camera.start(camera.settings.camera_device);
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      await camera.load();
      if (camera.status.running || camera.status.error) break;
    }
    if (!camera.status.running) toasts.error(camera.status.error || 'The stream did not start');
    nonce.value = Date.now();
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

function reload() {
  failed.value = false;
  nonce.value = Date.now();
}
</script>

<template>
  <div v-if="src" class="flex flex-col gap-3">
    <div class="aspect-video max-h-[75vh] w-full overflow-hidden rounded-lg border border-zinc-800 bg-black">
      <CameraStream v-if="!failed" :src="src" @error="failed = true" />
      <WidgetEmpty v-else icon="camera" message="No image">
        <AppButton size="sm" icon="refresh" @click="reload">Reload</AppButton>
      </WidgetEmpty>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <AppButton icon="refresh" @click="reload">Reload</AppButton>
      <AppButton v-if="usbActive" icon="stop" @click="stop">Stop stream</AppButton>
      <a v-if="usbActive" :href="camera.snapshotUrl" target="_blank" rel="noopener">
        <AppButton icon="photo">Snapshot</AppButton>
      </a>
    </div>
  </div>

  <div v-else class="mx-auto mt-6 max-w-xl rounded-lg border border-zinc-800 bg-zinc-900">
    <WidgetEmpty v-if="camera.settings.camera_device" icon="camera" :message="`${camera.settings.camera_device} is not streaming`">
      <p v-if="camera.status.error" class="text-xs text-red-400">{{ camera.status.error }}</p>
      <p v-if="!camera.status.available" class="text-xs text-amber-300">ustreamer is not installed on this system</p>
      <AppButton size="sm" icon="play" :disabled="busy || !camera.status.available" @click="start">
        {{ busy ? 'Starting…' : 'Start stream' }}
      </AppButton>
    </WidgetEmpty>
    <WidgetEmpty v-else icon="camera" message="No camera configured">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'settings' }" custom>
        <AppButton size="sm" variant="ghost" icon="settings" @click="navigate">Settings</AppButton>
      </RouterLink>
    </WidgetEmpty>
  </div>
</template>
