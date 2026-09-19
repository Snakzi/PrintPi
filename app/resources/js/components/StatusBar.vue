<script setup>
import { useRoute } from 'vue-router';
import { usePrinterStore } from '../stores/printer';
import { useToastStore } from '../stores/toasts';
import { useConfirm } from '../composables/useConfirm';
import ConnectButton from './ConnectButton.vue';
import Icon from './Icon.vue';
import MenuButton from './MenuButton.vue';
import PrinterLightButton from './PrinterLightButton.vue';
import PrinterPowerButton from './PrinterPowerButton.vue';

const route = useRoute();
const printer = usePrinterStore();
const toasts = useToastStore();
const confirm = useConfirm();

async function disconnect() {
  if (printer.printing && !(await confirm('Disconnect during the print?', { message: 'The running print would fail.', danger: true }))) return;
  try {
    await printer.disconnect();
    toasts.info('Disconnected');
  } catch (error) {
    toasts.error(error.message);
  }
}

async function emergencyStop() {
  if (!(await confirm('Send an emergency stop?', { message: 'The printer halts immediately and must be reset afterwards.', danger: true }))) return;
  try {
    await printer.emergencyStop();
    toasts.error('Emergency stop sent');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <header class="flex min-h-14 flex-wrap items-center gap-x-4 gap-y-2 border-b border-zinc-800 bg-zinc-900 px-4 py-2 md:py-0">
    <MenuButton />
    <h1 class="text-base font-semibold">{{ route.meta.title }}</h1>

    <div class="flex items-center gap-2 text-sm text-zinc-300">
      <span class="inline-block size-2.5 rounded-full" :class="printer.statusDotClass" />
      <span>{{ printer.statusLabel }}</span>
      <span v-if="printer.connected && printer.machineType" class="hidden text-zinc-500 sm:inline">
        · {{ printer.machineType }}
      </span>
      <span v-if="printer.connected && printer.printer.port" class="hidden text-zinc-500 lg:inline">
        · {{ printer.printer.port }}
      </span>
    </div>

    <p v-if="printer.apiError" class="truncate text-sm text-red-400">API: {{ printer.apiError }}</p>

    <div class="ml-auto flex items-center gap-2">
      <!-- Both switches sit in the drawer on a phone. max-md, since the switch's own inline-flex
           is emitted after hidden and would win. -->
      <PrinterLightButton v-if="printer.light" class="max-md:hidden" />
      <PrinterPowerButton v-if="printer.power" class="max-md:hidden" />
      <template v-if="printer.connected">
        <button class="rounded-md border border-zinc-700 px-3 py-1.5 text-sm whitespace-nowrap hover:bg-zinc-800" title="Disconnect" @click="disconnect">
          <span class="hidden sm:inline">Disconnect</span>
          <Icon name="unlink" class="sm:hidden" />
        </button>
        <button class="rounded-md bg-red-600 px-3 py-1.5 text-sm font-semibold whitespace-nowrap text-white hover:bg-red-500" title="Emergency stop" @click="emergencyStop">
          <span class="hidden sm:inline">Emergency stop</span>
          <span class="sm:hidden">Stop</span>
        </button>
      </template>
      <ConnectButton v-else-if="printer.daemonAlive" />
    </div>
  </header>
</template>
