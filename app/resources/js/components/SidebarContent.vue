<script setup>
import { useRoute, useRouter } from 'vue-router';
import { usePrinterStore } from '../stores/printer';
import Icon from './Icon.vue';
import Logo from './Logo.vue';
import PanelLightSwitch from './panel/PanelLightSwitch.vue';
import PanelPowerSwitch from './panel/PanelPowerSwitch.vue';
import SidebarPluginLinks from './SidebarPluginLinks.vue';
import UserMenu from './UserMenu.vue';

/* The navigation itself: brand, the pages, the installed plugins and the user menu at the
   bottom. Sits in the sidebar from md up; with `touch` it is the drawer on a phone, with rows
   a thumb cannot miss and the printer's light and power switches, which the status bar
   has no room for there. */
defineProps({ touch: { type: Boolean, default: false } });

const current = useRoute();
const printer = usePrinterStore();
// The definition order is the menu order; getRoutes() would sort by matcher score instead.
// Active by route name, so a page with its own tabs (settings) keeps its entry lit.
const routes = useRouter().options.routes.filter((route) => route.meta?.nav);
</script>

<template>
  <div class="flex h-full flex-col">
    <div class="flex h-14 shrink-0 items-center gap-2.5 border-b border-zinc-800 px-4">
      <Logo />
      <span class="text-lg font-semibold tracking-tight">PrintPi</span>
      <slot name="corner" />
    </div>
    <div v-if="touch && (printer.light || printer.power)" class="flex shrink-0 gap-2 border-b border-zinc-800 bg-zinc-950/50 p-3">
      <PanelLightSwitch class="flex-1 justify-center" />
      <PanelPowerSwitch class="flex-1 justify-center" />
    </div>
    <nav class="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2">
      <template v-for="route in routes" :key="route.name">
        <RouterLink
          :to="{ name: route.name }"
          class="flex items-center gap-3 rounded-md text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
          :class="[touch ? 'px-4 py-3 text-base' : 'px-3 py-2 text-sm', { 'bg-zinc-800 text-zinc-100': current.name === route.name }]"
          active-class=""
          exact-active-class=""
        >
          <Icon :name="route.meta.icon" :class="touch ? 'size-6' : ''" />
          {{ route.meta.title }}
        </RouterLink>
        <SidebarPluginLinks v-if="route.name === 'plugins'" :touch="touch" />
      </template>
    </nav>
    <div class="shrink-0 border-t border-zinc-800 p-2">
      <UserMenu sidebar />
    </div>
  </div>
</template>
