<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { api } from '../api';
import { useSessionStore } from '../stores/session';
import { useToastStore } from '../stores/toasts';
import { browserTimezone, timezones } from '../format';
import PrinterPicker from '../components/PrinterPicker.vue';
import PrinterConnectionFields from '../components/PrinterConnectionFields.vue';
import CameraPicker from '../components/CameraPicker.vue';
import Icon from '../components/Icon.vue';
import Logo from '../components/Logo.vue';

const router = useRouter();
const session = useSessionStore();
const toasts = useToastStore();

const steps = ['Account', 'Device', 'Printer', 'Connection', 'Camera', 'Done'];
const step = ref(0);
const info = ref(null);
const loadError = ref(null);
const errors = ref({});
const submitting = ref(false);
const cameraBusy = ref(false);

const form = reactive({
  username: '',
  email: '',
  password: '',
  password_confirmation: '',
  hostname: '',
  timezone: browserTimezone(),
  printer_profile: null,
  printer_name: '',
  serial_port: '',
  baud_rate: 115200,
  camera: { device: null, url: null },
});

const zones = timezones();
let timer = null;

async function load(initial = false) {
  try {
    const data = await api('setup');
    info.value = data;
    loadError.value = null;
    if (initial) {
      form.hostname = data.hostname || 'printpi';
      if (data.timezone) form.timezone = data.timezone;
    }
    if (!form.serial_port && data.ports.length) {
      form.serial_port = data.ports.find((port) => !port.device.startsWith('fake://'))?.device ?? data.ports[0].device;
    }
  } catch (error) {
    if (error.status === 403) {
      session.setupComplete = true;
      router.replace({ name: 'login' });
      return;
    }
    loadError.value = error.message;
  }
}

onMounted(async () => {
  await load(true);
  timer = setInterval(load, 4000);
});
onUnmounted(() => clearInterval(timer));

const printers = computed(() => info.value?.printers ?? []);
const selectedPrinter = computed(() => printers.value.find((printer) => printer.id === form.printer_profile) ?? null);

function choosePrinter(id) {
  form.printer_profile = id;
  const printer = printers.value.find((entry) => entry.id === id);
  if (!printer) return;
  form.baud_rate = printer.baud_rate;
  if (!form.printer_name || form.printer_name === lastSuggestedName) form.printer_name = `${printer.manufacturer} ${printer.model}`;
  lastSuggestedName = form.printer_name;
}
let lastSuggestedName = '';

const stepFields = [
  ['username', 'email', 'password', 'password_confirmation'],
  ['hostname', 'timezone'],
  ['printer_profile', 'printer_name'],
  ['serial_port', 'baud_rate'],
  ['camera_device', 'camera_url'],
  [],
];

function validateStep() {
  const found = {};
  if (step.value === 0) {
    if (!/^[a-z0-9._-]{3,50}$/i.test(form.username)) found.username = ['3 to 50 characters: letters, numbers, periods, hyphens and underscores.'];
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) found.email = ['Enter a valid email address.'];
    if (form.password.length < 8) found.password = ['At least 8 characters.'];
    if (form.password !== form.password_confirmation) found.password_confirmation = ['The passwords do not match.'];
  }
  if (step.value === 1) {
    if (!/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(form.hostname)) found.hostname = ['Only lowercase letters, numbers and hyphens.'];
  }
  if (step.value === 2) {
    if (!form.printer_profile) found.printer_profile = ['Select a printer.'];
    if (!form.printer_name.trim()) found.printer_name = ['Enter a name.'];
  }
  errors.value = found;
  return Object.keys(found).length === 0;
}

function next() {
  if (!validateStep()) return;
  step.value = Math.min(step.value + 1, steps.length - 1);
}

function back() {
  errors.value = {};
  step.value = Math.max(step.value - 1, 0);
}

async function startCamera(device) {
  cameraBusy.value = true;
  try {
    await api('setup/camera/start', { method: 'POST', body: { device } });
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 700));
      const status = await api('setup/camera');
      info.value = { ...info.value, camera: status.status, cameras: status.cameras };
      if (status.status.running && status.status.device === device) return;
      if (status.status.error) break;
    }
    toasts.error(info.value.camera.error || 'The stream did not start.');
  } catch (error) {
    toasts.error(error.message);
  } finally {
    cameraBusy.value = false;
  }
}

