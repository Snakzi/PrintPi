<script setup>
import { nextTick, ref } from 'vue';
import IconButton from './IconButton.vue';

/* A piece of text with a pencil next to it that turns into an input in place. Enter or the
   check saves (trimmed), Escape or the cross cancels; the update fires only on a change. */
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Edit' },
  placeholder: { type: String, default: '' },
  maxlength: { type: Number, default: 40 },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const editing = ref(false);
const draft = ref('');
const input = ref(null);

async function start() {
  draft.value = props.modelValue;
  editing.value = true;
  await nextTick();
  input.value?.focus();
  input.value?.select();
}

function save() {
  const next = draft.value.trim();
  editing.value = false;
  if (next !== props.modelValue) emit('update:modelValue', next);
}

function cancel() {
  editing.value = false;
}
</script>

<template>
  <form v-if="editing" class="flex min-w-0 items-center gap-1" @submit.prevent="save">
    <input
      ref="input"
      v-model="draft"
      type="text"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :aria-label="label"
      class="h-7 min-w-0 flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none"
      @keydown.esc.prevent="cancel"
    >
    <IconButton icon="check" title="Save" size="sm" class="text-emerald-400" @click="save" />
    <IconButton icon="x" title="Cancel" size="sm" @click="cancel" />
  </form>
  <span v-else class="flex min-w-0 items-center gap-1">
    <span class="truncate"><slot>{{ modelValue }}</slot></span>
    <IconButton
      icon="pencil"
      :title="label"
      size="sm"
      :disabled="disabled"
      class="text-zinc-500"
      @click="start"
    />
  </span>
</template>
