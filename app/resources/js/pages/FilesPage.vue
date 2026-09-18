<script setup>
import { onMounted } from 'vue';
import { useFileStore } from '../stores/files';
import { useToastStore } from '../stores/toasts';
import FileUpload from '../components/FileUpload.vue';
import FileList from '../components/FileList.vue';

const files = useFileStore();
const toasts = useToastStore();

onMounted(async () => {
  try {
    await files.load();
  } catch (error) {
    toasts.error(error.message);
  }
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <FileUpload />
    <FileList />
  </div>
</template>
