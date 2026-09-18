<script setup>
import { computed, nextTick, ref } from 'vue';
import { inputClass } from './settings/styles';

/* A select over known values with a last entry that opens a text input for anything else.
   A model value outside the options shows in the text input, so a value that was typed
   before, or whose options arrive later, is never lost. */
const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, required: true },
  none: { type: String, default: null },
  other: { type: String, default: 'Other…' },
  placeholder: { type: String, default: '' },
  maxlength: { type: Number, default: 100 },
  required: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const OTHER = '__other__';
const chosenOther = ref(false);
const input = ref(null);

const custom = computed(() => chosenOther.value || (props.modelValue !== '' && !props.options.includes(props.modelValue)));
const selected = computed(() => (custom.value ? OTHER : props.modelValue));

async function choose(event) {
  const value = event.target.value;
  chosenOther.value = value === OTHER;
  emit('update:modelValue', value === OTHER ? '' : value);
  if (value === OTHER) {
    await nextTick();
    input.value?.focus();
  }
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <select :value="selected" :class="inputClass" @change="choose">
      <option v-if="none !== null" value="">{{ none }}</option>
      <option v-for="option in options" :key="option" :value="option">{{ option }}</option>
      <option :value="OTHER">{{ other }}</option>
    </select>
    <input
      v-if="custom"
      ref="input"
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :required="required"
      :class="inputClass"
      @input="emit('update:modelValue', $event.target.value)"
    >
  </div>
</template>
