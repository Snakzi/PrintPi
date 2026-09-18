<script setup>
import { computed } from 'vue';
import ChevronToggle from './ChevronToggle.vue';
import Icon from './Icon.vue';

/* A status bar switch: icon, label and a dot for the state, tinted while on. offline paints
   the dot red and disables the button. `dotColor` paints the dot in the switched thing's own
   colour while on, and `expandable` attaches the chevron half of a split button, which emits
   `toggle` for the panel underneath. */
const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  on: { type: Boolean, default: false },
  offline: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  title: { type: String, default: '' },
  dotColor: { type: String, default: null },
  expandable: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
  panelTitle: { type: String, default: '' },
});
const emit = defineEmits(['click', 'toggle']);

const tone = computed(() =>
  props.on
    ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
    : 'border-zinc-700 text-zinc-300 hover:bg-zinc-800',
);
</script>

<template>
  <span class="inline-flex">
    <button
      type="button"
      class="flex items-center gap-2 border px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
      :class="[tone, expandable ? 'rounded-l-md' : 'rounded-md']"
      :disabled="disabled || offline"
      :title="title"
      :aria-pressed="on"
      @click="emit('click')"
    >
      <Icon :name="icon" class="size-4" />
      <span class="hidden sm:inline">{{ label }}</span>
      <span
        class="size-2 rounded-full"
        :class="on ? 'bg-emerald-400' : offline ? 'bg-red-500' : 'bg-zinc-600'"
        :style="on && dotColor ? { backgroundColor: dotColor } : null"
      />
    </button>
    <ChevronToggle
      v-if="expandable"
      class="rounded-r-md border border-l-0"
      :class="tone"
      :expanded="expanded"
      :title="panelTitle"
      @click="emit('toggle')"
    />
  </span>
</template>
