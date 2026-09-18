<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { useCameraStore } from '../../stores/camera';
import { useToastStore } from '../../stores/toasts';
import AppButton from '../AppButton.vue';
import CameraModal from '../CameraModal.vue';
import CameraStream from '../camera/CameraStream.vue';
import IconButton from '../IconButton.vue';
import WidgetActions from '../dashboard/WidgetActions.vue';
import WidgetEmpty from '../dashboard/WidgetEmpty.vue';

const camera = useCameraStore();
const toasts = useToastStore();
const nonce = ref(Date.now());
const failed = ref(false);
const busy = ref(false);
const enlarged = ref(false);

onMounted(async () => {
  try {
    if (!camera.loaded) await camera.load();
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
  if (!base) return null;
  return `${base}${base.includes('?') ? '&' : '?'}_=${nonce.value}`;
});

async function start() {
  busy.value = true;
  try {
    await camera.start(camera.settings.camera_device);
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      await camera.load();
      if (camera.status.running || camera.status.error) break;
    }
    failed.value = false;
    nonce.value = Date.now();
  } catch (error) {
    toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}

function reload() {
  failed.value = false;
  nonce.value = Date.now();
}
</script>

<template>
  <div class="flex h-full flex-col">
    <WidgetActions>
      <template v-if="src">
        <IconButton icon="refresh" title="Reload" @click="reload" />
        <IconButton icon="expand" title="Enlarge" :disabled="failed" @click="enlarged = true" />
      </template>
    </WidgetActions>

    <div v-if="src" class="relative min-h-40 flex-1 overflow-hidden rounded-md bg-black">
      <button v-if="!failed" type="button" class="block size-full cursor-zoom-in" title="Enlarge" @click="enlarged = true">
        <CameraStream :src="src" @error="failed = true" />
      </button>
      <WidgetEmpty v-else icon="camera" message="No image">
        <AppButton size="sm" icon="refresh" @click="reload">Reload</AppButton>
      </WidgetEmpty>
    </div>

    <WidgetEmpty v-else-if="camera.settings.camera_device" icon="camera" :message="`${camera.settings.camera_device} is not streaming`">
      <p v-if="camera.status.error" class="text-xs text-red-400">{{ camera.status.error }}</p>
      <AppButton size="sm" icon="play" :disabled="busy || !camera.status.available" @click="start">
        {{ busy ? 'Starting…' : 'Start stream' }}
      </AppButton>
    </WidgetEmpty>

    <WidgetEmpty v-else icon="camera" message="No camera configured">
      <RouterLink v-slot="{ navigate }" :to="{ name: 'settings' }" custom>
        <AppButton size="sm" variant="ghost" icon="settings" @click="navigate">Settings</AppButton>
      </RouterLink>
    </WidgetEmpty>

    <CameraModal v-if="enlarged" :src="streamUrl" @close="enlarged = false" />
  </div>
</template>
