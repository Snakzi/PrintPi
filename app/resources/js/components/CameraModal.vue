<script setup>
import { computed, ref } from 'vue';
import CameraStream from './camera/CameraStream.vue';
import IconButton from './IconButton.vue';
import Modal from './Modal.vue';

const props = defineProps({ src: { type: String, required: true } });
const emit = defineEmits(['close']);

const nonce = ref(Date.now());
const failed = ref(false);

// A fresh query string makes the browser reopen the MJPEG stream instead of reusing a stalled one.
const url = computed(() => `${props.src}${props.src.includes('?') ? '&' : '?'}_=${nonce.value}`);

function reload() {
  failed.value = false;
  nonce.value = Date.now();
}
</script>

<template>
  <Modal @close="emit('close')">
    <template #title>
      <div class="flex min-w-0 flex-1 items-center justify-between gap-4">
        <h2 class="font-medium">Camera</h2>
        <IconButton icon="refresh" title="Reload" @click="reload" />
      </div>
    </template>
    <div class="flex h-[80vh] items-center justify-center bg-black">
      <CameraStream v-if="!failed" :src="url" @error="failed = true" />
      <p v-else class="p-10 text-sm text-zinc-400">No image</p>
    </div>
  </Modal>
</template>
