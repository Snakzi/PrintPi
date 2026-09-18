<script setup>
import { formatDate } from '../../format';
import { formatSize } from '../../updates/format.js';
import AppButton from '../AppButton.vue';
import ReleaseCard from './ReleaseCard.vue';

defineProps({
  release: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
});
defineEmits(['install']);
</script>

<template>
  <ReleaseCard :title="`PrintPi ${release.version}`" :meta="`${formatDate(release.date)} · ${formatSize(release.size)}`" :notes="release.notes">
    <AppButton variant="primary" icon="download" :disabled="disabled" @click="$emit('install', release.version)">
      Install {{ release.version }}
    </AppButton>
  </ReleaseCard>
</template>
