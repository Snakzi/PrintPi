<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { api } from '../../api';
import { usePrinterStore } from '../../stores/printer';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import PrinterPicker from '../PrinterPicker.vue';
import PrinterConnectionFields from '../PrinterConnectionFields.vue';
import SettingsCard from './SettingsCard.vue';
import SettingsField from './SettingsField.vue';
import { inputClass } from './styles';

const printer = usePrinterStore();
const settings = useSettingsStore();
const toasts = useToastStore();

const printers = ref([]);
const errors = ref({});
const form = reactive({
  printer_profile: settings.values.printer_profile,
  printer_name: settings.values.printer_name ?? '',
  serial_port: settings.values.serial_port ?? '',
  baud_rate: settings.values.baud_rate ?? 115200,
});

onMounted(async () => {
  try {
    printers.value = (await api('printers')).data;
  } catch (error) {
    toasts.error(error.message);
  }
});

const selectedPrinter = computed(() => printers.value.find((entry) => entry.id === form.printer_profile) ?? null);

function choosePrinter(id) {
  form.printer_profile = id;
  const entry = printers.value.find((candidate) => candidate.id === id);
  if (entry) form.baud_rate = entry.baud_rate;
}

async function save(patch, message) {
  errors.value = {};
  try {
    await settings.save(patch);
    toasts.success(message);
  } catch (error) {
    errors.value = error.errors ?? {};
    toasts.error(error.message);
  }
}

function savePrinter() {
  save({ printer_profile: form.printer_profile, printer_name: form.printer_name || null }, 'Printer saved');
}

function saveConnection() {
  save({ serial_port: form.serial_port || null, baud_rate: Number(form.baud_rate) }, 'Connection saved');
}
</script>

<template>
  <SettingsCard title="Printer" :saving="settings.saving" :disabled="!form.printer_profile" @submit="savePrinter">
    <SettingsField label="Name">
      <input v-model="form.printer_name" :class="inputClass" placeholder="e.g. MK4S in the workshop">
    </SettingsField>
    <PrinterPicker class="mt-4" :printers="printers" :model-value="form.printer_profile" name="settings-printer" @update:model-value="choosePrinter" />
  </SettingsCard>

  <SettingsCard title="Connection" :saving="settings.saving" @submit="saveConnection">
    <PrinterConnectionFields
      :model-value="form"
      :ports="printer.ports"
      :profile="selectedPrinter"
      :errors="errors"
      @update:model-value="Object.assign(form, $event)"
    />
  </SettingsCard>
</template>
