<script setup>
import { computed, reactive, ref } from 'vue';
import { methodLabel } from '../../firmware/format.js';
import { useFirmwareStore } from '../../stores/firmware';
import { useSettingsStore } from '../../stores/settings';
import { useToastStore } from '../../stores/toasts';
import AppButton from '../AppButton.vue';
import SettingsField from './SettingsField.vue';
import { inputClass } from './styles';

/* The flash method, saved on change, and the avrdude board parameters with their own Save. */
defineProps({ disabled: { type: Boolean, default: false } });

const firmware = useFirmwareStore();
const settings = useSettingsStore();
const toasts = useToastStore();

const BAUD_RATES = [19200, 38400, 57600, 115200, 230400, 250000];
const changing = ref(false);
const form = reactive({
  mcu: firmware.avrdude.mcu ?? '',
  programmer: firmware.avrdude.programmer ?? '',
  baud: firmware.avrdude.baud ?? 115200,
});
const busy = computed(() => changing.value || settings.saving);

async function changeMethod(event) {
  changing.value = true;
  try {
    await settings.save({ firmware_method: event.target.value });
    await firmware.load();
  } catch (error) {
    toasts.error(error.message);
  } finally {
    event.target.value = firmware.method;
    changing.value = false;
  }
}

async function saveBoard() {
  try {
    await settings.save({
      firmware_mcu: form.mcu.trim().toLowerCase() || null,
      firmware_programmer: form.programmer.trim().toLowerCase() || null,
      firmware_baud: Number(form.baud),
    });
    await firmware.load();
    toasts.success('Board saved');
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <SettingsField label="Method" inline>
      <select :value="firmware.method" :class="inputClass" class="min-w-0 flex-1" :disabled="disabled || busy" @change="changeMethod">
        <option v-for="method in firmware.methods" :key="method" :value="method">{{ methodLabel(method) }}</option>
      </select>
    </SettingsField>
    <form v-if="firmware.method === 'avrdude'" class="flex flex-wrap items-end gap-3" @submit.prevent="saveBoard">
      <SettingsField label="MCU" class="min-w-36 flex-1">
        <input v-model="form.mcu" :class="inputClass" placeholder="atmega2560" :disabled="disabled">
      </SettingsField>
      <SettingsField label="Programmer" class="min-w-36 flex-1">
        <input v-model="form.programmer" :class="inputClass" placeholder="wiring" :disabled="disabled">
      </SettingsField>
      <SettingsField label="Baud rate" class="min-w-28">
        <select v-model="form.baud" :class="inputClass" :disabled="disabled">
          <option v-for="rate in BAUD_RATES" :key="rate" :value="rate">{{ rate }}</option>
        </select>
      </SettingsField>
      <AppButton type="submit" variant="secondary" :disabled="disabled || busy">Save</AppButton>
    </form>
  </div>
</template>
