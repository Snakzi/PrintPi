<script setup>
import { usePrinterStore } from '../stores/printer';
import Terminal from '../components/Terminal.vue';

const printer = usePrinterStore();
</script>

<template>
  <Terminal v-if="printer.connected" class="h-[calc(100vh-7.5rem)] md:h-[calc(100vh-6rem)]" />
  <div v-else class="mx-auto mt-6 max-w-xl rounded-lg border border-zinc-800 bg-zinc-900 p-6 text-sm text-zinc-400">
    Das Terminal ist erst verfügbar, wenn ein Drucker verbunden ist.
    <RouterLink :to="{ name: 'dashboard' }" class="text-emerald-400 hover:underline">Zum Verbinden</RouterLink>
  </div>
</template>
