<script setup>
import { computed } from 'vue';
import FormSection from './FormSection.vue';
import PrinterCard from './PrinterCard.vue';

/* The printer profiles as radio cards, one section per manufacturer in catalog order. */
const props = defineProps({
  printers: { type: Array, required: true },
  modelValue: { type: String, default: null },
  name: { type: String, default: 'printer' },
});
defineEmits(['update:modelValue']);

const groups = computed(() => {
  const byManufacturer = new Map();
  for (const printer of props.printers) {
    if (!byManufacturer.has(printer.manufacturer)) byManufacturer.set(printer.manufacturer, []);
    byManufacturer.get(printer.manufacturer).push(printer);
  }
  return [...byManufacturer].map(([manufacturer, printers]) => ({ manufacturer, printers }));
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <FormSection v-for="group in groups" :key="group.manufacturer" :title="group.manufacturer">
      <div class="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] gap-3">
        <PrinterCard
          v-for="printer in group.printers"
          :key="printer.id"
          :printer="printer"
          :model-value="modelValue"
          :name="name"
          @update:model-value="$emit('update:modelValue', $event)"
        />
      </div>
    </FormSection>
  </div>
</template>
