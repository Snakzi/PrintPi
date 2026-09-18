<script setup>
import Icon from './Icon.vue';

/* The chevron half of a split button; the panel state lives in the parent. Colours and rounding
   come through the class attribute so it matches the button it is attached to. */
defineProps({
  expanded: { type: Boolean, default: false },
  title: { type: String, default: '' },
});
</script>

<template>
  <button type="button" class="flex items-center px-1.5 transition-colors" :aria-expanded="expanded" :title="title">
    <Icon name="chevron" class="size-4 transition-transform" :class="expanded ? 'rotate-180' : ''" />
  </button>
</template>
