<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { usePanel } from '../composables/usePanel';
import { usePrinterStore } from '../stores/printer';
import { useSettingsStore } from '../stores/settings';
import { useToastStore } from '../stores/toasts';
import PrinterConnectionFields from './PrinterConnectionFields.vue';
import AppButton from './AppButton.vue';
import ChevronToggle from './ChevronToggle.vue';
import Icon from './Icon.vue';

const printer = usePrinterStore();
const settings = useSettingsStore();
const toasts = useToastStore();
const { root, panel, open, hovering, visible, align, toggle, close } = usePanel();

const form = ref({ serial_port: '', baud_rate: 115200 });
const errors = ref({});

const connecting = computed(() => printer.connecting || printer.connectionState === 'connecting');
const canConnect = computed(() => !connecting.value && Boolean(form.value.serial_port));
const error = computed(() => (printer.connectionState === 'error' ? printer.printer.last_error : null));

onMounted(async () => {
  if (!settings.loaded) {
    try {
      await settings.load();
    } catch (e) {
      toasts.error(e.message);
    }
  }
  loadSettings();
});

watch(() => printer.ports, pickPort);
watch(() => settings.values, loadSettings);

function loadSettings() {
  form.value = { serial_port: '', baud_rate: settings.values.baud_rate ?? 115200 };
  errors.value = {};
  pickPort();
}

function pickPort() {
  if (form.value.serial_port && printer.ports.some((entry) => entry.device === form.value.serial_port)) return;
  const preferred = settings.values.serial_port;
  if (preferred && printer.ports.some((entry) => entry.device === preferred)) {
    form.value.serial_port = preferred;
  } else if (printer.ports.length) {
    form.value.serial_port = printer.ports[0].device;
  }
}

async function connect() {
  if (!canConnect.value) return;
  errors.value = {};
  close();
  try {
    const ok = await printer.connect(form.value.serial_port, Number(form.value.baud_rate));
    if (ok) {
      toasts.success(`Connected to ${printer.machineType || form.value.serial_port}`);
    } else {
      toasts.error(printer.printer.last_error || 'Connection failed');
    }
  } catch (e) {
    if (e.errors) {
      const fields = { port: 'serial_port', baud: 'baud_rate' };
      errors.value = Object.fromEntries(Object.entries(e.errors).map(([key, value]) => [fields[key] ?? key, value]));
      open.value = true;
    }
    toasts.error(e.message);
  }
}
</script>

<template>
  <div ref="root" class="relative" @mouseenter="hovering = true" @mouseleave="hovering = false">
    <div class="flex">
      <button
        type="button"
        class="flex items-center gap-1.5 rounded-l-md bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="!canConnect"
        @click="connect"
      >
        <Icon name="link" class="size-4" />
        {{ connecting ? 'Connecting…' : 'Connect' }}
      </button>
      <ChevronToggle
        class="rounded-r-md border-l border-emerald-700/70 bg-emerald-600 text-white hover:bg-emerald-500"
        :expanded="visible"
        title="Connection"
        @click="toggle"
      />
    </div>

    <div v-show="visible" ref="panel" class="absolute top-full z-30 pt-1.5" :class="align === 'left' ? 'left-0' : 'right-0'">
      <form class="flex w-72 flex-col gap-3 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl" @submit.prevent="connect">
        <fieldset :disabled="connecting">
          <PrinterConnectionFields
            v-model="form"
            :ports="printer.ports"
            :errors="errors"
            compact
          />
        </fieldset>
        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
        <AppButton type="submit" size="sm" variant="primary" icon="link" block :disabled="!canConnect">
          {{ connecting ? 'Connecting…' : 'Connect' }}
        </AppButton>
      </form>
    </div>
  </div>
</template>
