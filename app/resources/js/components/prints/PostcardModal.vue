<script setup>
import { computed, onMounted, ref } from 'vue';
import { useSettingsStore } from '../../stores/settings';
import JobStateBadge from '../job/JobStateBadge.vue';
import Modal from '../Modal.vue';
import SegmentedControl from '../SegmentedControl.vue';
import PostcardActions from './PostcardActions.vue';
import PostcardCanvas from './PostcardCanvas.vue';
import TimelapsePlayer from './TimelapsePlayer.vue';

/* The card and the timelapse of a print share one frame; the switch in the title picks which one
   shows. Without `card` (postcards switched off) only the timelapse is left. */
const props = defineProps({
  print: { type: Object, required: true },
  card: { type: Boolean, default: true },
});
const emit = defineEmits(['close']);

const VIEWS = [
  { value: 'card', label: 'Postcard' },
  { value: 'timelapse', label: 'Timelapse' },
];

const settings = useSettingsStore();
const canvas = ref(null);
const view = ref(props.card ? 'card' : 'timelapse');

onMounted(() => {
  if (!settings.loaded) settings.load().catch(() => {});
});

const options = computed(() => ({
  energyPrice: settings.values.energy_price,
  currency: settings.values.currency ?? '€',
  printerName: props.print.printer,
}));
const hasTimelapse = computed(() => Boolean(props.print.video_url || props.print.timelapse_url));
</script>

<template>
  <Modal @close="emit('close')">
    <template #title>
      <div class="flex min-w-0 flex-1 items-center gap-3">
        <h2 class="truncate font-medium">{{ print.name }}</h2>
        <JobStateBadge :state="print.state" />
        <SegmentedControl v-if="card && hasTimelapse" v-model="view" :options="VIEWS" class="ml-auto" />
      </div>
    </template>
    <div class="flex max-h-[80vh] flex-col overflow-y-auto">
      <div class="p-4">
        <div class="aspect-[40/21] overflow-hidden rounded-xl" :class="view === 'timelapse' ? 'bg-black' : ''">
          <PostcardCanvas v-if="card" v-show="view === 'card'" :print="print" :options="options" @rendered="canvas = $event" />
          <TimelapsePlayer v-if="hasTimelapse && view === 'timelapse'" :print="print" />
        </div>
      </div>
      <div class="flex justify-end border-t border-zinc-800 px-4 py-3">
        <PostcardActions :print="print" :canvas="canvas" :card="card" />
      </div>
    </div>
  </Modal>
</template>
