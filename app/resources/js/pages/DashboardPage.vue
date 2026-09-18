<script setup>
import { onMounted } from 'vue';
import { useDashboardStore } from '../stores/dashboard';
import { useToastStore } from '../stores/toasts';
import DashboardToolbar from '../components/dashboard/DashboardToolbar.vue';
import DashboardGrid from '../components/dashboard/DashboardGrid.vue';

const dashboard = useDashboardStore();
const toasts = useToastStore();

onMounted(async () => {
  if (dashboard.loaded) return;
  try {
    await dashboard.load();
  } catch (error) {
    toasts.error(error.message);
  }
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <DashboardToolbar />
    <DashboardGrid v-if="dashboard.loaded" />
  </div>
</template>
