<script setup>
import { computed, ref } from 'vue';
import { formatTemp } from '../../format';
import AppButton from '../AppButton.vue';
import Icon from '../Icon.vue';
import IconButton from '../IconButton.vue';
import ProgressBar from '../ProgressBar.vue';

/* One heater: current and target temperature, how far the heat-up has come and a target input.
   `set` carries the new target in °C; 0 turns the heater off. */
const props = defineProps({
  label: { type: String, required: true },
  icon: { type: String, required: true },
  reading: { type: Object, default: null },
  max: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['set']);

const input = ref('');
const actual = computed(() => props.reading?.actual ?? null);
const target = computed(() => props.reading?.target ?? 0);

const state = computed(() => {
  if (!target.value) return { label: 'Off', classes: 'text-zinc-500', tone: 'zinc' };
  if (actual.value == null || actual.value < target.value - 2) {
    return { label: 'Heating', classes: 'text-amber-300', tone: 'amber', pulse: true };
  }
  if (actual.value > target.value + 2) return { label: 'Cooling', classes: 'text-sky-300', tone: 'sky' };
  return { label: 'At target', classes: 'text-emerald-300', tone: 'emerald' };
});

const progress = computed(() => (target.value ? Math.min(1, (actual.value ?? 0) / target.value) : 0));

function submit() {
  const value = Math.max(0, Math.min(props.max, Number(input.value) || 0));
  input.value = '';
  emit('set', value);
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2 rounded-md bg-zinc-950/70 p-3">
    <div class="flex items-center gap-1.5 text-xs">
      <Icon :name="icon" class="size-4 text-zinc-500" />
      <span class="font-medium text-zinc-300">{{ label }}</span>
      <span class="ml-auto flex items-center gap-1.5" :class="state.classes">
        <span class="size-1.5 rounded-full bg-current" :class="state.pulse ? 'animate-pulse' : ''" />
        {{ state.label }}
      </span>
    </div>

    <div class="flex items-baseline gap-2">
      <span class="text-3xl leading-none font-semibold tracking-tight text-zinc-50 tabular-nums">
        {{ formatTemp(actual) }}<span class="ml-0.5 text-base font-normal text-zinc-500">°C</span>
      </span>
      <span class="ml-auto text-sm text-zinc-500 tabular-nums">/ {{ formatTemp(target, 0) }} °C</span>
    </div>

    <ProgressBar :value="progress" :tone="state.tone" size="sm" full />

    <form class="flex items-center gap-1.5" @submit.prevent="submit">
      <input
        v-model="input"
        type="number"
        min="0"
        :max="max"
        step="5"
        placeholder="°C"
        :disabled="disabled"
        class="h-7 min-w-0 flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-2 text-sm tabular-nums [appearance:textfield] placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none disabled:opacity-40 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      >
      <AppButton type="submit" size="sm" variant="primary" :disabled="disabled">Set</AppButton>
      <IconButton icon="power" title="Turn off" :disabled="disabled || !target" @click="emit('set', 0)" />
    </form>
  </div>
</template>
