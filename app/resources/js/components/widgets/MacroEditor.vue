<script setup>
import { ref } from 'vue';
import AppButton from '../AppButton.vue';
import IconButton from '../IconButton.vue';

/* Edits a copy of the macros; `save` returns the cleaned list, `cancel` discards the draft. */
const props = defineProps({
  macros: { type: Array, required: true },
  saving: { type: Boolean, default: false },
});
const emit = defineEmits(['save', 'cancel']);

const MAX = 20;
const draft = ref(props.macros.map((macro) => ({ ...macro })));

function add() {
  if (draft.value.length >= MAX) return;
  draft.value.push({ label: '', gcode: '' });
}

function save() {
  const macros = draft.value
    .map((macro) => ({ label: macro.label.trim(), gcode: macro.gcode.trim() }))
    .filter((macro) => macro.label && macro.gcode);
  emit('save', macros);
}

const input = 'w-full rounded-md border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none';
</script>

<template>
  <div class="flex h-full flex-col gap-2">
    <div class="flex min-h-0 flex-1 flex-col gap-2 overflow-auto">
      <div v-for="(macro, index) in draft" :key="index" class="flex gap-2 rounded-md bg-zinc-950/50 p-2">
        <div class="flex min-w-0 flex-1 flex-col gap-1.5">
          <input v-model="macro.label" placeholder="Label" maxlength="30" :class="input">
          <textarea v-model="macro.gcode" placeholder="G-code, one command per line" rows="2" spellcheck="false" :class="[input, 'font-mono text-xs']" />
        </div>
        <IconButton icon="trash" title="Remove" class="hover:text-red-400" @click="draft.splice(index, 1)" />
      </div>
      <AppButton size="sm" variant="ghost" icon="plus" class="self-start" :disabled="draft.length >= MAX" @click="add">Add command</AppButton>
    </div>
    <div class="flex shrink-0 justify-end gap-2 pt-1">
      <AppButton size="sm" variant="ghost" @click="emit('cancel')">Cancel</AppButton>
      <AppButton size="sm" variant="primary" icon="check" :disabled="saving" @click="save">Save</AppButton>
    </div>
  </div>
</template>
