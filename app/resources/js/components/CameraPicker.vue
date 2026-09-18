<script setup>
import { computed, ref, watch } from 'vue';
import { cameraLabel } from '../format';
import Icon from './Icon.vue';

const props = defineProps({
  cameras: { type: Array, default: () => [] },
  status: { type: Object, default: () => ({ running: false, device: null, available: false, error: null }) },
  streamUrl: { type: String, default: '/webcam/stream' },
  modelValue: { type: Object, required: true }, // { device: string|null, url: string|null }
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'start', 'stop']);

// A url of '' means the stream mode with nothing typed yet; only null means no stream.
const modeOf = (value) => (typeof value.url === 'string' ? 'url' : value.device ? 'usb' : 'none');

const mode = ref(modeOf(props.modelValue));
const nonce = ref(Date.now());
const previewFailed = ref(false);

watch(
  () => props.modelValue,
  (value) => {
    mode.value = modeOf(value);
  },
  { deep: true },
);

function choose(next, device = null) {
  mode.value = next;
  previewFailed.value = false;
  if (next === 'none') emit('update:modelValue', { device: null, url: null });
  if (next === 'usb') emit('update:modelValue', { device: device ?? props.cameras[0]?.device ?? null, url: null });
  if (next === 'url') emit('update:modelValue', { device: null, url: props.modelValue.url ?? '' });
}

function setUrl(url) {
  emit('update:modelValue', { device: null, url });
}

const previewActive = computed(
  () => mode.value === 'usb' && props.status.running && props.status.device === props.modelValue.device,
);
const previewSrc = computed(() => {
  if (mode.value === 'url') return props.modelValue.url || null;
  if (previewActive.value) return `${props.streamUrl}${props.streamUrl.includes('?') ? '&' : '?'}_=${nonce.value}`;
  return null;
});

function preview() {
  previewFailed.value = false;
  nonce.value = Date.now();
  if (mode.value === 'usb' && props.modelValue.device) emit('start', props.modelValue.device);
}

const radio = 'flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm';
</script>

<template>
  <div class="flex flex-col gap-3">
    <label :class="[radio, mode === 'none' ? 'border-emerald-500' : 'border-zinc-700 hover:bg-zinc-800']">
      <input type="radio" name="camera" class="accent-emerald-500" :checked="mode === 'none'" @change="choose('none')">
      No camera
    </label>

    <label
      v-for="camera in cameras"
      :key="camera.device"
      :class="[radio, mode === 'usb' && modelValue.device === camera.device ? 'border-emerald-500' : 'border-zinc-700 hover:bg-zinc-800']"
    >
      <input
        type="radio"
        name="camera"
        class="accent-emerald-500"
        :checked="mode === 'usb' && modelValue.device === camera.device"
        @change="choose('usb', camera.device)"
      >
      <span class="flex flex-col">
        <span>{{ cameraLabel(camera) }}</span>
        <span class="text-xs text-zinc-500">USB camera</span>
      </span>
    </label>
    <p v-if="!cameras.length" class="text-xs text-zinc-500">No USB camera detected</p>

    <label :class="[radio, mode === 'url' ? 'border-emerald-500' : 'border-zinc-700 hover:bg-zinc-800']">
      <input type="radio" name="camera" class="accent-emerald-500" :checked="mode === 'url'" @change="choose('url')">
      <span class="flex flex-1 flex-col gap-1">
        <span>Stream URL</span>
        <input
          v-if="mode === 'url'"
          :value="modelValue.url"
          type="url"
          placeholder="http://192.168.1.50:8080/?action=stream"
          class="rounded-md border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm"
          @input="setUrl($event.target.value)"
          @click.stop
        >
      </span>
    </label>

    <div v-if="mode !== 'none'" class="flex flex-col gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="flex items-center gap-2 rounded-md border border-zinc-700 px-3 py-1.5 text-sm hover:bg-zinc-800 disabled:opacity-40"
          :disabled="busy || (mode === 'usb' && !status.available) || (mode === 'url' && !modelValue.url)"
          @click="preview"
        >
          <Icon name="camera" class="size-4" />
          {{ previewActive || mode === 'url' ? 'Reload preview' : 'Show preview' }}
        </button>
        <button
          v-if="previewActive"
          type="button"
          class="rounded-md border border-zinc-700 px-3 py-1.5 text-sm hover:bg-zinc-800"
          @click="emit('stop')"
        >
          Stop stream
        </button>
        <span v-if="mode === 'usb' && !status.available" class="text-xs text-amber-300">ustreamer is not installed on this system</span>
        <span v-else-if="mode === 'usb' && busy" class="text-xs text-zinc-400">Starting…</span>
        <span v-if="status.error && mode === 'usb'" class="text-xs text-red-400">{{ status.error }}</span>
      </div>

      <div v-if="previewSrc" class="overflow-hidden rounded-md border border-zinc-800 bg-black">
        <img
          v-if="!previewFailed"
          :src="previewSrc"
          alt="Camera preview"
          class="mx-auto block max-h-80"
          @error="previewFailed = true"
        >
        <p v-else class="p-6 text-center text-sm text-zinc-400">No image</p>
      </div>
    </div>
  </div>
</template>
