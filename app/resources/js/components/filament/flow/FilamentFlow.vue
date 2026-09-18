<script setup>
import { computed, watch } from 'vue';
import { useFilamentChangeStore } from '../../../stores/filamentChange';
import { useFilamentStore } from '../../../stores/filament';
import { usePrinterStore } from '../../../stores/printer';
import { useToastStore } from '../../../stores/toasts';
import { useNow } from '../../../composables/useNow';
import { ACTION_LABELS, canCancel, isEnded, showsOldFilament, stepActions, stepProgress, stepTitle } from '../../../filament/walkthrough';
import { formatTemp } from '../../../format';
import AppButton from '../../AppButton.vue';
import ExtruderScene from './ExtruderScene.vue';
import FilamentStepper from './FilamentStepper.vue';
import PanelButton from '../../panel/PanelButton.vue';
import ProgressBar from '../../ProgressBar.vue';
import ProgressRing from '../../panel/ProgressRing.vue';
import SpoolSwatch from '../SpoolSwatch.vue';

/* The walkthrough itself: the steps, the extruder playing the current one, what the user is
   asked to do and the buttons for it. `touch` lays it out for the panel with finger-sized
   buttons and the steps down the side; otherwise it fits a modal. */
const props = defineProps({ touch: { type: Boolean, default: false } });
const emit = defineEmits(['close']);

const change = useFilamentChangeStore();
const filament = useFilamentStore();
const printer = usePrinterStore();
const toasts = useToastStore();
const now = useNow(100);

const state = computed(() => change.current);
const ended = computed(() => isEnded(state.value));
const progress = computed(() => stepProgress(state.value, now.value));
const title = computed(() => stepTitle(state.value));
const actions = computed(() => stepActions(state.value));
const heading = computed(() => ACTION_LABELS[state.value?.action] ?? 'Filament');
const subject = computed(() => state.value?.spool?.name || state.value?.material || null);
const hotend = computed(() => printer.hotend);
const heating = computed(() => state.value?.step === 'heating');
const motion = computed(() => ['loading', 'purging', 'unloading'].includes(state.value?.step));
const Button = computed(() => (props.touch ? PanelButton : AppButton));

const temperature = computed(() => {
  const actual = hotend.value?.actual ?? state.value?.temperature;
  return actual == null ? '–' : formatTemp(actual, 0);
});

// The inventory follows the daemon's record through the next state poll; fetch it again after that.
watch(
  () => state.value?.step,
  (step) => {
    if (step === 'done') setTimeout(() => filament.load().catch(() => {}), 2500);
  },
);

async function act(id) {
  try {
    if (id === 'close') {
      change.dismiss();
      emit('close');
    } else if (id === 'continue') await change.proceed();
    else await change.answer(id);
  } catch (error) {
    toasts.error(error.message);
  }
}

async function cancel() {
  try {
    await change.cancel();
  } catch (error) {
    toasts.error(error.message);
  }
}
</script>

<template>
  <div v-if="state" class="flex h-full min-h-0 flex-col" :class="touch ? 'gap-3' : 'gap-4'">
    <!-- The modal carries the heading in its own title; the panel shows it here, with room kept for the button. -->
    <div v-if="touch || canCancel(state)" class="flex shrink-0 items-center justify-between gap-3" :class="touch ? 'min-h-14' : ''">
      <div v-if="touch" class="flex min-w-0 items-center gap-3">
        <SpoolSwatch v-if="state.spool" :color="state.spool.color" size="lg" />
        <div class="min-w-0">
          <div class="truncate text-xl font-semibold">{{ heading }}</div>
          <div v-if="subject" class="truncate text-sm text-zinc-500">{{ subject }}</div>
        </div>
      </div>
      <span v-else />
      <component :is="Button" v-if="canCancel(state)" variant="ghost" icon="x" :size="touch ? undefined : 'sm'" :disabled="change.busy" @click="cancel">Cancel</component>
    </div>

    <div class="flex min-h-0 flex-1" :class="touch ? 'flex-row gap-4' : 'flex-col gap-4'">
      <FilamentStepper :state="state" :vertical="touch" :class="touch ? 'w-40 shrink-0 pt-1' : 'shrink-0'" />

      <div class="flex min-h-0 flex-1 items-stretch gap-4" :class="touch ? 'flex-row' : 'flex-col sm:flex-row'">
        <div class="flex min-h-0 shrink-0 items-center justify-center" :class="touch ? 'w-44' : 'h-52 sm:h-auto sm:w-44'">
          <ExtruderScene :step="state.step" :action="state.action" :old="showsOldFilament(state)" :progress="progress" :color="state.spool?.color ?? null" class="max-h-full" />
        </div>

        <div class="flex min-w-0 flex-1 flex-col justify-center gap-4">
          <div class="font-semibold" :class="touch ? 'text-2xl' : 'text-lg'">{{ title }}</div>

          <div v-if="heating" class="flex items-center gap-4">
            <ProgressRing v-if="touch" :value="progress" :size="112" :stroke="10" tone="amber">
              <span class="text-2xl font-semibold tabular-nums">{{ temperature }}</span>
              <span class="text-xs text-zinc-500">°C</span>
            </ProgressRing>
            <template v-else>
              <span class="text-2xl font-semibold tabular-nums">{{ temperature }}<span class="ml-1 text-sm font-normal text-zinc-500">°C</span></span>
              <ProgressBar :value="progress" tone="amber" full />
            </template>
          </div>
          <ProgressBar v-else-if="motion" :value="progress" full :size="touch ? 'md' : 'sm'" />

          <div v-if="actions.length" class="flex flex-wrap gap-3" :class="touch ? 'mt-2' : ''">
            <component
              :is="Button"
              v-for="action in actions"
              :key="action.id"
              :variant="action.variant"
              :icon="action.icon"
              :size="touch ? undefined : 'lg'"
              :disabled="change.busy && !ended"
              @click="act(action.id)"
            >
              {{ action.label }}
            </component>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
