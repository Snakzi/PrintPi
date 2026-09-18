<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

/* align: which edge of the trigger the menu hangs from; direction "up" opens it above the trigger,
   for a menu at the bottom of the screen. menuClass widens or restyles the panel. */
defineProps({
  align: { type: String, default: 'right' },
  direction: { type: String, default: 'down' },
  menuClass: { type: String, default: 'min-w-48' },
});

const open = ref(false);
const root = ref(null);

function toggle() {
  open.value = !open.value;
}

function close() {
  open.value = false;
}

function onPointerDown(event) {
  if (open.value && root.value && !root.value.contains(event.target)) close();
}

function onKeydown(event) {
  if (event.key === 'Escape') close();
}

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown);
  document.addEventListener('keydown', onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onPointerDown);
  document.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <div ref="root" class="relative">
    <slot name="trigger" :open="open" :toggle="toggle" />
    <div
      v-if="open"
      role="menu"
      class="absolute z-30 overflow-hidden rounded-md border border-zinc-700 bg-zinc-900 py-1 shadow-xl"
      :class="[align === 'left' ? 'left-0' : 'right-0', direction === 'up' ? 'bottom-full mb-1' : 'top-full mt-1', menuClass]"
      @click="close"
    >
      <slot />
    </div>
  </div>
</template>
