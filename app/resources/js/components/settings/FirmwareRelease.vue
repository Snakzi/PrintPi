<script setup>
import { computed } from 'vue';
import { formatDate } from '../../format';
import { plainNotes } from '../../firmware/format.js';
import { formatSize } from '../../updates/format.js';
import AppButton from '../AppButton.vue';
import Icon from '../Icon.vue';
import ReleaseCard from './ReleaseCard.vue';

/* The newest release Prusa published. avrdude fetches and flashes it from here; the other
   methods need the file on the printer's drive, so they get a download link. */
const props = defineProps({
  release: { type: Object, required: true },
  method: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
defineEmits(['flash']);

const meta = computed(() => [formatDate(props.release.date), formatSize(props.release.size), props.release.name].join(' · '));
const extension = computed(() => props.release.name?.match(/\.\w+$/)?.[0] ?? 'file');
</script>

<template>
  <ReleaseCard :title="`Firmware ${release.version}`" :meta="meta" :notes="plainNotes(release.notes)">
    <AppButton v-if="method === 'avrdude'" variant="primary" icon="bolt" :disabled="disabled" @click="$emit('flash', release)">
      Flash {{ release.version }}
    </AppButton>
    <a
      :href="release.url"
      class="inline-flex h-9 items-center gap-1.5 rounded-md border border-zinc-700 px-3.5 text-sm font-medium text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800"
      download
    >
      <Icon name="download" class="size-4" />
      Download {{ extension }}
    </a>
    <a
      v-if="release.page"
      :href="release.page"
      target="_blank"
      rel="noopener"
      class="inline-flex h-9 items-center gap-1.5 rounded-md px-3.5 text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
    >
      <Icon name="link" class="size-4" />
      Release page
    </a>
  </ReleaseCard>
</template>
