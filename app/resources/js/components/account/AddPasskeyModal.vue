<script setup>
import { onMounted, ref } from 'vue';
import { usePasskeysStore } from '../../stores/passkeys';
import { useToastStore } from '../../stores/toasts';
import { passkeyErrorMessage } from '../../passkeys/errors';
import AppButton from '../AppButton.vue';
import Modal from '../Modal.vue';
import SettingsField from '../settings/SettingsField.vue';
import { inputClass } from '../settings/styles';

/* Names the passkey, then runs the browser's registration ceremony. */
const emit = defineEmits(['close']);

const passkeys = usePasskeysStore();
const toasts = useToastStore();
const name = ref('');
const input = ref(null);
const error = ref(null);

// The modal is teleported, so the autofocus attribute would not take.
onMounted(() => input.value?.focus());

async function add() {
  error.value = null;
  try {
    const passkey = await passkeys.register(name.value.trim());
    toasts.success(`${passkey.name} added`);
    emit('close');
  } catch (e) {
    error.value = passkeyErrorMessage(e);
  }
}
</script>

<template>
  <Modal size="md" @close="emit('close')">
    <template #title>
      <h2 class="font-medium">Add passkey</h2>
    </template>
    <form class="flex flex-col" @submit.prevent="add">
      <div class="p-4">
        <SettingsField label="Name">
          <input ref="input" v-model="name" :class="inputClass" maxlength="100" placeholder="MacBook, iPhone, YubiKey…" required>
        </SettingsField>
        <p v-if="error" class="mt-3 text-sm text-red-400">{{ error }}</p>
      </div>
      <div class="flex justify-end gap-2 border-t border-zinc-800 px-4 py-3">
        <AppButton variant="ghost" @click="emit('close')">Cancel</AppButton>
        <AppButton type="submit" variant="primary" icon="key" :disabled="passkeys.busy">Continue</AppButton>
      </div>
    </form>
  </Modal>
</template>
