<script setup>
import { onMounted } from 'vue';
import { usePrintStore } from '../stores/prints';
import { useToastStore } from '../stores/toasts';
import PrintHistoryList from '../components/prints/PrintHistoryList.vue';

const prints = usePrintStore();
const toasts = useToastStore();

onMounted(async () => {
  try {
    await prints.load();
  } catch (error) {
    toasts.error(error.message);
  }
});
</script>

<template>
  <PrintHistoryList />
</template>
