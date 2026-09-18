<script setup>
import { ref, watch } from 'vue';
import Icon from './Icon.vue';

const props = defineProps({ file: { type: Object, required: true } });

const failed = ref(false);
watch(() => props.file.thumbnail_url, () => (failed.value = false));
</script>

<template>
  <div class="flex h-10 w-14 shrink-0 items-center justify-center overflow-hidden rounded bg-zinc-950">
    <img
      v-if="file.thumbnail_url && !failed"
      :src="file.thumbnail_url"
      :alt="file.name"
      loading="lazy"
      class="size-full object-contain"
      @error="failed = true"
    >
    <Icon v-else name="cube" class="size-5 text-zinc-600" />
  </div>
</template>
