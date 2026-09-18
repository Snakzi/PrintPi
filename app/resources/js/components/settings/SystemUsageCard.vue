<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { DAY, HOUR } from '../../charts/timeWindow';
import { useSystemStore } from '../../stores/system';
import { useToastStore } from '../../stores/toasts';
import SegmentedControl from '../SegmentedControl.vue';
import Spinner from '../Spinner.vue';
import UsageChart from '../system/UsageChart.vue';
import SettingsCard from './SettingsCard.vue';

const RANGES = [
  { value: DAY, label: '24 h' },
  { value: 6 * HOUR, label: '6 h' },
  { value: HOUR, label: '1 h' },
];

const system = useSystemStore();
const toasts = useToastStore();
const span = ref(DAY);

let timer = null;
onMounted(async () => {
  try {
    await system.loadHistory();
  } catch (error) {
    toasts.error(error.message);
  }
  timer = setInterval(() => system.loadHistory().catch(() => {}), system.historyInterval);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <SettingsCard title="Usage" :form="false">
    <template #actions>
      <SegmentedControl v-model="span" :options="RANGES" />
    </template>
    <div class="flex h-64 flex-col">
      <UsageChart v-if="system.historyLoaded" v-model:span="span" :points="system.history" :interval="system.historyInterval" />
      <div v-else class="flex flex-1 items-center justify-center"><Spinner /></div>
    </div>
  </SettingsCard>
</template>
