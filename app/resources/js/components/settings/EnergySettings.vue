<script setup>
import { reactive } from 'vue';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import SettingsCard from './SettingsCard.vue';
import SettingsField from './SettingsField.vue';
import { inputClass } from './styles';

const settings = useSettingsStore();
const toasts = useToastStore();

const form = reactive({
  energy_price: settings.values.energy_price ?? '',
  currency: settings.values.currency ?? '€',
});

async function save() {
  const price = form.energy_price === '' || form.energy_price === null ? null : Number(form.energy_price);
  try {
    await settings.save({ energy_price: price, currency: form.currency || '€' });
    toasts.success('Energy saved');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <SettingsCard title="Energy" :saving="settings.saving" @submit="save">
    <div class="grid gap-4 sm:grid-cols-2">
      <SettingsField label="Electricity price per kWh">
        <input v-model="form.energy_price" type="number" min="0" step="0.01" inputmode="decimal" :class="inputClass" placeholder="0.30">
      </SettingsField>
      <SettingsField label="Currency">
        <input v-model="form.currency" maxlength="5" :class="inputClass">
      </SettingsField>
    </div>
  </SettingsCard>
</template>
