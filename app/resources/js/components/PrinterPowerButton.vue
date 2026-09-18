<script setup>
import { computed, ref, watch } from 'vue';
import { usePrinterStore } from '../stores/printer';
import { useToastStore } from '../stores/toasts';
import { useConfirm } from '../composables/useConfirm';
import SwitchButton from './SwitchButton.vue';

/* The printer's power switch in the status bar, backed by whichever plugin reports one. The
   requested state shows until the plugin confirms it or clearly did not. */
const printer = usePrinterStore();
const toasts = useToastStore();
const confirm = useConfirm();

const requested = ref(null);
let timer = null;

watch(
  () => printer.power?.on,
  (on) => {
    if (requested.value !== null && on === requested.value) settle();
  },
);

function settle() {
  clearTimeout(timer);
  requested.value = null;
}

const on = computed(() => requested.value ?? Boolean(printer.power?.on));
const offline = computed(() => printer.power?.online === false);
const title = computed(() => {
  const name = printer.power?.name || 'printer';
  if (offline.value) return `${name} is offline`;
  return on.value ? `Turn ${name} off` : `Turn ${name} on`;
});

async function toggle() {
  const next = !on.value;
  if (!next && printer.printing && !(await confirm('Turn the printer off during the print?', { message: 'The running print would be lost.', danger: true }))) return;
  requested.value = next;
  clearTimeout(timer);
  timer = setTimeout(settle, 8000);
  try {
    await printer.setPower(next);
  } catch (error) {
    settle();
    toasts.error(error.message);
  }
}
</script>

<template>
  <SwitchButton icon="power" label="Power" :on="on" :offline="offline" :disabled="requested !== null" :title="title" @click="toggle" />
</template>
