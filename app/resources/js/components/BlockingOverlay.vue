<script setup>
import Spinner from './Spinner.vue';

/* Full-screen card for host actions the user has to wait out; `busy` shows the spinner. */
defineProps({
  title: { type: String, required: true },
  detail: { type: String, default: '' },
  busy: { type: Boolean, default: true },
  tone: { type: String, default: 'neutral', validator: (value) => ['neutral', 'success', 'error'].includes(value) },
});

const TONES = { neutral: 'text-zinc-400', success: 'text-emerald-400', error: 'text-red-400' };
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-zinc-950/90 p-4 text-center backdrop-blur-sm"
      role="alert"
      aria-live="assertive"
    >
      <Spinner v-if="busy" size="size-10" />
      <h2 class="text-lg font-semibold">{{ title }}</h2>
      <p v-if="detail" class="max-w-md text-sm" :class="TONES[tone]">{{ detail }}</p>
      <slot />
    </div>
  </Teleport>
</template>
