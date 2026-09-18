<script setup>
import { ref } from 'vue';
import { useToastStore } from '../stores/toasts';
import AppButton from './AppButton.vue';

/* Share or save a rendered canvas as PNG named `name`; the Web Share API where the browser has
   it, else a download. The slot takes further buttons that belong to the same card. */
const props = defineProps({
  canvas: { type: Object, default: null },
  name: { type: String, required: true },
  saveLabel: { type: String, default: 'Save image' },
});

const toasts = useToastStore();
const busy = ref(false);
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';

function blob() {
  return new Promise((resolve, reject) => {
    props.canvas.toBlob((result) => (result ? resolve(result) : reject(new Error('Could not render the image'))), 'image/png');
  });
}

function saveBlob(data, fileName) {
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function share() {
  busy.value = true;
  try {
    const file = new File([await blob()], `${props.name}.png`, { type: 'image/png' });
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: props.name });
    } else {
      saveBlob(file, file.name);
    }
  } catch (error) {
    if (error.name !== 'AbortError') toasts.error(error.message);
  } finally {
    busy.value = false;
  }
}

async function download() {
  try {
    saveBlob(await blob(), `${props.name}.png`);
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <AppButton v-if="canShare" variant="primary" icon="share" :disabled="!canvas || busy" @click="share">Share</AppButton>
    <AppButton :variant="canShare ? 'secondary' : 'primary'" icon="download" :disabled="!canvas" @click="download">{{ saveLabel }}</AppButton>
    <slot />
  </div>
</template>
