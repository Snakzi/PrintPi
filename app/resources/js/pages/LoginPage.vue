<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';
import Checkbox from '../components/Checkbox.vue';
import Logo from '../components/Logo.vue';
import PasskeyLoginButton from '../components/PasskeyLoginButton.vue';

const session = useSessionStore();
const router = useRouter();
const route = useRoute();
const username = ref('');
const password = ref('');
const remember = ref(false);
const error = ref(null);
const busy = ref(false);

function enter() {
  router.replace(route.query.redirect ? String(route.query.redirect) : { name: 'dashboard' });
}

async function submit() {
  error.value = null;
  busy.value = true;
  try {
    await session.login(username.value.trim(), password.value, remember.value);
    enter();
  } catch (e) {
    error.value = e.status === 422 ? 'Wrong username or password.' : e.message;
  } finally {
    busy.value = false;
  }
}

const field = 'rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-base';
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <form class="w-full max-w-sm rounded-lg border border-zinc-800 bg-zinc-900 p-6" @submit.prevent="submit">
      <h1 class="flex items-center gap-3 text-xl font-semibold"><Logo size="size-10" /> PrintPi</h1>

      <div class="mt-5 flex flex-col gap-3">
        <label class="flex flex-col gap-1 text-sm">
          <span class="text-zinc-400">Username or email</span>
          <input v-model="username" :class="field" autocomplete="username webauthn" autocapitalize="off" autofocus required>
        </label>
        <label class="flex flex-col gap-1 text-sm">
          <span class="text-zinc-400">Password</span>
          <input v-model="password" type="password" :class="field" autocomplete="current-password" required>
        </label>
        <Checkbox v-model="remember" label="Stay signed in" />
      </div>

      <p v-if="error" class="mt-3 text-sm text-red-400">{{ error }}</p>

      <button
        type="submit"
        class="mt-5 w-full rounded-md bg-emerald-600 px-4 py-2.5 font-semibold text-white hover:bg-emerald-500 disabled:opacity-40"
        :disabled="busy"
      >
        Sign in
      </button>

      <PasskeyLoginButton v-if="session.passkeys" :remember="remember" class="mt-3" @success="enter" @error="error = $event" />
    </form>
  </div>
</template>
