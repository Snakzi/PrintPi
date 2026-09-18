<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { browserSupportsWebAuthnAutofill, WebAuthnAbortService } from '@simplewebauthn/browser';
import { useSessionStore } from '../stores/session';
import { passkeyErrorMessage, passkeysUsable } from '../passkeys/errors';
import Icon from './Icon.vue';

/* Signs in with a passkey. Where the browser supports it, the passkeys are also offered in
   the username field (conditional UI) as soon as the page opens; the button opens the
   dialog. `remember` is read at the moment the ceremony finishes. */
const props = defineProps({ remember: { type: Boolean, default: false } });
const emit = defineEmits(['success', 'error']);

const session = useSessionStore();
const busy = ref(false);
const usable = passkeysUsable();

async function run(autofill) {
  try {
    await session.loginWithPasskey(props.remember, autofill);
    emit('success');
  } catch (error) {
    const message = passkeyErrorMessage(error);
    if (message && !(autofill && error?.name === 'NotAllowedError')) emit('error', message);
  }
}

async function click() {
  busy.value = true;
  try {
    await run(false);
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  if (usable && (await browserSupportsWebAuthnAutofill())) run(true);
});
onBeforeUnmount(() => WebAuthnAbortService.cancelCeremony());
</script>

<template>
  <button
    v-if="usable"
    type="button"
    class="flex w-full items-center justify-center gap-2 rounded-md border border-zinc-700 px-4 py-2.5 font-medium text-zinc-200 hover:bg-zinc-800 disabled:opacity-40"
    :disabled="busy"
    @click="click"
  >
    <Icon name="key" class="size-5" />
    Sign in with a passkey
  </button>
</template>
