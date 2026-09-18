<script setup>
import { computed } from 'vue';
import { avatarColor, initials } from '../avatar';

/* A round badge with the initials of a name on a colour derived from it. */
const props = defineProps({
  name: { type: String, default: '' },
  size: { type: String, default: 'size-8' },
  textClass: { type: String, default: 'text-xs' },
});
const letters = computed(() => initials(props.name));
const background = computed(() => avatarColor(props.name));
</script>

<template>
  <span
    class="flex shrink-0 items-center justify-center rounded-full font-semibold tracking-wide text-white select-none"
    :class="[size, textClass]"
    :style="{ background }"
    aria-hidden="true"
  >
    {{ letters }}
  </span>
</template>
