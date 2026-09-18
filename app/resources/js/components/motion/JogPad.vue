<script setup>
import JogButton from './JogButton.vue';

/* The X/Y cross and the Z column. `jog` carries axis and direction, `home` the axes to home. */
defineProps({
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
});
const emit = defineEmits(['jog', 'home']);
</script>

<template>
  <div class="flex shrink-0 items-start gap-3">
    <div class="flex flex-col items-center gap-1.5">
      <div class="grid grid-cols-3 gap-1">
        <span />
        <JogButton title="Y+" :rotate="180" :size="size" :disabled="disabled" @click="emit('jog', 'Y', 1)" />
        <span />
        <JogButton title="X−" :rotate="90" :size="size" :disabled="disabled" @click="emit('jog', 'X', -1)" />
        <JogButton icon="home" title="Home X and Y" :size="size" :disabled="disabled" @click="emit('home', 'X Y')" />
        <JogButton title="X+" :rotate="270" :size="size" :disabled="disabled" @click="emit('jog', 'X', 1)" />
        <span />
        <JogButton title="Y−" :size="size" :disabled="disabled" @click="emit('jog', 'Y', -1)" />
        <span />
      </div>
      <span class="text-[11px] font-medium tracking-wide text-zinc-500 uppercase">X / Y</span>
    </div>

    <div class="flex flex-col items-center gap-1.5">
      <div class="grid grid-cols-1 gap-1">
        <JogButton title="Z+" :rotate="180" :size="size" :disabled="disabled" @click="emit('jog', 'Z', 1)" />
        <JogButton icon="home" title="Home Z" :size="size" :disabled="disabled" @click="emit('home', 'Z')" />
        <JogButton title="Z−" :size="size" :disabled="disabled" @click="emit('jog', 'Z', -1)" />
      </div>
      <span class="text-[11px] font-medium tracking-wide text-zinc-500 uppercase">Z</span>
    </div>
  </div>
</template>
