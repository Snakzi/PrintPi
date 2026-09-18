<script setup>
import { computed, defineAsyncComponent, ref } from 'vue';
import { usePrinterBed } from '../composables/usePrinterBed';
import Modal from './Modal.vue';

// three.js only loads when a preview is opened.
const GcodeViewer = defineAsyncComponent(() => import('./GcodeViewer.vue'));

defineProps({ file: { type: Object, required: true } });
const emit = defineEmits(['close']);

const bed = usePrinterBed();
const info = ref(null);

const dimensions = computed(() => info.value?.size.map((value) => value.toFixed(1)).join(' × '));
</script>

<template>
  <Modal @close="emit('close')">
    <template #title>
      <div class="min-w-0">
        <h2 class="truncate font-medium">{{ file.name }}</h2>
        <p v-if="info" class="text-xs tabular-nums text-zinc-400">{{ dimensions }} mm · {{ info.layers }} layers</p>
      </div>
    </template>
    <GcodeViewer :file="file" :bed="bed" class="h-[75vh]" @loaded="info = $event" />
  </Modal>
</template>
