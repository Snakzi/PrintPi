<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useConfirmStore } from '../stores/confirm';
import AppButton from './AppButton.vue';
import Icon from './Icon.vue';

/* The app's confirmation dialog, mounted once; the confirm store decides when it shows. A
   compact card with the question, the consequence and two buttons: Cancel on the left,
   Confirm on the right, which is red when the action destroys something. On a phone the
   buttons are tall and share the width, from md up they sit compact at the two edges, Cancel left and Confirm right. Confirm
   has the focus, so Enter confirms and Escape cancels. */
const confirm = useConfirmStore();
const button = ref(null);

function onKeydown(event) {
  if (event.key === 'Escape') confirm.answer(false);
}

watch(
  () => confirm.request,
  async (request) => {
    document.body.classList.toggle('overflow-hidden', Boolean(request));
    if (request) {
      window.addEventListener('keydown', onKeydown);
      await nextTick();
      button.value?.$el?.focus();
    } else {
      window.removeEventListener('keydown', onKeydown);
    }
  },
);
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown);
  document.body.classList.remove('overflow-hidden');
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="confirm.request" class="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/80 p-4 backdrop-blur-sm" @click.self="confirm.answer(false)">
        <div role="alertdialog" aria-modal="true" class="w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl md:rounded-xl md:p-5">
          <div class="flex items-center gap-4 md:gap-3">
            <div class="flex size-12 shrink-0 items-center justify-center rounded-full md:size-10" :class="confirm.request.danger ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-400'">
              <Icon :name="confirm.request.danger ? 'warning' : 'info'" class="size-6 md:size-5" />
            </div>
            <div class="min-w-0">
              <h2 class="text-lg leading-snug font-semibold wrap-anywhere md:text-base md:font-medium">{{ confirm.request.title }}</h2>
              <p v-if="confirm.request.message" class="mt-1 text-sm text-zinc-400">{{ confirm.request.message }}</p>
            </div>
          </div>
          <div class="mt-6 grid grid-cols-2 gap-3 md:mt-5 md:flex md:justify-between md:gap-2">
            <AppButton variant="muted" class="w-full max-md:h-11 md:w-auto md:min-w-24" @click="confirm.answer(false)">Cancel</AppButton>
            <AppButton ref="button" :variant="confirm.request.danger ? 'destructive' : 'primary'" class="w-full max-md:h-11 md:w-auto md:min-w-24" @click="confirm.answer(true)">Confirm</AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
