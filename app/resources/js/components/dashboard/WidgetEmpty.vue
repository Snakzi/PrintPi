<script setup>
import Icon from '../Icon.vue';

/* The empty state of a widget: an icon, one line of text and, in the slot, an optional action. */
defineProps({
  icon: { type: String, required: true },
  message: { type: String, required: true },
});
</script>

<template>
  <div class="flex h-full min-h-28 flex-1 flex-col items-center justify-center gap-2 p-4 text-center">
    <span class="flex size-10 items-center justify-center rounded-full bg-zinc-800/70">
      <Icon :name="icon" fallback="grid" class="size-5 text-zinc-500" />
    </span>
    <p class="text-sm text-zinc-500">{{ message }}</p>
    <slot />
  </div>
</template>
