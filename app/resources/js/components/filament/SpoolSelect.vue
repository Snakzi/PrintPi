<script setup>
import { computed } from 'vue';
import { useFilamentStore } from '../../stores/filament';
import { spoolDetail } from '../../filament/spools';

/* A select over the spools in use; the model is a spool id or null for "no spool". An
   archived spool that is the current value stays selectable so the choice is visible;
   `markLoaded` names the spool in the printer, `allowNone` false drops the empty entry. */
const props = defineProps({
  modelValue: { type: Number, default: null },
  none: { type: String, default: 'No spool' },
  allowNone: { type: Boolean, default: true },
  markLoaded: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
});
const emit = defineEmits(['update:modelValue']);

const filament = useFilamentStore();
const options = computed(() => filament.items.filter((spool) => !spool.archived_at || spool.id === props.modelValue));

function label(spool) {
  const detail = spoolDetail(spool);
  const name = detail ? `${spool.name} (${detail})` : spool.name;
  return props.markLoaded && spool.loaded ? `${name} · loaded` : name;
}

function onChange(event) {
  const value = event.target.value;
  emit('update:modelValue', value === '' ? null : Number(value));
}
</script>

<template>
  <select
    :value="modelValue ?? ''"
    :disabled="disabled"
    class="min-w-0 rounded-md border border-zinc-700 bg-zinc-950 text-zinc-100 focus:border-emerald-500 focus:outline-none disabled:opacity-40"
    :class="size === 'sm' ? 'h-7 px-2 text-xs' : 'h-9 px-3 text-sm'"
    @change="onChange"
  >
    <option v-if="allowNone" value="">{{ none }}</option>
    <option v-for="spool in options" :key="spool.id" :value="spool.id">{{ label(spool) }}</option>
  </select>
</template>
