<script setup>
import { onBeforeUnmount, onMounted } from 'vue';
import Icon from './Icon.vue';

/* size: xl for viewers and pictures, lg for a picker, md for a form. */
defineProps({ size: { type: String, default: 'xl' } });

const SIZES = { md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-5xl' };
const emit = defineEmits(['close']);

function onKeydown(event) {
  if (event.key === 'Escape') emit('close');
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
  document.body.classList.add('overflow-hidden');
});
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
  document.body.classList.remove('overflow-hidden');
});
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-40 flex items-center justify-center bg-zinc-950/80 p-4 backdrop-blur-sm" @click.self="emit('close')">
      <div
        role="dialog"
        aria-modal="true"
        class="flex max-h-full w-full flex-col overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 shadow-2xl"
        :class="SIZES[size] ?? SIZES.xl"
      >
        <div class="flex items-center justify-between gap-4 border-b border-zinc-800 px-4 py-3">
          <slot name="title" />
          <button
            type="button"
            class="shrink-0 rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
            title="Close"
            @click="emit('close')"
          >
            <Icon name="x" />
          </button>
        </div>
        <div class="min-h-0 flex-1">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>
