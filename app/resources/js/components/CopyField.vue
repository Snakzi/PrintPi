<script setup>
import { copyText } from '../clipboard';
import { useToastStore } from '../stores/toasts';
import IconButton from './IconButton.vue';
import { inputClass } from './settings/styles';

/* A read-only value with a copy button; `mono` for keys and URLs. */
const props = defineProps({
  value: { type: String, default: null },
  placeholder: { type: String, default: '' },
  mono: { type: Boolean, default: false },
});
const toasts = useToastStore();

async function copy() {
  try {
    await copyText(props.value);
    toasts.success('Copied');
  } catch {
    toasts.error('Could not copy');
  }
}
</script>

<template>
  <div class="relative flex min-w-0">
    <input
      :value="value ?? ''"
      :placeholder="placeholder"
      readonly
      spellcheck="false"
      :class="[inputClass, 'w-full pr-10', mono && 'font-mono']"
      @focus="$event.target.select()"
    >
    <IconButton icon="copy" title="Copy" class="absolute top-1/2 right-1.5 -translate-y-1/2" :disabled="!value" @click="copy" />
  </div>
</template>
