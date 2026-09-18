<script setup>
import NavDrawer from './NavDrawer.vue';
import SidebarContent from './SidebarContent.vue';

/* The sidebar from md up, the drawer below it; both show the same navigation. */
</script>

<template>
  <aside class="sticky top-0 hidden h-screen w-56 shrink-0 border-r border-zinc-800 bg-zinc-900 md:block">
    <SidebarContent />
  </aside>
  <NavDrawer />
</template>
