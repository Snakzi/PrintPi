<script setup>
import Icon from './Icon.vue';

defineProps({
  icon: { type: String, default: null },
  danger: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
</script>

<template>
  <button
    type="button"
    role="menuitem"
    :disabled="disabled"
    class="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm disabled:cursor-not-allowed disabled:opacity-40"
    :class="danger ? 'text-red-300 hover:enabled:bg-red-950/60 hover:enabled:text-red-200' : 'text-zinc-200 hover:enabled:bg-zinc-800 hover:enabled:text-zinc-50'"
  >
    <Icon v-if="icon" :name="icon" class="size-4" />
    <slot />
  </button>
</template>