async function stopCamera() {
  try {
    await api('setup/camera/stop', { method: 'POST' });
    await load();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function finish() {
  submitting.value = true;
  errors.value = {};
  try {
    const data = await api('setup', {
      method: 'POST',
      body: {
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        password_confirmation: form.password_confirmation,
        hostname: form.hostname,
        timezone: form.timezone,
        printer_profile: form.printer_profile,
        printer_name: form.printer_name.trim(),
        serial_port: form.serial_port || null,
        baud_rate: Number(form.baud_rate),
        camera_device: form.camera.device,
        camera_url: form.camera.url || null,
      },
    });
    session.completeSetup(data.user);
    toasts.success(`Welcome, ${data.user.username}!`);
    if (!data.hostname_applied) {
      toasts.info('The hostname was saved but could not be applied on this system.');
    } else {
      toasts.info(`The Pi is now named ${form.hostname}.local`);
    }
    router.replace({ name: 'dashboard' });
  } catch (error) {
    if (error.status === 422 && error.errors) {
      errors.value = error.errors;
      const failing = Object.keys(error.errors);
      const target = stepFields.findIndex((fields) => fields.some((field) => failing.includes(field)));
      if (target >= 0) step.value = target;
    } else {
      toasts.error(error.message);
    }
  } finally {
    submitting.value = false;
  }
}

const field = 'w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-base';
const button = 'rounded-md px-4 py-2 font-semibold disabled:opacity-40';
</script>

<template>
  <div class="mx-auto flex min-h-screen max-w-4xl flex-col p-4">
    <header class="flex flex-wrap items-center gap-4 py-4">
      <h1 class="flex items-center gap-3 text-xl font-semibold"><Logo size="size-10" /> Set up PrintPi</h1>
      <ol class="flex flex-wrap gap-1 text-xs">
        <li
          v-for="(label, index) in steps"
          :key="label"
          class="rounded-full px-2.5 py-1"
          :class="index === step ? 'bg-emerald-600 text-white' : index < step ? 'bg-zinc-800 text-zinc-300' : 'text-zinc-500'"
        >
          {{ index + 1 }} {{ label }}
        </li>
      </ol>
    </header>

    <div v-if="loadError && !info" class="rounded-lg border border-red-800 bg-red-950/50 p-4 text-sm text-red-100">
      The API is not responding: {{ loadError }}
    </div>

    <form v-else-if="info" class="flex flex-1 flex-col gap-4" @submit.prevent="step === steps.length - 1 ? finish() : next()">
      <section v-show="step === 0" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Administrator account</h2>
        <p class="mt-1 text-sm text-zinc-400">Use this account to sign in to PrintPi.</p>
        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Username</span>
            <input v-model="form.username" :class="field" autocomplete="username" autocapitalize="off" autofocus>
            <span v-if="errors.username" class="text-xs text-red-400">{{ errors.username[0] }}</span>
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Email</span>
            <input v-model="form.email" type="email" :class="field" autocomplete="email" autocapitalize="off">
            <span v-if="errors.email" class="text-xs text-red-400">{{ errors.email[0] }}</span>
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Password</span>
            <input v-model="form.password" type="password" :class="field" autocomplete="new-password">
            <span v-if="errors.password" class="text-xs text-red-400">{{ errors.password[0] }}</span>
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Confirm password</span>
            <input v-model="form.password_confirmation" type="password" :class="field" autocomplete="new-password">
            <span v-if="errors.password_confirmation" class="text-xs text-red-400">{{ errors.password_confirmation[0] }}</span>
          </label>
        </div>
      </section>

      <section v-show="step === 1" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Device</h2>
        <p class="mt-1 text-sm text-zinc-400">The hostname makes PrintPi accessible on your network, for example at http://{{ form.hostname || 'printpi' }}.local</p>
        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Hostname</span>
            <input v-model="form.hostname" :class="field" autocapitalize="off" spellcheck="false">
            <span v-if="errors.hostname" class="text-xs text-red-400">{{ errors.hostname[0] }}</span>
            <span v-else-if="!info.system_control" class="text-xs text-amber-300">On this system, the hostname is saved but cannot be applied.</span>
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-zinc-400">Time zone</span>
            <select v-model="form.timezone" :class="field">
              <option v-for="zone in zones" :key="zone" :value="zone">{{ zone }}</option>
            </select>
            <span v-if="errors.timezone" class="text-xs text-red-400">{{ errors.timezone[0] }}</span>
          </label>
        </div>
      </section>

      <section v-show="step === 2" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Which printer will you use?</h2>
        <p class="mt-1 text-sm text-zinc-400">The profile includes the build volume and baud rate.</p>
        <span v-if="errors.printer_profile" class="mt-2 block text-sm text-red-400">{{ errors.printer_profile[0] }}</span>
        <PrinterPicker class="mt-4" :printers="printers" :model-value="form.printer_profile" @update:model-value="choosePrinter" />
        <label class="mt-5 flex flex-col gap-1 text-sm">
          <span class="text-zinc-400">Printer name</span>
          <input v-model="form.printer_name" :class="field" placeholder="e.g. MK4S in the workshop">
          <span v-if="errors.printer_name" class="text-xs text-red-400">{{ errors.printer_name[0] }}</span>
        </label>
      </section>

      <section v-show="step === 3" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Connection</h2>
        <p class="mt-1 text-sm text-zinc-400">
          {{ info.daemon_alive ? 'The daemon is running and lists the ports it detects.' : 'The daemon is not running. Once it starts, it will list the ports it detects.' }}
          You can connect later from the dashboard.
        </p>
        <PrinterConnectionFields
          class="mt-4"
          :model-value="form"
          :ports="info.ports"
          :profile="selectedPrinter"
          :errors="errors"
          @update:model-value="Object.assign(form, $event)"
        />
      </section>

      <section v-show="step === 4" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Camera</h2>
        <p class="mt-1 text-sm text-zinc-400">USB cameras are detected automatically. A stream URL is only needed for a camera connected elsewhere.</p>
        <div class="mt-4">
          <CameraPicker
            v-model="form.camera"
            :cameras="info.cameras"
            :status="info.camera"
            :stream-url="info.stream_url"
            :busy="cameraBusy"
            @start="startCamera"
            @stop="stopCamera"
          />
        </div>
        <span v-if="errors.camera_device || errors.camera_url" class="mt-2 block text-sm text-red-400">
          {{ (errors.camera_device ?? errors.camera_url)[0] }}
        </span>
      </section>

      <section v-show="step === 5" class="rounded-lg border border-zinc-800 bg-zinc-900 p-6">
        <h2 class="text-lg font-semibold">Summary</h2>
        <dl class="mt-4 grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt class="text-zinc-500">Account</dt>
          <dd>{{ form.username }} <span class="text-zinc-500">· {{ form.email }}</span></dd>
          <dt class="text-zinc-500">Hostname</dt>
          <dd>{{ form.hostname }}.local <span class="text-zinc-500">· {{ form.timezone }}</span></dd>
          <dt class="text-zinc-500">Printer</dt>
          <dd>{{ form.printer_name }} <span v-if="selectedPrinter" class="text-zinc-500">· {{ selectedPrinter.manufacturer }} {{ selectedPrinter.model }}</span></dd>
          <dt class="text-zinc-500">Connection</dt>
          <dd>{{ form.serial_port || 'later' }} <span class="text-zinc-500">· {{ form.baud_rate }} baud</span></dd>
          <dt class="text-zinc-500">Camera</dt>
          <dd>{{ form.camera.device || form.camera.url || 'none' }}</dd>
        </dl>
      </section>

      <div class="mt-auto flex items-center justify-between gap-2 py-2">
        <button type="button" :class="[button, 'border border-zinc-700 hover:bg-zinc-800']" :disabled="step === 0 || submitting" @click="back">
          Back
        </button>
        <button
          type="submit"
          :class="[button, 'flex items-center gap-2 bg-emerald-600 text-white hover:bg-emerald-500']"
          :disabled="submitting"
        >
          <template v-if="step === steps.length - 1"><Icon name="check" /> Finish setup</template>
          <template v-else>Next</template>
        </button>
      </div>
    </form>

    <p v-else class="py-12 text-center text-sm text-zinc-500">Loading…</p>
  </div>
</template>
