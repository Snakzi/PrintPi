<script setup>
import { computed } from 'vue';
import ToggleSwitch from './ToggleSwitch.vue';

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean], default: null },
  error: { type: String, default: null },
});
const emit = defineEmits(['update:modelValue']);

const value = computed({
  get: () => props.modelValue,
  set: (next) => emit('update:modelValue', next),
});

const input = 'rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-base';
</script>

<template>
  <label class="flex flex-col gap-1 text-sm" :class="field.type === 'text' ? 'sm:col-span-2' : ''">
    <span class="text-zinc-400">{{ field.label }}</span>

    <select v-if="field.type === 'select'" v-model="value" :class="input">
      <option v-for="option in field.options" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
    </select>

    <input
      v-else-if="field.type === 'integer' || field.type === 'number'"
      v-model.number="value"
      type="number"
      :min="field.min"
      :max="field.max"
      :step="field.type === 'integer' ? 1 : 'any'"
      :class="input"
    >

    <input
      v-else-if="field.type === 'color'"
      v-model="value"
      type="color"
      class="h-10 w-20 cursor-pointer rounded-md border border-zinc-700 bg-zinc-950 p-1"
    >

    <span v-else-if="field.type === 'boolean'" class="py-1">
      <ToggleSwitch :model-value="Boolean(value)" :label="field.label" @update:model-value="value = $event" />
    </span>

    <textarea v-else-if="field.type === 'text'" v-model="value" rows="10" spellcheck="false" :class="[input, 'font-mono text-sm']" />

    <input v-else-if="field.type === 'password'" v-model="value" type="password" autocomplete="new-password" :class="input">

    <input v-else v-model="value" type="text" :class="input">

    <span v-if="error" class="text-xs text-red-400">{{ error }}</span>
  </label>
</template>
