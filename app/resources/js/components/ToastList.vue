<script setup>
import { useToastStore } from '../stores/toasts';
import Icon from './Icon.vue';

const toasts = useToastStore();

const styles = {
  info: 'border-zinc-700 bg-zinc-800 text-zinc-100',
  success: 'border-emerald-700 bg-emerald-950 text-emerald-100',
  warning: 'border-amber-700 bg-amber-950 text-amber-100',
  error: 'border-red-800 bg-red-950 text-red-100',
};
const icons = { info: 'info', success: 'check', warning: 'exclamation-circle', error: 'warning' };
</script>

<template>
  <div class="pointer-events-none fixed inset-x-4 top-4 z-50 flex flex-col items-end gap-2 md:inset-x-auto md:right-4">
    <div
      v-for="toast in toasts.items"
      :key="toast.id"
      class="pointer-events-auto flex max-w-sm items-start gap-2 rounded-md border px-3 py-2 text-sm shadow-lg"
      :class="styles[toast.type]"
      role="status"
    >
      <Icon :name="icons[toast.type]" class="mt-0.5 shrink-0" />
      <span class="min-w-0 flex-1 wrap-anywhere">{{ toast.message }}</span>
      <button class="shrink-0 text-current/60 hover:text-current" aria-label="Close" @click="toasts.remove(toast.id)">
        <Icon name="x" class="size-4" />
      </button>
    </div>
  </div>
</template>
