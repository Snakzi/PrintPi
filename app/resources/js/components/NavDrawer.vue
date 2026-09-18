<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useNavStore } from '../stores/nav';
import Icon from './Icon.vue';
import SidebarContent from './SidebarContent.vue';

/* The navigation as a drawer from the left on a phone: opened by the menu button in the status
   bar, closed by its own button, the backdrop, Escape or the next page. */
const nav = useNavStore();
const route = useRoute();

watch(() => route.fullPath, () => nav.close());
watch(
  () => nav.open,
  (open) => document.body.classList.toggle('overflow-hidden', open),
);

function onKeydown(event) {
  if (event.key === 'Escape') nav.close();
}

onMounted(() => window.addEventListener('keydown', onKeydown));
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
  document.body.classList.remove('overflow-hidden');
});
</script>

<template>
  <div class="md:hidden">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200"
      leave-to-class="opacity-0"
    >
      <div v-if="nav.open" class="fixed inset-0 z-30 bg-zinc-950/70 backdrop-blur-sm" @click="nav.close()" />
    </Transition>
    <aside
      class="fixed inset-y-0 left-0 z-40 flex w-72 max-w-[85vw] flex-col border-r border-zinc-800 bg-zinc-900 shadow-2xl transition-transform duration-200"
      :class="nav.open ? 'translate-x-0' : '-translate-x-full'"
      :aria-hidden="!nav.open"
    >
      <SidebarContent touch>
        <template #corner>
          <button type="button" class="-mr-2 ml-auto rounded-md p-3 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100" title="Close menu" @click="nav.close()">
            <Icon name="x" class="size-6" />
          </button>
        </template>
      </SidebarContent>
    </aside>
  </div>
</template>
