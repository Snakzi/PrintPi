<script setup>
import { onMounted } from 'vue';
import { useFilamentStore } from '../stores/filament';
import { useToastStore } from '../stores/toasts';
import SpoolList from '../components/filament/SpoolList.vue';
import SpoolStats from '../components/filament/SpoolStats.vue';

const filament = useFilamentStore();
const toasts = useToastStore();

onMounted(async () => {
  try {
    await Promise.all([filament.load(), filament.loadCatalog()]);
  } catch (error) {
    toasts.error(error.message);
  }
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <SpoolStats />
    <SpoolList />
  </div>
</template>
