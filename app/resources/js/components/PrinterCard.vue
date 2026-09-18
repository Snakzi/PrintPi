<script setup>
import { computed, ref, watch } from 'vue';
import Icon from './Icon.vue';

/* One printer profile as a radio card: the drawing on the left, model and build volume on the right.
   The manufacturer is not repeated here, the picker groups the cards under it. */
const props = defineProps({
  printer: { type: Object, required: true },
  modelValue: { type: String, default: null },
  name: { type: String, default: 'printer' },
});
const emit = defineEmits(['update:modelValue']);

const src = ref(props.printer.image);
watch(() => props.printer.image, (image) => (src.value = image));

const selected = computed(() => props.modelValue === props.printer.id);
const disabled = computed(() => !props.printer.supported);
</script>

<template>
  <label
    class="relative flex items-center gap-3 rounded-lg border p-3 transition-colors"
    :class="[
      selected ? 'border-emerald-500 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-950/40',
      disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:border-zinc-600',
    ]"
  >
    <input
      type="radio"
      class="sr-only"
      :name="name"
      :value="printer.id"
      :checked="selected"
      :disabled="disabled"
      @change="emit('update:modelValue', printer.id)"
    >
    <img
      :src="src"
      :alt="`${printer.manufacturer} ${printer.model}`"
      class="h-8 w-10 shrink-0 object-contain"
      loading="lazy"
      @error="src = `/images/printers/${printer.type}.svg`"
    >
    <div class="flex min-w-0 flex-1 flex-col justify-center gap-0.5 pr-5">
      <span class="flex items-center gap-2 text-sm font-medium leading-tight">
        {{ printer.model }}
        <span v-if="disabled" class="rounded-md bg-zinc-800 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-zinc-400">Soon</span>
      </span>
      <span v-if="printer.bed" class="text-xs text-zinc-400">{{ printer.bed.x }} × {{ printer.bed.y }} × {{ printer.bed.z }} mm</span>
      <span v-if="printer.note" class="text-xs text-zinc-500">{{ printer.note }}</span>
    </div>
    <span v-if="selected" class="absolute top-2 right-2 flex size-5 items-center justify-center rounded-full bg-emerald-500 text-zinc-950">
      <Icon name="check" class="size-3.5" />
    </span>
  </label>
</template>
