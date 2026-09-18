<script setup>
import { onMounted, ref } from 'vue';
import { usePasskeysStore } from '../../stores/passkeys';
import { useSessionStore } from '../../stores/session';
import { useToastStore } from '../../stores/toasts';
import { passkeysUsable } from '../../passkeys/errors';
import AddPasskeyModal from './AddPasskeyModal.vue';
import AppButton from '../AppButton.vue';
import PasskeyRow from './PasskeyRow.vue';
import { useConfirm } from '../../composables/useConfirm';
import SettingsCard from '../settings/SettingsCard.vue';

/* The user's passkeys with add, rename and remove. Adding needs a secure context (HTTPS or
   localhost) and a hostname; on a plain HTTP address the button stays off and the line says why. */
const passkeys = usePasskeysStore();
const session = useSessionStore();
const toasts = useToastStore();
const confirm = useConfirm();
const adding = ref(false);
const usable = passkeysUsable();

onMounted(async () => {
  try {
    await passkeys.load();
  } catch (error) {
    toasts.error(error.message);
  }
});

async function rename(passkey, name) {
  if (!name) return;
  try {
    await passkeys.rename(passkey, name);
  } catch (error) {
    toasts.error(error.message);
  }
}

async function remove(passkey) {
  if (!(await confirm(`Remove the passkey ${passkey.name}?`, { danger: true }))) return;
  try {
    await passkeys.remove(passkey);
    session.passkeys = passkeys.items.length > 0;
    toasts.success(`${passkey.name} removed`);
  } catch (error) {
    toasts.error(error.message);
  }
}

function closeAdd() {
  adding.value = false;
  session.passkeys = passkeys.items.length > 0;
}
</script>

<template>
  <SettingsCard title="Passkeys" :form="false">
    <template #actions>
      <AppButton icon="plus" :disabled="!usable" @click="adding = true">Add passkey</AppButton>
    </template>

    <ul v-if="passkeys.items.length" class="divide-y divide-zinc-800">
      <PasskeyRow v-for="passkey in passkeys.items" :key="passkey.id" :passkey="passkey" @rename="rename(passkey, $event)" @remove="remove(passkey)" />
    </ul>
    <p v-else class="text-sm text-zinc-500">{{ passkeys.loaded ? 'No passkeys' : 'Loading…' }}</p>
    <p v-if="!usable" class="mt-3 text-sm text-amber-400">Passkeys need HTTPS and a hostname, not an IP address.</p>

    <AddPasskeyModal v-if="adding" @close="closeAdd" />
  </SettingsCard>
</template>
