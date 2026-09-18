<script setup>
import { computed, ref, watch } from 'vue';
import AppButton from './AppButton.vue';

/* A plug the scan found but nobody added yet, with the name it will get in PrintPi. Tapo
   plugs give their own name only once signed in. */
const props = defineProps({
  device: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['add']);

const suggested = computed(() => props.device.name || props.device.model);
const name = ref(suggested.value);
watch(suggested, (next, previous) => {
  if (name.value === previous) name.value = next;
});

const detail = computed(() => [props.device.name ? props.device.model : null, props.device.host].filter(Boolean).join(' · '));
</script>

<template>
  <form class="flex items-center gap-3 px-3 py-2 text-sm" @submit.prevent="emit('add', name.trim())">
    <div class="flex min-w-0 flex-1 flex-col gap-1">
      <input
        v-model="name"
        type="text"
        maxlength="40"
        :placeholder="suggested"
        :aria-label="`Name for ${suggested}`"
        :disabled="disabled || device.needs_auth"
        class="h-7 w-full max-w-64 rounded-md border border-zinc-700 bg-zinc-950 px-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500 focus:outline-none disabled:opacity-40"
      >
      <span class="truncate text-xs text-zinc-500">{{ detail }}</span>
    </div>
    <span v-if="device.needs_auth" class="rounded bg-amber-950 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-amber-300 uppercase">
      Sign-in required
    </span>
    <AppButton type="submit" size="sm" icon="plus" :disabled="disabled || device.needs_auth">Add</AppButton>
  </form>
</template>
