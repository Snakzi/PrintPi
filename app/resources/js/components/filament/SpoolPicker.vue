<script setup>
import { nextTick, ref } from 'vue';
import IconButton from '../IconButton.vue';
import SpoolSelect from './SpoolSelect.vue';
import SpoolSwatch from './SpoolSwatch.vue';

/* The spool of a print with a pencil next to it that turns into a select in place;
   `spool` is what is shown, the model is the id the select works on. */
defineProps({
  spool: { type: Object, default: null },
  modelValue: { type: Number, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const editing = ref(false);
const select = ref(null);

async function start() {
  editing.value = true;
  await nextTick();
  select.value?.$el?.focus();
}

function choose(id) {
  editing.value = false;
  emit('update:modelValue', id);
}
</script>

<template>
  <span v-if="editing" class="flex min-w-0 items-center gap-1" @keydown.esc.prevent="editing = false">
    <SpoolSelect ref="select" :model-value="modelValue" size="sm" class="min-w-0 flex-1" @update:model-value="choose" @blur="editing = false" />
    <IconButton icon="x" title="Cancel" size="sm" @click="editing = false" />
  </span>
  <span v-else class="flex min-w-0 items-center gap-1.5">
    <SpoolSwatch v-if="spool" :color="spool.color" :finish="spool.finish" size="sm" />
    <span class="truncate text-xs" :class="spool ? 'text-zinc-300' : 'text-zinc-500'" :title="spool?.name">{{ spool?.name ?? 'No spool' }}</span>
    <IconButton icon="pencil" title="Change spool" size="sm" :disabled="disabled" class="text-zinc-500" @click="start" />
  </span>
</template>
