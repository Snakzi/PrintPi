<script setup>
import { inject } from 'vue';

/* Secondary controls of a widget. Inside a WidgetFrame they move into the frame's header; on a page
   without a frame they render where they are written. */
const target = inject('widgetActions', null);
</script>

<template>
  <Teleport v-if="target" defer :to="target">
    <slot />
  </Teleport>
  <slot v-else />
</template>
