<script setup>
import { useNavStore } from '../stores/nav';
import Icon from './Icon.vue';

/* The hamburger that opens the navigation drawer; only on a phone. */
const nav = useNavStore();
</script>

<template>
  <button
    type="button"
    class="-ml-2 rounded-md p-2.5 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 md:hidden"
    title="Menu"
    :aria-expanded="nav.open"
    @click="nav.toggle()"
  >
    <Icon name="bars" class="size-6" />
  </button>
</template>
