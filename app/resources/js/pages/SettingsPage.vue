<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSettingsStore } from '../stores/settings';
import { useToastStore } from '../stores/toasts';
import SettingsNav from '../components/settings/SettingsNav.vue';
import PrinterSettings from '../components/settings/PrinterSettings.vue';
import CameraSettings from '../components/settings/CameraSettings.vue';
import SlicerSettings from '../components/settings/SlicerSettings.vue';
import EnergySettings from '../components/settings/EnergySettings.vue';
import PrintsSettings from '../components/settings/PrintsSettings.vue';
import NotificationsSettings from '../components/settings/NotificationsSettings.vue';
import DeviceSettings from '../components/settings/DeviceSettings.vue';
import UpdatesSettings from '../components/settings/UpdatesSettings.vue';
import SystemSettings from '../components/settings/SystemSettings.vue';

const TABS = [
  { id: 'printer', label: 'Printer', icon: 'printer', component: PrinterSettings },
  { id: 'camera', label: 'Camera', icon: 'camera', component: CameraSettings },
  { id: 'slicer', label: 'Slicer', icon: 'send', component: SlicerSettings },
  { id: 'prints', label: 'Prints', icon: 'photo', component: PrintsSettings },
  { id: 'energy', label: 'Energy', icon: 'bolt', component: EnergySettings },
  { id: 'notifications', label: 'Notifications', icon: 'bell', component: NotificationsSettings },
  { id: 'device', label: 'Device', icon: 'chip', component: DeviceSettings },
  { id: 'updates', label: 'Updates', icon: 'download', component: UpdatesSettings },
  { id: 'system', label: 'System', icon: 'info', component: SystemSettings },
];

const route = useRoute();
const router = useRouter();
const settings = useSettingsStore();
const toasts = useToastStore();
const ready = ref(false);

const current = computed(() => TABS.find((tab) => tab.id === route.params.tab) ?? TABS[0]);

watch(
  () => route.params.tab,
  (tab) => {
    if (tab && !TABS.some((entry) => entry.id === tab)) router.replace({ name: 'settings', params: { tab: TABS[0].id } });
  },
  { immediate: true },
);

// The sections take their initial values from the store, so it is loaded before they mount.
onMounted(async () => {
  try {
    await settings.load();
  } catch (error) {
    toasts.error(error.message);
  }
  ready.value = true;
});
</script>

<template>
  <div class="mx-auto flex max-w-6xl flex-col gap-4 md:flex-row md:gap-6">
    <SettingsNav :tabs="TABS" :current="current.id" />
    <div class="flex min-w-0 flex-1 flex-col gap-4">
      <component :is="current.component" v-if="ready" :key="current.id" />
    </div>
  </div>
</template>
