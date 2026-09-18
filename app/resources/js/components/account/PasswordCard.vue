<script setup>
import { reactive, ref } from 'vue';
import { useSessionStore } from '../../stores/session';
import { useToastStore } from '../../stores/toasts';
import SettingsCard from '../settings/SettingsCard.vue';
import SettingsField from '../settings/SettingsField.vue';
import { inputClass } from '../settings/styles';

/* A new password, confirmed with the current one; the fields clear once it is saved. */
const session = useSessionStore();
const toasts = useToastStore();
const saving = ref(false);

const form = reactive({ current: '', password: '', confirmation: '' });

async function save() {
  saving.value = true;
  try {
    await session.updatePassword(form.current, form.password, form.confirmation);
    Object.assign(form, { current: '', password: '', confirmation: '' });
    toasts.success('Password changed');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <SettingsCard title="Password" :saving="saving" :disabled="!form.current || !form.password || form.password !== form.confirmation" @submit="save">
    <div class="grid gap-4 sm:grid-cols-3">
      <SettingsField label="Current password">
        <input v-model="form.current" type="password" :class="inputClass" autocomplete="current-password" required>
      </SettingsField>
      <SettingsField label="New password">
        <input v-model="form.password" type="password" :class="inputClass" autocomplete="new-password" minlength="8" required>
      </SettingsField>
      <SettingsField label="Confirm new password">
        <input v-model="form.confirmation" type="password" :class="inputClass" autocomplete="new-password" minlength="8" required>
      </SettingsField>
    </div>
  </SettingsCard>
</template>
