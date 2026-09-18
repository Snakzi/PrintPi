<script setup>
import { reactive, ref } from 'vue';
import { useSessionStore } from '../../stores/session';
import { useToastStore } from '../../stores/toasts';
import SettingsCard from '../settings/SettingsCard.vue';
import SettingsField from '../settings/SettingsField.vue';
import { inputClass } from '../settings/styles';

/* Username and email of the signed-in user. */
const session = useSessionStore();
const toasts = useToastStore();
const saving = ref(false);

const form = reactive({
  username: session.user?.username ?? '',
  email: session.user?.email ?? '',
});

async function save() {
  saving.value = true;
  try {
    await session.updateProfile(form.username.trim(), form.email.trim());
    toasts.success('Profile saved');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <SettingsCard title="Profile" :saving="saving" @submit="save">
    <div class="grid gap-4 sm:grid-cols-2">
      <SettingsField label="Username">
        <input v-model="form.username" :class="inputClass" autocomplete="username" autocapitalize="off" minlength="3" maxlength="50" required>
      </SettingsField>
      <SettingsField label="Email">
        <input v-model="form.email" type="email" :class="inputClass" autocomplete="email" required>
      </SettingsField>
    </div>
  </SettingsCard>
</template>
