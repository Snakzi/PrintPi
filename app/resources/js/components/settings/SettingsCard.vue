<script setup>
import AppButton from '../AppButton.vue';

/* A titled card; with `form` it submits through a Save button, otherwise it is a plain section.
   The `actions` slot sits in the title row, for a button that belongs to the whole card. */
defineProps({
  title: { type: String, required: true },
  form: { type: Boolean, default: true },
  saving: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
defineEmits(['submit']);
</script>

<template>
  <component :is="form ? 'form' : 'section'" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6" @submit.prevent="$emit('submit')">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-lg font-semibold">{{ title }}</h2>
      <slot name="actions" />
    </div>
    <div class="mt-4">
      <slot />
    </div>
    <div v-if="form" class="mt-4">
      <AppButton type="submit" variant="primary" :disabled="saving || disabled">Save</AppButton>
    </div>
  </component>
</template>
