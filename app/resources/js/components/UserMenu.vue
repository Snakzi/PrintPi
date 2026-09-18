<script setup>
import { useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';
import { useSystemStore } from '../stores/system';
import { useThemeStore } from '../stores/theme';
import { useUpdatesStore } from '../stores/updates';
import { useToastStore } from '../stores/toasts';
import { useConfirm } from '../composables/useConfirm';
import DropdownItem from './DropdownItem.vue';
import DropdownMenu from './DropdownMenu.vue';
import Icon from './Icon.vue';
import UserAvatar from './UserAvatar.vue';

/* sidebar: the full-width row at the bottom of the sidebar, whose menu opens upwards; otherwise
   the compact trigger of the status bar. */
defineProps({ sidebar: { type: Boolean, default: false } });

const router = useRouter();
const session = useSessionStore();
const system = useSystemStore();
const theme = useThemeStore();
const updates = useUpdatesStore();
const toasts = useToastStore();
const confirm = useConfirm();

async function signOut() {
  await session.logout();
  router.push({ name: 'login' });
}

async function restartWebServer() {
  if (!(await confirm('Restart the web server?'))) return;
  try {
    await system.restartWebServer();
  } catch (error) {
    toasts.error(error.message);
  }
}

async function reboot() {
  if (!(await confirm('Reboot the Raspberry Pi?', { danger: true }))) return;
  try {
    await system.reboot();
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <DropdownMenu :align="sidebar ? 'left' : 'right'" :direction="sidebar ? 'up' : 'down'" :menu-class="sidebar ? 'w-full' : 'min-w-48'">
    <template #trigger="{ open, toggle }">
      <button
        v-if="sidebar"
        type="button"
        class="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
        :class="{ 'bg-zinc-800 text-zinc-100': open }"
        aria-haspopup="menu"
        :aria-expanded="open"
        @click="toggle"
      >
        <UserAvatar :name="session.user?.name || session.user?.username" />
        <span class="min-w-0 flex-1">
          <span class="block truncate font-medium">{{ session.user?.username }}</span>
          <span class="block truncate text-xs text-zinc-500">{{ session.user?.email }}</span>
        </span>
        <Icon name="chevron" class="size-3.5 shrink-0 text-zinc-500 transition-transform" :class="{ 'rotate-180': !open }" />
      </button>
      <button
        v-else
        type="button"
        class="flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
        :class="{ 'bg-zinc-800 text-zinc-100': open }"
        aria-haspopup="menu"
        :aria-expanded="open"
        @click="toggle"
      >
        <UserAvatar :name="session.user?.name || session.user?.username" size="size-7" textClass="text-[10px]" />
        <Icon name="chevron" class="size-3.5 transition-transform" :class="{ 'rotate-180': open }" />
      </button>
    </template>

    <template v-if="updates.available">
      <DropdownItem icon="download" @click="router.push({ name: 'settings', params: { tab: 'updates' } })">Update to {{ updates.available.version }}</DropdownItem>
      <hr class="my-1 border-zinc-800" />
    </template>
    <DropdownItem icon="user" @click="router.push({ name: 'account' })">Account</DropdownItem>
    <DropdownItem :icon="theme.light ? 'moon' : 'sun'" @click="theme.toggle()">{{ theme.light ? 'Dark mode' : 'Light mode' }}</DropdownItem>
    <DropdownItem icon="logout" @click="signOut">Sign out</DropdownItem>
    <hr class="my-1 border-zinc-800" />
    <DropdownItem icon="server" :disabled="!system.available" @click="restartWebServer">Restart web server</DropdownItem>
    <DropdownItem icon="power" danger :disabled="!system.available" @click="reboot">Reboot Pi</DropdownItem>
  </DropdownMenu>
</template>
