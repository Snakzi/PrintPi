<script setup>
/* A titled group of fields inside a form. */
defineProps({ title: { type: String, required: true } });
</script>

<template>
  <fieldset class="flex flex-col gap-3">
    <legend class="mb-3 text-[11px] font-medium tracking-wide text-zinc-500 uppercase">{{ title }}</legend>
    <slot />
  </fieldset>
</template>
